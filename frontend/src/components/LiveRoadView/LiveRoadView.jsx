import React, { useCallback, useEffect, useRef, useState } from 'react';
import api, { videoApi } from '../../services/api';

function LiveRoadView({ onAnalysisComplete, onAnalysisReset }) {
  const [videoUrl, setVideoUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileName, setFileName] = useState('No recording selected');
  const [analysisStatus, setAnalysisStatus] = useState('Choose a recording to begin analysis');
  const [locationStatus, setLocationStatus] = useState('');
  const [playbackStatus, setPlaybackStatus] = useState('');
  const [locationQuery, setLocationQuery] = useState('');
  const [location, setLocation] = useState(null);
  const [savedDatasets, setSavedDatasets] = useState([]);
  const [archiveStatus, setArchiveStatus] = useState('Loading saved videos...');
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const locationRef = useRef(null);
  const inputRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const analysisCompleteRef = useRef(false);
  const hasUserSelectedVideoRef = useRef(false);
  const [analysis, setAnalysis] = useState({ detections: [], metadata: null });
  const [analysisProgress, setAnalysisProgress] = useState(null);
  const jobRequestRef = useRef(0);

  useEffect(() => () => videoUrl && URL.revokeObjectURL(videoUrl), [videoUrl]);

  const restoreDataset = useCallback(async (datasetId) => {
    const requestId = ++jobRequestRef.current;
    setSelectedDatasetId(datasetId);
    setAnalysisProgress({ percentage: 0, phase: 'Loading saved analysis', done: false });
    setAnalysisStatus('Loading saved video and detections...');
    try {
      const { data: dataset } = await api.get(`/api/detect/video/datasets/${datasetId}`);
      if (requestId !== jobRequestRef.current) return;

      const nextVideoUrl = new URL(
        `/api/detect/video/datasets/${datasetId}/video`,
        videoApi.defaults.baseURL,
      ).toString();
      setVideoUrl(nextVideoUrl);
      setFileName(dataset.source_name);
      setSelectedFile(null);
      setLocationQuery(dataset.location.label);
      locationRef.current = dataset.location;
      setLocation(dataset.location);
      setAnalysis({
        detections: dataset.result?.detections || [],
        metadata: dataset.result?.frame_metadata || null,
      });
      analysisCompleteRef.current = true;
      setAnalysisProgress(null);
      setAnalysisStatus(`Restored saved analysis from ${new Date(dataset.analyzed_at).toLocaleString()}`);
      setPlaybackStatus('');
      onAnalysisComplete?.({
        fileName: dataset.source_name,
        detections: dataset.result?.detections || [],
        metadata: dataset.result?.frame_metadata || null,
        location: dataset.location,
        datasetId,
        archived: true,
      });
    } catch (error) {
      if (requestId !== jobRequestRef.current) return;
      const detail = error.response?.data?.detail || error.message || 'Could not load this saved dataset.';
      setAnalysisProgress(null);
      setArchiveStatus(`Cloud archive unavailable: ${detail}`);
      setAnalysisStatus('No saved analysis available yet. Upload a video to start from scratch.');
    }
  }, [onAnalysisComplete]);

  useEffect(() => {
    let active = true;
    api.get('/api/detect/video/datasets?limit=50')
      .then(({ data }) => {
        if (!active) return;
        const datasets = data.datasets || [];
        setSavedDatasets(datasets);
        const localCount = datasets.filter((dataset) => dataset.storage_backend === 'local').length;
        const cloudCount = datasets.length - localCount;
        if (!datasets.length) {
          setArchiveStatus('No saved videos yet');
        } else if (localCount && cloudCount) {
          setArchiveStatus(`${cloudCount} saved in cloud · ${localCount} saved locally`);
        } else if (localCount) {
          setArchiveStatus(`${localCount} saved video${localCount === 1 ? '' : 's'} available locally · cloud archive unavailable`);
        } else {
          setArchiveStatus(`${cloudCount} saved video${cloudCount === 1 ? '' : 's'} in cloud archive`);
        }
        if (datasets[0] && !hasUserSelectedVideoRef.current) {
          restoreDataset(datasets[0].dataset_id);
        }
      })
      .catch((error) => {
        if (!active) return;
        const detail = error.response?.data?.detail || 'Check your S3 bucket and AWS credentials.';
        setArchiveStatus(`Cloud archive unavailable: ${detail}`);
        setAnalysisProgress(null);
      });
    return () => { active = false; };
  }, [restoreDataset]);

  const handleVideoSelect = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    jobRequestRef.current += 1;
    hasUserSelectedVideoRef.current = true;
    setSelectedDatasetId('');
    if (videoUrl) URL.revokeObjectURL(videoUrl);
    setVideoUrl(URL.createObjectURL(file));
    setFileName(file.name);
    setSelectedFile(file);
    setAnalysis({ detections: [], metadata: null });
    onAnalysisReset?.();
    analysisCompleteRef.current = false;
    setAnalysisProgress(null);
    setAnalysisStatus(locationRef.current ? 'Starting video analysis...' : 'Confirm the recording location to start analysis');
    setPlaybackStatus('Starting playback...');
  };

  const analyzeSelectedVideo = useCallback(() => {
    if (!selectedFile || !location) return;

    const file = selectedFile;
    const videoLocation = location;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('location', videoLocation.label);
    formData.append('latitude', String(videoLocation.latitude));
    formData.append('longitude', String(videoLocation.longitude));
    const requestId = ++jobRequestRef.current;
    setAnalysisProgress({ percentage: 0, phase: 'Preparing upload', done: false });
    setAnalysisStatus('Uploading video...');

    const trackAnalysisJob = async () => {
      try {
        const { data: createdJob } = await videoApi.post('/api/detect/video/jobs', formData, {
          timeout: 0,
          onUploadProgress: (uploadEvent) => {
            if (requestId !== jobRequestRef.current) return;
            const percentage = uploadEvent.total ? Math.round((uploadEvent.loaded / uploadEvent.total) * 100) : 0;
            setAnalysisProgress({ percentage, phase: 'Uploading video', done: false });
          },
        });
        if (requestId !== jobRequestRef.current) return;
        setAnalysisStatus('Video uploaded · starting analysis');

        while (requestId === jobRequestRef.current) {
          const { data: job } = await videoApi.get(`/api/detect/video/jobs/${createdJob.job_id}`);
          if (requestId !== jobRequestRef.current) return;
          setAnalysisProgress({ percentage: job.progress || 0, phase: job.phase || 'Analyzing video', done: job.status === 'completed' || job.status === 'failed' });
          if (job.status === 'failed') throw new Error(job.error || 'Video analysis failed.');
          if (job.status === 'completed') {
            const detections = job.result?.detections || [];
            const metadata = job.result?.frame_metadata || null;
            if (job.dataset) {
              setSavedDatasets((previous) => [
                job.dataset,
                ...previous.filter((item) => item.dataset_id !== job.dataset_id),
              ].slice(0, 50));
              setSelectedDatasetId(job.dataset_id);
              setArchiveStatus(job.dataset.storage_backend === 'local'
                ? 'Video and analysis saved locally (cloud archive unavailable)'
                : 'Video and analysis saved to the cloud archive');
            }
            analysisCompleteRef.current = true;
            setAnalysis({ detections, metadata });
            setAnalysisStatus(`Analysis complete · ${detections.length} detections · dashboard updated`);
            onAnalysisComplete?.({
              fileName: file.name,
              detections,
              metadata,
              location: videoLocation,
              datasetId: job.dataset_id,
            });
            return;
          }
          await new Promise((resolve) => window.setTimeout(resolve, 500));
        }
      } catch (error) {
        if (requestId !== jobRequestRef.current) return;
        const detail = error.response?.data?.detail || error.message || `analysis request failed (${error.code || 'network error'})`;
        setAnalysisProgress((current) => current ? { ...current, phase: 'Analysis failed', done: true, failed: true } : current);
        setAnalysisStatus(`Playback ready · analysis failed: ${detail}`);
      }
    };
    trackAnalysisJob();
  }, [location, onAnalysisComplete, selectedFile]);

  useEffect(() => {
    if (selectedFile && location && !analysisProgress) {
      analyzeSelectedVideo();
    }
  }, [analysisProgress, analyzeSelectedVideo, location, selectedFile]);

  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !analysis.metadata?.frame_width || !analysis.metadata?.frame_height) return undefined;

    const context = canvas.getContext('2d');
    let animationFrame;
    const draw = () => {
      const width = video.clientWidth;
      const height = video.clientHeight;
      if (width && height) {
        const pixelRatio = window.devicePixelRatio || 1;
        canvas.width = Math.round(width * pixelRatio);
        canvas.height = Math.round(height * pixelRatio);
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
        context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
        context.clearRect(0, 0, width, height);

        const fps = analysis.metadata.frames_per_second || 25;
        const interval = analysis.metadata.sample_interval || 1;
        const frame = Math.round(video.currentTime * fps);
        const selected = analysis.detections.filter((item) => item.frame_index != null && Math.abs(item.frame_index - frame) <= interval / 2);
        const scaleX = width / analysis.metadata.frame_width;
        const scaleY = height / analysis.metadata.frame_height;
        selected.forEach((item) => {
          const [x1, y1, x2, y2] = item.bbox || [];
          if ([x1, y1, x2, y2].some((value) => !Number.isFinite(value))) return;
          const color = item.class_name === 'pothole' || item.class_name === 'pedestrian' ? '#ff557b' : '#42f0d2';
          const x = x1 * scaleX;
          const y = y1 * scaleY;
          const boxWidth = (x2 - x1) * scaleX;
          const boxHeight = (y2 - y1) * scaleY;
          const label = `${item.class_name} ${Math.round((item.confidence || 0) * 100)}%`;
          context.strokeStyle = color;
          context.lineWidth = 2;
          context.strokeRect(x, y, boxWidth, boxHeight);
          context.font = '600 11px Inter, Arial, sans-serif';
          const labelWidth = context.measureText(label).width + 8;
          context.fillStyle = color;
          context.fillRect(x, Math.max(0, y - 18), labelWidth, 18);
          context.fillStyle = '#031225';
          context.fillText(label, x + 4, Math.max(12, y - 5));
        });
      }
      if (!video.paused && !video.ended) animationFrame = requestAnimationFrame(draw);
    };
    const start = () => { cancelAnimationFrame(animationFrame); draw(); };
    video.addEventListener('timeupdate', start);
    video.addEventListener('seeked', start);
    video.addEventListener('loadedmetadata', start);
    video.addEventListener('play', start);
    window.addEventListener('resize', start);
    start();
    return () => {
      cancelAnimationFrame(animationFrame);
      video.removeEventListener('timeupdate', start);
      video.removeEventListener('seeked', start);
      video.removeEventListener('loadedmetadata', start);
      video.removeEventListener('play', start);
      window.removeEventListener('resize', start);
    };
  }, [videoUrl, analysis]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !videoUrl) return undefined;
    const startPlayback = () => {
      video.play().then(() => setPlaybackStatus('Playing automatically Â· muted')).catch(() => {
        setPlaybackStatus('Ready Â· press play to start');
      });
    };
    video.addEventListener('canplay', startPlayback, { once: true });
    if (video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) startPlayback();
    return () => video.removeEventListener('canplay', startPlayback);
  }, [videoUrl]);

  const chooseVideo = () => {
    // Clear the value so selecting the same file after a failed request triggers change again.
    if (inputRef.current) inputRef.current.value = '';
    inputRef.current?.click();
  };

  const handleLocationChange = (event) => {
    const value = event.target.value;
    jobRequestRef.current += 1;
    if (locationRef.current) onAnalysisReset?.();
    setLocationQuery(value);
    locationRef.current = null;
    setLocation(null);
    setAnalysis({ detections: [], metadata: null });
    setAnalysisProgress(null);
    analysisCompleteRef.current = false;
    setLocationStatus(value.trim() ? 'Confirm this location to enable video analysis.' : '');
    if (selectedFile) setAnalysisStatus('Analysis is waiting for a confirmed location');
  };

  const resolveLocation = async () => {
    if (!locationQuery.trim()) return;
    setLocationStatus('Finding location...');
    try {
      const response = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=in&q=${encodeURIComponent(locationQuery)}`);
      const results = await response.json();
      if (!results.length) throw new Error('Location not found');
      const result = results[0];
      const resolved = { label: result.display_name.split(',').slice(0, 2).join(','), latitude: Number(result.lat), longitude: Number(result.lon) };
      locationRef.current = resolved;
      setLocation(resolved);
      setLocationStatus('Location confirmed');
      if (selectedFile) setAnalysisStatus('Starting video analysis...');
    } catch {
      locationRef.current = null;
      setLocation(null);
      setLocationStatus('Location not found. Try a city, road, or landmark');
    }
  };

  return (
    <section className="panel">
      <div className="video-heading">
        <div>
          <h2 className="card-title">Recorded Road Video</h2>
          <p className="video-file-name">{fileName} Â· {analysisStatus}{playbackStatus ? ` Â· ${playbackStatus}` : ''}</p>
        </div>
        <button type="button" className="upload-button" onClick={chooseVideo}>
          Choose video
        </button>
        {savedDatasets.length > 0 && (
          <select
            className="saved-video-select"
            aria-label="Load a saved video analysis"
            value={selectedDatasetId}
            onChange={(event) => event.target.value && restoreDataset(event.target.value)}
          >
            <option value="">Saved videos ({savedDatasets.length})</option>
            {savedDatasets.map((dataset) => (
              <option key={dataset.dataset_id} value={dataset.dataset_id}>
                {dataset.source_name} · {new Date(dataset.analyzed_at).toLocaleDateString()}
              </option>
            ))}
          </select>
        )}
        <input
          ref={inputRef}
          className="visually-hidden"
          type="file"
          accept="video/*"
          onChange={handleVideoSelect}
        />
      </div>

      <div className="video-location-form">
        <label htmlFor="video-location">Where was this video recorded?</label>
        <div className="location-input-row">
          <input id="video-location" value={locationQuery} onChange={handleLocationChange} onKeyDown={(event) => event.key === 'Enter' && resolveLocation()} placeholder="City, road, or landmark" />
          <button type="button" className="upload-button" onClick={resolveLocation} disabled={!locationQuery.trim() || locationStatus === 'Finding location...'}>Set location</button>
        </div>
        {(location || locationStatus || selectedFile) && <span className={`location-confirmed ${location ? 'location-ready' : 'location-pending'}`}>{location ? `Confirmed: ${location.label}` : locationStatus || (selectedFile ? 'Confirm a location to enable analysis.' : '')}</span>}
      </div>

      <p className="archive-status" role="status" aria-live="polite">{archiveStatus}</p>

      {analysisProgress && <div className={`analysis-progress ${analysisProgress.failed ? 'failed' : ''}`} role="status" aria-live="polite">
        <div className="analysis-progress-heading"><span>{analysisProgress.phase}</span><strong>{analysisProgress.percentage}%</strong></div>
        <div className="analysis-progress-track"><span style={{ width: `${analysisProgress.percentage}%` }} /></div>
      </div>}
      {analysisProgress?.failed && selectedFile && location && <button type="button" className="upload-button" onClick={() => setAnalysisProgress(null)}>Retry analysis</button>}

      <div className="road-view recorded-video-view">
        {videoUrl ? (
          <div className="video-overlay-stage" style={analysis.metadata?.frame_width ? { aspectRatio: `${analysis.metadata.frame_width} / ${analysis.metadata.frame_height}` } : undefined}>
            <video ref={videoRef} className="recorded-video" src={videoUrl} controls autoPlay muted playsInline preload="auto"
              onEnded={() => setPlaybackStatus(analysisCompleteRef.current ? 'Video finished Â· dashboard results updated' : 'Video finished Â· analysis is still running')}
              onPlay={() => setPlaybackStatus('Playing automatically Â· muted')}
              onVolumeChange={(event) => event.currentTarget.muted && !event.currentTarget.paused && setPlaybackStatus('Playing Â· muted')}
            />
            <canvas ref={canvasRef} className="detection-overlay" aria-label="Object detection overlay" />
          </div>
        ) : (
          <div className="video-empty-state">
            <strong>Select a recorded road video</strong>
            <span>Playback and analysis results will use this recording.</span>
          </div>
        )}
      </div>
    </section>
  );
}

export default LiveRoadView;
