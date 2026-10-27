"""Persistent storage for uploaded video analysis datasets in AWS S3."""

from __future__ import annotations

import json
import logging
import mimetypes
import shutil
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)
LOCAL_ARCHIVE_DIR = Path(__file__).resolve().parents[2] / "data" / "video_datasets"


def _s3_credentials_configured() -> bool:
    """Avoid futile S3 calls in development when .env still has sample credentials."""
    access_key = settings.aws_access_key_id.strip()
    secret_key = settings.aws_secret_access_key.strip()
    sample_values = {"your_aws_access_key", "your_aws_secret_key", "changeme", "placeholder"}
    if access_key.lower() in sample_values or secret_key.lower() in sample_values:
        return False
    # Production may use an IAM role or another boto credential provider.
    return (bool(access_key and secret_key) or not settings.is_development)


class _LocalStreamingBody:
    """Small file wrapper matching the chunked interface returned by boto3."""

    def __init__(self, path: Path, start: int, length: int) -> None:
        self._file = path.open("rb")
        self._file.seek(start)
        self._remaining = length

    def iter_chunks(self, chunk_size: int = 1024 * 1024):
        while self._remaining:
            chunk = self._file.read(min(chunk_size, self._remaining))
            if not chunk:
                break
            self._remaining -= len(chunk)
            yield chunk

    def close(self) -> None:
        self._file.close()


def _local_dataset_dir(dataset_id: str) -> Path:
    return LOCAL_ARCHIVE_DIR / dataset_id


def _read_local_dataset(dataset_id: str) -> Dict[str, Any] | None:
    manifest = _local_dataset_dir(dataset_id) / "analysis.json"
    if not manifest.exists():
        return None
    return json.loads(manifest.read_text(encoding="utf-8"))


def _write_local_dataset(dataset: Dict[str, Any], video_path: str | Path) -> None:
    dataset_dir = _local_dataset_dir(dataset["dataset_id"])
    dataset_dir.mkdir(parents=True, exist_ok=True)
    source_name = f"source{Path(video_path).suffix.lower()}"
    shutil.copy2(video_path, dataset_dir / source_name)
    local_dataset = {**dataset, "storage_backend": "local", "video_key": source_name}
    temporary_manifest = dataset_dir / "analysis.json.tmp"
    temporary_manifest.write_text(json.dumps(local_dataset, separators=(",", ":")), encoding="utf-8")
    temporary_manifest.replace(dataset_dir / "analysis.json")


