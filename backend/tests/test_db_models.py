from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import AlertRecord, DetectionRecord, RiskAssessment, VideoJob


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_video_job_and_detections_can_be_persisted():
    session = _make_session()

    job = VideoJob(
        id="job_123",
        file_name="sample.mp4",
        status="queued",
        phase="Queued for analysis",
        location_label="Dwarka",
        latitude=28.6,
        longitude=77.2,
        metadata_json={"source": "sample"},
    )
    session.add(job)
    session.commit()

    detection = DetectionRecord(
        job_id="job_123",
        frame_index=3,
        class_name="car",
        confidence=0.88,
        bbox_json=[1, 2, 3, 4],
        track_id=21,
    )
    session.add(detection)
    session.commit()

    assessment = RiskAssessment(
        job_id="job_123",
        camera_id="recorded_video",
        score=0.61,
        severity="medium",
        confidence=0.82,
        factors_json={"traffic_density": 0.7},
        summary="Moderate congestion observed.",
    )
    session.add(assessment)
    session.commit()

    alert = AlertRecord(
        job_id="job_123",
        alert_type="risk",
        level="medium",
        message="Traffic density is elevated.",
        acknowledged=0,
    )
    session.add(alert)
    session.commit()

    saved_job = session.get(VideoJob, "job_123")
    assert saved_job is not None
    assert saved_job.file_name == "sample.mp4"
    assert len(saved_job.detections) == 1
    assert saved_job.assessments[0].severity == "medium"
    assert saved_job.alerts[0].message == "Traffic density is elevated."

    session.close()
