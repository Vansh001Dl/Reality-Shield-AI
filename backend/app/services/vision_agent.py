"""YOLO-based vision agent for road object detection, tracking, and frame processing."""

from __future__ import annotations

from collections import OrderedDict
from functools import lru_cache
import logging
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np
import requests
try:
    from ultralytics import YOLO
except ImportError:  # Keep health, risk, route, and chat APIs available without vision extras.
    YOLO = None  # type: ignore[assignment,misc]

from app.core.config import settings
from app.models.detection import Detection, DetectionResponse

logger = logging.getLogger(__name__)

TARGET_CLASSES = {
    "car": {"car", "vehicle"},
    "truck": {"truck", "pickup_truck"},
    "bus": {"bus"},
    "bike": {"bike", "motorcycle", "bicycle"},
    "pedestrian": {"person", "pedestrian", "man", "woman"},
    "pothole": {"pothole", "road_hole", "crack", "road_hazard"},
}

# Larger vehicle classes are commonly confused in distant or partially occluded
# road footage. Keep their threshold stricter than the general YOLO threshold.
CLASS_CONFIDENCE_THRESHOLDS = {
    "car": 0.30,
    "truck": 0.45,
    "bus": 0.35,
    "bike": 0.30,
    "pedestrian": 0.30,
    "pothole": 0.35,
}

MODEL_DIR = Path(__file__).resolve().parents[2] / "ml_models" / "yolo_weights"


class CentroidTracker:
    """Very small centroid-based tracker for assigning stable IDs across frames."""

    def __init__(self, max_disappeared: int = 10) -> None:
        self.next_id = 1
        self.objects: Dict[int, Tuple[float, float]] = {}
        self.class_ids: Dict[int, int] = {}
        self.disappeared: Dict[int, int] = {}
        self.max_disappeared = max_disappeared

    def register(self, centroid: Tuple[float, float], class_id: int) -> int:
        object_id = self.next_id
        self.next_id += 1
        self.objects[object_id] = centroid
        self.class_ids[object_id] = class_id
        self.disappeared[object_id] = 0
        return object_id

    def deregister(self, object_id: int) -> None:
        self.objects.pop(object_id, None)
        self.class_ids.pop(object_id, None)
        self.disappeared.pop(object_id, None)

    def update(self, detections: Sequence[Tuple[int, int, float, float]]) -> Dict[int, int]:
        """Match same-class centroids and return detection-index to track-ID assignments."""
        if not detections:
            for object_id in list(self.objects.keys()):
                self.disappeared[object_id] = self.disappeared.get(object_id, 0) + 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return {}

        assignments: Dict[int, int] = {}
        matched_tracks: set[int] = set()
        matched_detections: set[int] = set()
        candidates: List[Tuple[float, int, int]] = []
        for detection_position, (_, class_id, x, y) in enumerate(detections):
            for object_id, centroid in self.objects.items():
                if self.class_ids.get(object_id) != class_id:
                    continue
                distance = float(np.linalg.norm(np.asarray(centroid) - np.asarray((x, y))))
                if distance < 200:
                    candidates.append((distance, object_id, detection_position))

        for _, object_id, detection_position in sorted(candidates):
            if object_id in matched_tracks or detection_position in matched_detections:
                continue
            detection_index, class_id, x, y = detections[detection_position]
            self.objects[object_id] = (x, y)
            self.disappeared[object_id] = 0
            assignments[detection_index] = object_id
            matched_tracks.add(object_id)
            matched_detections.add(detection_position)

        for object_id in list(self.objects):
            if object_id in matched_tracks:
                continue
            self.disappeared[object_id] = self.disappeared.get(object_id, 0) + 1
            if self.disappeared[object_id] > self.max_disappeared:
                self.deregister(object_id)

        for detection_position, (detection_index, class_id, x, y) in enumerate(detections):
            if detection_position in matched_detections:
                continue
            assignments[detection_index] = self.register((x, y), class_id)

        return assignments


def _normalize_class_name(raw_label: str) -> str:
    """Map model class names to the requested categories."""
    label = raw_label.lower().strip()
    for canonical_name, aliases in TARGET_CLASSES.items():
        if label in aliases or label == canonical_name:
            return canonical_name
    return label


def _resolve_model_path(custom_path: Optional[str] = None) -> str:
    """Choose an available local YOLO weights file or pretrained weights."""
    if custom_path:
        candidate = Path(custom_path)
        if candidate.exists():
            return str(candidate)

    preferred = MODEL_DIR / "best.pt"
    if preferred.exists():
        return str(preferred)

    return "yolov8n.pt"


class _RoboflowBoxes:
    def __init__(self, xyxy: List[List[float]], confidences: List[float], classes: List[int]) -> None:
        self.xyxy = np.asarray(xyxy, dtype=float).reshape((-1, 4))
        self.conf = np.asarray(confidences, dtype=float)
        self.cls = np.asarray(classes, dtype=float)

    def __len__(self) -> int:
        return len(self.xyxy)


