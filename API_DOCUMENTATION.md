# PV-Hawk REST API Documentation

This document provides comprehensive documentation for the PV-Hawk REST API, which allows external systems to control and monitor PV-Hawk processing tasks through HTTP requests.

## 🚀 Quick Start

### 1. Installation

Install API dependencies:
```bash
pip install -r api/requirements.txt
```

### 2. Start the API Server

```bash
# Start with default settings
python start_api.py

# Start with custom configuration
python start_api.py --host 0.0.0.0 --port 8000 --workers 4

# Development mode with auto-reload
python start_api.py --reload

# With SSL (production)
python start_api.py --ssl-keyfile /path/to/key.pem --ssl-certfile /path/to/cert.pem
```

### 3. Access API Documentation

- **Interactive Docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.json

## 📚 API Overview

### Base URL
```
http://localhost:8000
```

### Authentication
The API supports optional authentication via:
- **API Key**: Set `API_KEY` environment variable
- **JWT Bearer Token**: For more advanced authentication

### Response Format
All API responses follow this structure:
```json
{
  "status": "success|error",
  "data": {...},
  "message": "Human readable message",
  "timestamp": "2023-12-01T10:30:00Z"
}
```

## 🔍 API Endpoints

### Health & System Information

#### GET /health
Check API server health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-12-01T10:30:00Z",
  "version": "2.0.0",
  "gpu_available": true
}
```

#### GET /system/info
Get detailed system information.

**Response:**
```json
{
  "python_version": "3.9.10",
  "tensorflow_version": "2.14.0",
  "gpu_available": true,
  "gpu_count": 1,
  "gpu_names": ["NVIDIA GeForce RTX 4060"],
  "cpu_count": 8,
  "memory_total_gb": 16.0,
  "disk_space_gb": 500.0
}
```

#### GET /system/gpu
Get detailed GPU information.

**Response:**
```json
{
  "gpu_available": true,
  "gpu_count": 1,
  "gpus": [
    {
      "index": 0,
      "name": "NVIDIA GeForce RTX 4060",
      "memory_total": 8589934592,
      "memory_used": 1073741824,
      "memory_free": 7516192768
    }
  ],
  "cuda_version": "12.1"
}
```

### Configuration Management

#### GET /config/defaults
Get default configuration settings.

**Response:** Returns the complete default configuration structure.

#### POST /config/validate
Validate a pipeline configuration.

**Request Body:**
```json
{
  "plant_name": "Test Installation",
  "groups": [...],
  "tasks": ["split_sequences", "segment_pv_modules"],
  "settings": {...}
}
```

**Response:**
```json
{
  "valid": true,
  "message": "Configuration is valid",
  "errors": []
}
```

### Pipeline Processing

#### POST /pipeline/run
Run the complete PV-Hawk processing pipeline.

**Request Body:**
```json
{
  "config": {
    "plant_name": "Solar Installation",
    "groups": [
      {
        "cam_params_dir": "/calibration",
        "ir_or_rgb": "ir",
        "clusters": [
          {
            "cluster_idx": 0,
            "frame_idx_start": 0,
            "frame_idx_end": 1000
          }
        ],
        "settings": {
          "segment_pv_modules": {
            "gpu_count": 1,
            "images_per_gpu": 2,
            "detection_min_confidence": 0.9
          }
        }
      }
    ],
    "tasks": [
      "split_sequences",
      "segment_pv_modules",
      "track_pv_modules",
      "compute_pv_module_quadrilaterals"
    ]
  },
  "work_dir": "/path/to/work/directory"
}
```

**Response:**
```json
{
  "job_id": "uuid-string",
  "message": "Pipeline started successfully"
}
```

#### POST /pipeline/step/{step_name}
Run a specific pipeline step.

**Valid Step Names:**
- `split_sequences`
- `interpolate_gps`
- `segment_pv_modules`
- `track_pv_modules`
- `compute_pv_module_quadrilaterals`
- `prepare_opensfm`
- `opensfm_extract_metadata`
- `opensfm_detect_features`
- `opensfm_match_features`
- `opensfm_create_tracks`
- `opensfm_reconstruct`
- `triangulate_pv_modules`
- `refine_triangulation`
- `crop_pv_modules`

**Request Body:**
```json
{
  "config": {
    "ir_or_rgb": "ir",
    "settings": {
      "segment_pv_modules": {
        "gpu_count": 1,
        "images_per_gpu": 2,
        "detection_min_confidence": 0.9
      }
    }
  },
  "work_dir": "/path/to/work/directory",
  "group_name": "group_001"
}
```

### Inference Processing

#### POST /inference/segment
Run PV module segmentation on a set of images.

**Request Body:**
```json
{
  "frames_root": "/path/to/input/frames",
  "output_dir": "/path/to/output",
  "ir_or_rgb": "ir",
  "settings": {
    "gpu_count": 1,
    "images_per_gpu": 2,
    "detection_min_confidence": 0.9,
    "weights_file_ir": "/models/mask_rcnn_pv_modules_0120.h5"
  }
}
```

### Job Management

#### GET /jobs
List all jobs with their current status.

**Response:**
```json
[
  {
    "job_id": "uuid-string",
    "job_type": "full_pipeline",
    "status": "running",
    "created_at": "2023-12-01T10:00:00Z",
    "started_at": "2023-12-01T10:01:00Z",
    "completed_at": null,
    "progress": 45,
    "message": "Processing segmentation...",
    "error": null,
    "work_dir": "/path/to/work/directory",
    "group_name": "group_001"
  }
]
```

#### GET /jobs/{job_id}
Get detailed status of a specific job.

**Response:**
```json
{
  "job_id": "uuid-string",
  "job_type": "full_pipeline",
  "status": "completed",
  "created_at": "2023-12-01T10:00:00Z",
  "started_at": "2023-12-01T10:01:00Z",
  "completed_at": "2023-12-01T10:30:00Z",
  "progress": 100,
  "message": "Pipeline completed successfully",
  "error": null,
  "work_dir": "/path/to/work/directory",
  "config": {...}
}
```

#### DELETE /jobs/{job_id}
Cancel a running job.

**Response:**
```json
{
  "message": "Job uuid-string cancelled successfully"
}
```

#### DELETE /jobs
Clear all completed jobs from the queue.

**Response:**
```json
{
  "message": "Cleared 5 completed jobs"
}
```

### Results Management

#### GET /results/{job_id}/summary
Get summary of job results.

**Response:**
```json
{
  "job_id": "uuid-string",
  "work_dir": "/path/to/work/directory",
  "output_directories": [
    "/path/to/work/directory/group_001/segmented",
    "/path/to/work/directory/group_001/tracking"
  ],
  "file_counts": {
    "/path/to/work/directory/group_001/segmented": 1000,
    "/path/to/work/directory/group_001/tracking": 500
  },
  "total_files": 1500
}
```

#### GET /results/{job_id}/files
List all output files created by a job.

**Response:**
```json
[
  "/path/to/work/directory/group_001/segmented/frame_000001.csv",
  "/path/to/work/directory/group_001/segmented/frame_000002.csv",
  "..."
]
```

## 🔧 Configuration Reference

### Complete Pipeline Configuration

```yaml
plant_name: "Solar Installation Name"

