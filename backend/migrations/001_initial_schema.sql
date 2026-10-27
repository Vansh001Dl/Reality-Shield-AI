-- RealityShield-AI initial schema for PostgreSQL/PostGIS-backed deployment.
-- This file is intentionally compatible with the backend's SQLite fallback for local testing.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS video_jobs (
    id VARCHAR(64) PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    dataset_id VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    progress INTEGER NOT NULL DEFAULT 0,
    phase VARCHAR(128) NOT NULL DEFAULT 'queued',
    location_label VARCHAR(255) NOT NULL DEFAULT 'unknown',
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    source_path VARCHAR(512),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_video_jobs_status ON video_jobs(status);
CREATE INDEX IF NOT EXISTS idx_video_jobs_dataset_id ON video_jobs(dataset_id);

CREATE TABLE IF NOT EXISTS detection_records (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(64) NOT NULL REFERENCES video_jobs(id) ON DELETE CASCADE,
    frame_index INTEGER NOT NULL DEFAULT 0,
    class_name VARCHAR(64) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    bbox_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    track_id INTEGER,
    timestamp_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_detection_records_job_id ON detection_records(job_id);
CREATE INDEX IF NOT EXISTS idx_detection_records_class_name ON detection_records(class_name);
CREATE INDEX IF NOT EXISTS idx_detection_records_track_id ON detection_records(track_id);

CREATE TABLE IF NOT EXISTS risk_assessments (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(64) NOT NULL REFERENCES video_jobs(id) ON DELETE CASCADE,
    camera_id VARCHAR(128) NOT NULL DEFAULT 'recorded_video',
    score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    severity VARCHAR(32) NOT NULL DEFAULT 'unknown',
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    factors_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary TEXT,
    model_version VARCHAR(128) NOT NULL DEFAULT 'rule_based_v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_assessments_job_id ON risk_assessments(job_id);

CREATE TABLE IF NOT EXISTS route_analyses (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(64) REFERENCES video_jobs(id) ON DELETE SET NULL,
    start_label VARCHAR(255) NOT NULL,
    end_label VARCHAR(255) NOT NULL,
    recommended_route JSONB NOT NULL DEFAULT '{}'::jsonb,
    alternatives_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    risk_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    travel_time_seconds INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_records (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(64) REFERENCES video_jobs(id) ON DELETE SET NULL,
    alert_type VARCHAR(64) NOT NULL DEFAULT 'risk',
    level VARCHAR(32) NOT NULL DEFAULT 'info',
    message TEXT NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_records_job_id ON alert_records(job_id);
CREATE INDEX IF NOT EXISTS idx_alert_records_created_at ON alert_records(created_at DESC);
