from app.core.celery_app import celery_app


@celery_app.task(name="realityshield.health_check")
def health_check_task():
    return {"status": "ok"}


@celery_app.task(name="realityshield.process_video")
def process_video_task(job_id, temp_path, file_name, location):
    from app.api.routes_detection import _run_video_analysis
    _run_video_analysis(job_id, temp_path, file_name, location)
    return {"job_id": job_id, "status": "finished"}