groups:
- cam_params_dir: /calibration
  ir_or_rgb: ir  # or "rgb"
  
  clusters:
  - cluster_idx: 0
    frame_idx_start: 0
    frame_idx_end: 1000
  
  settings:
    # Video splitting
    split_sequences:
      ir_file_extension: TIFF
      rgb_file_extension: mov
      extract_timestamps: true
      extract_gps: true
      subsample: null
    
    # PV module segmentation
    segment_pv_modules:
      gpu_count: 1
      images_per_gpu: 2
      detection_min_confidence: 0.9
      weights_file_ir: /models/mask_rcnn_pv_modules_0120.h5
      weights_file_rgb: /models/mask_rcnn_pv_modules_rgb_0059.h5
    
    # Module tracking
    track_pv_modules:
      motion_model: homography
      max_distance: 60
      output_video_fps: 8.0
    
    # OpenSfM reconstruction
    prepare_opensfm:
      select_frames_mode: gps
      frame_selection_gps_distance: 0.75
    
    opensfm:
      matching_gps_distance: 20
      processes: 16
      align_method: orientation_prior

tasks:
  - split_sequences
  - interpolate_gps
  - segment_pv_modules
  - track_pv_modules
  - compute_pv_module_quadrilaterals
  - prepare_opensfm
  - opensfm_extract_metadata
  - opensfm_detect_features
  - opensfm_match_features
  - opensfm_create_tracks
  - opensfm_reconstruct
  - triangulate_pv_modules
  - refine_triangulation
  - crop_pv_modules
```

## 🐍 Python Client Example

```python
import requests
import time

class PVHawkAPIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def run_inference(self, frames_path, output_path, ir_or_rgb="ir"):
        response = requests.post(f"{self.base_url}/inference/segment", json={
            "frames_root": frames_path,
            "output_dir": output_path,
            "ir_or_rgb": ir_or_rgb,
            "settings": {
                "gpu_count": 1,
                "images_per_gpu": 2,
                "detection_min_confidence": 0.9
            }
        })
        return response.json()["job_id"]
    
    def wait_for_completion(self, job_id):
        while True:
            response = requests.get(f"{self.base_url}/jobs/{job_id}")
            status = response.json()
            
            if status["status"] in ["completed", "failed", "cancelled"]:
                return status
            
            time.sleep(5)

# Usage
client = PVHawkAPIClient()
job_id = client.run_inference("/data/frames", "/data/output")
final_status = client.wait_for_completion(job_id)
print(f"Job completed: {final_status['status']}")
```

## 🚢 Docker Deployment

### Updated Docker Compose

```yaml
version: '3.8'

services:
  pv-hawk-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - API_SECRET_KEY=your-secret-key
      - API_KEY=your-api-key
    volumes:
      - ./workdir:/workdir
      - ./data:/data
      - ./models:/models
      - ./config:/config
    command: python start_api.py --host 0.0.0.0 --port 8000
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  pv-hawk-cli:
    build: .
    volumes:
      - ./workdir:/workdir
      - ./data:/data
      - ./models:/models
    command: python main.py /workdir
    profiles: ["cli"]
```

## 🔒 Security Considerations

### Production Deployment

1. **Authentication**: Set strong API keys and JWT secrets
2. **HTTPS**: Use SSL certificates for encrypted communication
3. **Network**: Restrict access using firewalls and VPNs
4. **Input Validation**: All inputs are validated server-side
5. **Resource Limits**: Configure appropriate CPU/GPU/memory limits

### Environment Variables

```bash
# Required for production
export API_SECRET_KEY="your-very-secure-secret-key"
export API_KEY="your-api-key"

# Optional
export TF_FORCE_GPU_ALLOW_GROWTH=true
export CUDA_VISIBLE_DEVICES=0
```

## 🐛 Troubleshooting

### Common Issues

1. **ImportError: No module named 'fastapi'**
   ```bash
   pip install -r api/requirements.txt
   ```

2. **GPU not available**
   - Check NVIDIA drivers: `nvidia-smi`
   - Verify TensorFlow GPU: `python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"`

3. **Permission denied errors**
   ```bash
   chmod +x start_api.py
   sudo chown -R $USER:$USER /workdir /data /models
   ```

4. **Port already in use**
   ```bash
   python start_api.py --port 8001
   ```

### Monitoring

- **API Logs**: Check console output for detailed logs
- **Job Status**: Monitor job progress via `/jobs/{job_id}`
- **System Resources**: Use `/system/info` and `/system/gpu`
- **Health Check**: Regular `/health` endpoint monitoring

## 📊 Performance Tips

1. **GPU Memory**: Adjust `images_per_gpu` based on GPU memory
2. **Batch Processing**: Process multiple frames in batches
3. **Parallel Processing**: Use multiple workers for CPU-bound tasks
4. **Storage**: Use SSD storage for better I/O performance
5. **Network**: Use local storage to minimize network overhead

## 🔄 Integration Examples

### Curl Commands

```bash
# Health check
curl -X GET "http://localhost:8000/health"

# Start inference
curl -X POST "http://localhost:8000/inference/segment" \
  -H "Content-Type: application/json" \
  -d '{
    "frames_root": "/data/frames",
    "output_dir": "/data/output",
    "ir_or_rgb": "ir",
    "settings": {"gpu_count": 1}
  }'

# Check job status
curl -X GET "http://localhost:8000/jobs/{job_id}"
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

class PVHawkAPI {
    constructor(baseUrl = 'http://localhost:8000') {
        this.client = axios.create({ baseURL: baseUrl });
    }
    
    async runInference(framesRoot, outputDir, irOrRgb = 'ir') {
        const response = await this.client.post('/inference/segment', {
            frames_root: framesRoot,
            output_dir: outputDir,
            ir_or_rgb: irOrRgb,
            settings: { gpu_count: 1 }
        });
        return response.data.job_id;
    }
    
    async getJobStatus(jobId) {
        const response = await this.client.get(`/jobs/${jobId}`);
        return response.data;
    }
}
```

This API system provides complete programmatic control over PV-Hawk processing, enabling seamless integration with other software systems and automated workflows.