class _RoboflowHostedModel:
    """Adapt Roboflow hosted object-detection responses to the YOLO result shape."""

    def __call__(self, frame: np.ndarray, conf: float = 0.25, **_: Any) -> List[Any]:
        success, encoded = cv2.imencode(".jpg", frame)
        if not success:
            raise RuntimeError("Could not encode frame for Roboflow inference.")

        model_id = settings.roboflow_model_id.strip().strip("/")
        url = f"{settings.roboflow_api_url.rstrip('/')}/{model_id}"
        response = requests.post(
            url,
            params={
                "api_key": settings.roboflow_api_key,
                "confidence": round(conf * 100),
            },
            data=encoded.tobytes(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        predictions = payload.get("predictions")
        if not isinstance(predictions, list):
            raise RuntimeError("Roboflow response did not contain a predictions list.")

        names: Dict[int, str] = {}
        class_ids: Dict[str, int] = {}
        boxes: List[List[float]] = []
        confidences: List[float] = []
        classes: List[int] = []
        for prediction in predictions:
            if not isinstance(prediction, dict):
                raise RuntimeError("Roboflow returned a malformed prediction.")
            class_name = str(prediction.get("class", "")).strip().lower()
            if not class_name:
                raise RuntimeError("Roboflow prediction is missing its class name.")
            class_id = prediction.get("class_id")
            if class_id is None:
                class_id = class_ids.setdefault(class_name, len(class_ids))
            else:
                class_id = int(class_id)

            try:
                center_x = float(prediction["x"])
                center_y = float(prediction["y"])
                width = float(prediction["width"])
                height = float(prediction["height"])
                confidence = float(prediction["confidence"])
            except (KeyError, TypeError, ValueError) as error:
                raise RuntimeError("Roboflow returned a prediction with invalid box data.") from error

            names[class_id] = class_name
            boxes.append([
                center_x - width / 2,
                center_y - height / 2,
                center_x + width / 2,
                center_y + height / 2,
            ])
            confidences.append(confidence)
            classes.append(class_id)

        result_boxes = _RoboflowBoxes(boxes, confidences, classes)
        return [SimpleNamespace(boxes=result_boxes, names=names)]


@lru_cache(maxsize=2)
def load_yolo_model(custom_path: Optional[str] = None) -> Any:
    """Load configured Roboflow inference or fall back to local YOLO weights."""
    if settings.roboflow_model_id.strip():
        if not settings.roboflow_api_key.strip():
            raise RuntimeError("ROBOFLOW_API_KEY is required when ROBOFLOW_MODEL_ID is configured.")
        return _RoboflowHostedModel()
    if settings.roboflow_api_key.strip():
        logger.warning("ROBOFLOW_API_KEY is set but ROBOFLOW_MODEL_ID is missing; using local YOLO weights.")
    if YOLO is None:
        raise RuntimeError(
            "Vision detection is unavailable because ultralytics is not installed. "
            "Install backend requirements to enable image and video analysis."
        )
    weights_path = _resolve_model_path(custom_path)
    return YOLO(weights_path)


def _build_detection_from_result(
    result: Any,
    tracker: Optional[CentroidTracker] = None,
    frame_index: int = 0,
) -> List[Detection]:
    """Convert YOLO bounding boxes into Detection objects and apply simple tracking."""
    detections: List[Detection] = []
    if result is None or getattr(result, "boxes", None) is None:
        if tracker is not None:
            tracker.update([])
        return detections

    boxes = result.boxes
    if len(boxes) == 0:
        if tracker is not None:
            tracker.update([])
        return detections

    tracked_inputs: List[Tuple[int, int, float, float]] = []
    detection_box_indices: List[int] = []

    for i in range(len(boxes)):
        xyxy = boxes.xyxy[i].tolist()
        conf = float(boxes.conf[i].item())
        cls_id = int(boxes.cls[i].item())

        class_name = getattr(result, "names", {}).get(cls_id, str(cls_id)).lower()
        normalized_name = _normalize_class_name(class_name)
        if normalized_name not in {"car", "truck", "bus", "bike", "pedestrian", "pothole"}:
            continue
        if conf < CLASS_CONFIDENCE_THRESHOLDS[normalized_name]:
            continue

        x1, y1, x2, y2 = xyxy
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        tracked_inputs.append((i, cls_id, float(cx), float(cy)))
        detection_box_indices.append(i)
        detections.append(
            Detection(
                class_name=normalized_name,
                confidence=round(conf, 4),
                bbox=[float(x1), float(y1), float(x2), float(y2)],
                track_id=None,
            )
        )

    if tracker is not None:
        tracker_map = tracker.update(tracked_inputs)
        for detection, box_index in zip(detections, detection_box_indices):
            detection.track_id = tracker_map.get(box_index)

    return detections


def _draw_boxes(frame: np.ndarray, detections: Iterable[Detection]) -> np.ndarray:
    """Draw bounding boxes and object labels on a frame for visualization."""
    output = frame.copy()
    for detection in detections:
        x1, y1, x2, y2 = [int(v) for v in detection.bbox[:4]]
        color = {
            "car": (0, 255, 0),
            "truck": (0, 128, 255),
            "bus": (255, 128, 0),
            "bike": (255, 0, 255),
            "pedestrian": (0, 255, 255),
            "pothole": (255, 0, 0),
        }.get(detection.class_name, (255, 255, 255))

        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
        label = f"{detection.class_name} {detection.confidence:.2f}"
        if detection.track_id is not None:
            label = f"{label} ID:{detection.track_id}"
        cv2.putText(output, label, (x1, max(0, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    return output


def process_frame(
    frame: np.ndarray,
    model: Optional[Any] = None,
    tracker: Optional[CentroidTracker] = None,
    source_name: str = "frame",
    inference_size: int = 640,
) -> DetectionResponse:
    """Process a single image frame and return all detected objects with tracking IDs."""
    current_model = model or load_yolo_model()
    results = current_model(frame, conf=0.25, verbose=False, imgsz=inference_size)[0]
    detections = _build_detection_from_result(results, tracker=tracker, frame_index=0)
    annotated_frame = _draw_boxes(frame, detections)
    return DetectionResponse(
        detections=detections,
        frame_metadata={
            "source": source_name,
            "frame_width": int(frame.shape[1]),
            "frame_height": int(frame.shape[0]),
            "frame_count": 1,
            "annotated_frame_available": True,
            "annotation_shape": list(annotated_frame.shape),
        },
    )


def process_video_file(
    video_path: str | Path,
    model: Optional[Any] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> DetectionResponse:
    """Process a full video file frame by frame and aggregate detections across the clip."""
    path = Path(video_path)
    if progress_callback:
        progress_callback(1, "Loading detection model")
    current_model = model or load_yolo_model()
    tracker = CentroidTracker()
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise FileNotFoundError(f"Unable to open video: {path}")

    all_detections: List[Detection] = []
    frame_count = 0
    frames_per_second = capture.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    max_sampled_frames = 24
    base_interval = max(1, round(frames_per_second / 2.5))
    if total_frames:
        desired_samples = min(max_sampled_frames, max(1, math.ceil(total_frames / base_interval)))
        sampled_indices = np.linspace(0, max(0, total_frames - 1), num=desired_samples, dtype=int).tolist()
        sample_interval = max(1, round(total_frames / max(1, desired_samples - 1))) if desired_samples > 1 else total_frames
        if progress_callback:
            progress_callback(4, f"Analyzing {desired_samples} sampled frames")
        for sample_number, frame_index in enumerate(sampled_indices, start=1):
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            success, frame = capture.read()
            if not success:
                continue
            response = process_frame(
                frame,
                model=current_model,
                tracker=tracker,
                source_name=str(path.name),
                inference_size=512,
            )
            for detection in response.detections:
                detection.frame_index = frame_index + 1
            all_detections.extend(response.detections)
            if progress_callback:
                progress_callback(min(94, 4 + round(90 * sample_number / desired_samples)), "Analyzing sampled frames")
        frame_count = total_frames
    else:
        if progress_callback:
            progress_callback(4, "Analyzing sampled frames")
        samples_processed = 0
        while samples_processed < max_sampled_frames:
            frame_index = frame_count
            success, frame = capture.read()
            if not success:
                break
            frame_count += 1
            if frame_index % base_interval:
                continue
            response = process_frame(frame, model=current_model, tracker=tracker, source_name=str(path.name), inference_size=512)
            for detection in response.detections:
                detection.frame_index = frame_index + 1
            all_detections.extend(response.detections)
            samples_processed += 1
        sample_interval = base_interval

    if progress_callback:
        progress_callback(97, "Finalizing detections")

    frame_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    capture.release()

    return DetectionResponse(
        detections=all_detections,
        frame_metadata={
            "source": str(path.name),
            "video_path": str(path),
            "frame_count": frame_count,
            "frames_per_second": float(frames_per_second),
            "sample_interval": sample_interval,
            "frame_width": frame_width,
            "frame_height": frame_height,
            "track_count": len({detection.track_id for detection in all_detections if detection.track_id is not None}),
            "total_objects_detected": len(all_detections),
        },
    )


def detect_objects(frame: np.ndarray, model: Optional[Any] = None) -> Dict[str, Any]:
    """Compatibility wrapper that returns a simple object list for external callers."""
    response = process_frame(frame, model=model, source_name="frame")
    return {
        "objects": [
            {
                "class_name": detection.class_name,
                "confidence": detection.confidence,
                "bbox": detection.bbox,
                "track_id": detection.track_id,
            }
            for detection in response.detections
        ],
        "frame_metadata": response.frame_metadata,
    }


def get_detection_summary(camera_id: str) -> Dict[str, Any]:
    """Return the latest camera summary until a live camera store is connected."""
    return {
        "camera_id": camera_id,
        "status": "stub",
        "latest_summary": {
            "total_detections": 0,
            "cars": 0,
            "trucks": 0,
            "buses": 0,
            "bikes": 0,
            "pedestrians": 0,
            "potholes": 0,
        },
        "message": "Live camera integration is still mocked for this phase.",
    }
