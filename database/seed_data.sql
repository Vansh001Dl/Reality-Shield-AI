INSERT INTO route_history (route_id, start_label, end_label, risk_score, route_data)
VALUES
  ('route_a', 'North Gate', 'City Centre', 0.210, '{"traffic_density": 0.2, "potholes": 0.1}'::jsonb),
  ('route_b', 'North Gate', 'City Centre', 0.670, '{"traffic_density": 0.8, "potholes": 0.8}'::jsonb)
ON CONFLICT DO NOTHING;

INSERT INTO alerts (camera_id, alert_type, level, message, metadata)
VALUES ('cam_01', 'risk', 'high', 'Traffic density is elevated near the monitored corridor.', '{"zone": "north_corridor"}'::jsonb)
ON CONFLICT DO NOTHING;