def _list_local_datasets(limit: int) -> List[Dict[str, Any]]:
    if not LOCAL_ARCHIVE_DIR.exists():
        return []
    manifests = sorted(
        LOCAL_ARCHIVE_DIR.glob("*/analysis.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    datasets = []
    for manifest in manifests:
        try:
            dataset = json.loads(manifest.read_text(encoding="utf-8"))
            datasets.append({
                key: dataset[key]
                for key in ("dataset_id", "source_name", "location", "analyzed_at", "storage_backend")
                if key in dataset
            })
        except (OSError, json.JSONDecodeError, KeyError):
            logger.warning("Skipping unreadable local dataset manifest %s", manifest)
    return datasets[:limit]


@lru_cache(maxsize=1)
def _get_s3_client():
    credentials: Dict[str, str] = {}
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        credentials = {
            "aws_access_key_id": settings.aws_access_key_id,
            "aws_secret_access_key": settings.aws_secret_access_key,
        }
        if settings.aws_session_token:
            credentials["aws_session_token"] = settings.aws_session_token
    client_options = {}
    if settings.is_development:
        client_options["config"] = Config(
            connect_timeout=3,
            read_timeout=10,
            retries={"max_attempts": 1, "mode": "standard"},
        )
    return boto3.client("s3", region_name=settings.aws_region, **credentials, **client_options)


def _dataset_prefix(dataset_id: str) -> str:
    return f"{settings.s3_dataset_storage_prefix.strip('/')}/{dataset_id}"


def save_dataset(
    dataset_id: str,
    video_path: str | Path,
    file_name: str,
    location: Dict[str, Any],
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """Keep a local copy and use S3 when it is reachable."""
    path = Path(video_path)
    prefix = _dataset_prefix(dataset_id)
    video_key = f"{prefix}/source{path.suffix.lower()}"
    manifest_key = f"{prefix}/analysis.json"
    dataset = {
        "dataset_id": dataset_id,
        "source_name": file_name,
        "location": location,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "video_key": video_key,
        "result": result,
    }

    local_saved = False
    try:
        _write_local_dataset(dataset, path)
        local_saved = True
    except Exception:
        logger.exception("Unable to create local fallback for video dataset %s", dataset_id)

    if not _s3_credentials_configured():
        logger.info("AWS credentials are not configured; saved video dataset %s locally", dataset_id)
        if local_saved:
            return {**dataset, "storage_backend": "local", "video_key": f"source{path.suffix.lower()}"}
        raise RuntimeError("Local archive could not be written and AWS S3 credentials are not configured")

    try:
        client = _get_s3_client()
        client.upload_file(
            str(path),
            settings.s3_bucket_name,
            video_key,
            ExtraArgs={
                "ContentType": mimetypes.guess_type(file_name)[0] or "application/octet-stream",
                "ServerSideEncryption": "AES256",
            },
        )
        cloud_dataset = {**dataset, "storage_backend": "s3"}
        client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=manifest_key,
            Body=json.dumps(cloud_dataset, separators=(",", ":")).encode("utf-8"),
            ContentType="application/json",
            ServerSideEncryption="AES256",
        )
        return cloud_dataset
    except Exception:
        logger.warning("S3 archive unavailable for video dataset %s", dataset_id, exc_info=True)
        try:
            if "client" in locals():
                client.delete_object(Bucket=settings.s3_bucket_name, Key=video_key)
        except Exception:
            logger.exception("Unable to clean up source video after dataset save failed")
        if local_saved:
            return {**dataset, "storage_backend": "local", "video_key": f"source{path.suffix.lower()}"}
        raise

    return {**dataset, "storage_backend": "local"}


def list_datasets(limit: int = 20) -> List[Dict[str, Any]]:
    """List S3 datasets and merge locally archived datasets for development."""
    local_datasets = _list_local_datasets(limit)
    if not _s3_credentials_configured():
        return local_datasets
    try:
        client = _get_s3_client()
        paginator = client.get_paginator("list_objects_v2")
        manifests = []
        for page in paginator.paginate(
            Bucket=settings.s3_bucket_name,
            Prefix=f"{settings.s3_dataset_storage_prefix.strip('/')}/",
        ):
            manifests.extend(
                item for item in page.get("Contents", [])
                if item["Key"].endswith("/analysis.json")
            )
        manifests.sort(key=lambda item: item["LastModified"], reverse=True)
    except Exception:
        logger.warning("S3 dataset listing unavailable; using local archive", exc_info=True)
        return local_datasets

    datasets = []
    seen = set()
    for item in manifests[:limit]:
        dataset_id = item["Key"].split("/")[-2]
        try:
            dataset = get_dataset(dataset_id)
        except Exception:
            logger.warning("Unable to load archived dataset %s", dataset_id, exc_info=True)
            continue
        datasets.append({
            key: dataset[key]
            for key in ("dataset_id", "source_name", "location", "analyzed_at", "storage_backend")
            if key in dataset
        })
        seen.add(dataset_id)
    datasets.extend(dataset for dataset in local_datasets if dataset["dataset_id"] not in seen)
    datasets.sort(key=lambda item: item.get("analyzed_at", ""), reverse=True)
    return datasets[:limit]


def get_dataset(dataset_id: str) -> Dict[str, Any]:
    """Load a saved dataset, falling back to the local archive when available."""
    if not _s3_credentials_configured():
        local_dataset = _read_local_dataset(dataset_id)
        if local_dataset:
            return local_dataset
        raise FileNotFoundError(f"Saved video dataset '{dataset_id}' was not found in the local archive.")
    try:
        response = _get_s3_client().get_object(
            Bucket=settings.s3_bucket_name,
            Key=f"{_dataset_prefix(dataset_id)}/analysis.json",
        )
    except ClientError as error:
        local_dataset = _read_local_dataset(dataset_id)
        if local_dataset:
            return local_dataset
        if error.response.get("Error", {}).get("Code") in {"NoSuchKey", "404", "NotFound"}:
            raise FileNotFoundError(f"Saved video dataset '{dataset_id}' was not found.") from error
        raise
    except Exception:
        local_dataset = _read_local_dataset(dataset_id)
        if local_dataset:
            logger.warning("S3 dataset fetch unavailable; using local dataset %s", dataset_id, exc_info=True)
            return local_dataset
        raise
    return json.loads(response["Body"].read())


def get_video(dataset_id: str, range_header: str | None = None):
    """Return a video from S3 or the local archive."""
    dataset = get_dataset(dataset_id)
    request_options = {}
    if range_header:
        request_options["Range"] = range_header
    try:
        if dataset.get("storage_backend") == "local":
            raise RuntimeError("Dataset is stored in the local development archive")
        response = _get_s3_client().get_object(
            Bucket=settings.s3_bucket_name,
            Key=dataset["video_key"],
            **request_options,
        )
        return (
            response["Body"],
            response.get("ContentType", "application/octet-stream"),
            response.get("ResponseMetadata", {}).get("HTTPStatusCode", 200),
            {
                key: response[key]
                for key in ("ContentLength", "ContentRange", "AcceptRanges")
                if key in response
            },
        )
    except Exception as error:
        local_video = _local_dataset_dir(dataset_id) / f"source{Path(dataset['source_name']).suffix.lower()}"
        if local_video.exists():
            size = local_video.stat().st_size
            start, end, status_code = 0, size - 1, 200
            if range_header and range_header.startswith("bytes="):
                byte_range = range_header[6:].split(",", 1)[0]
                first, _, last = byte_range.partition("-")
                if first:
                    start = int(first)
                    end = min(int(last), size - 1) if last else size - 1
                elif last:
                    start = max(0, size - int(last))
                if start > end or start >= size:
                    raise ValueError("Requested video byte range is not available") from error
                status_code = 206
            length = max(0, end - start + 1)
            headers = {"ContentLength": length, "AcceptRanges": "bytes"}
            if status_code == 206:
                headers["ContentRange"] = f"bytes {start}-{end}/{size}"
            return (
                _LocalStreamingBody(local_video, start, length),
                mimetypes.guess_type(local_video.name)[0] or "application/octet-stream",
                status_code,
                headers,
            )
        if isinstance(error, ClientError) and error.response.get("Error", {}).get("Code") in {"NoSuchKey", "404", "NotFound"}:
            raise FileNotFoundError(f"Source video for dataset '{dataset_id}' was not found.") from error
        raise
