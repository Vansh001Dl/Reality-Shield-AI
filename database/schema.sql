CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(320) NOT NULL UNIQUE,
    full_name VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    role VARCHAR(32) NOT NULL DEFAULT 'viewer'
);

CREATE TABLE IF NOT EXISTS detections (
    id BIGSERIAL PRIMARY KEY,
    camera_id VARCHAR(100) NOT NULL,
    source_name VARCHAR(255),
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_detections INTEGER NOT NULL DEFAULT 0 CHECK (total_detections >= 0),
    objects JSONB NOT NULL DEFAULT '[]'::jsonb,
    location GEOGRAPHY(POINT, 4326)
);

CREATE TABLE IF NOT EXISTS risk_scores (
    id BIGSERIAL PRIMARY KEY,
    camera_id VARCHAR(100) NOT NULL,
    detection_id BIGINT REFERENCES detections(id) ON DELETE SET NULL,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    score NUMERIC(4, 3) NOT NULL CHECK (score BETWEEN 0 AND 1),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'moderate', 'high', 'critical')),
    confidence NUMERIC(4, 3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    factors JSONB NOT NULL DEFAULT '{}'::jsonb,
    recommendations JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS route_history (
    id BIGSERIAL PRIMARY KEY,
    route_id VARCHAR(100) NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    start_label VARCHAR(255),
    end_label VARCHAR(255),
    risk_score NUMERIC(4, 3) NOT NULL CHECK (risk_score BETWEEN 0 AND 1),
    route_data JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    camera_id VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    alert_type VARCHAR(50) NOT NULL,
    level VARCHAR(20) NOT NULL CHECK (level IN ('low', 'moderate', 'high', 'critical')),
    message TEXT NOT NULL,
    acknowledged_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_detections_camera_time ON detections(camera_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_risk_scores_camera_time ON risk_scores(camera_id, calculated_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);

CREATE TABLE IF NOT EXISTS video_analysis_history (
    id BIGSERIAL PRIMARY KEY,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_name VARCHAR(255) NOT NULL,
    location_name VARCHAR(255),
    total_detections INTEGER NOT NULL DEFAULT 0,
    vehicle_count INTEGER NOT NULL DEFAULT 0,
    pedestrian_count INTEGER NOT NULL DEFAULT 0,
    pothole_count INTEGER NOT NULL DEFAULT 0,
    risk_score NUMERIC(4, 3) NOT NULL CHECK (risk_score BETWEEN 0 AND 1),
    severity VARCHAR(20) NOT NULL,
    route_risk NUMERIC(4, 3) NOT NULL DEFAULT 0 CHECK (route_risk BETWEEN 0 AND 1)
);

CREATE INDEX IF NOT EXISTS idx_video_history_analyzed_at ON video_analysis_history(analyzed_at DESC);
