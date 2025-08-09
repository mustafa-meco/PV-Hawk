# PV-Hawk API Quick Start Guide

This guide helps you get started with the PV-Hawk API system in just a few minutes.

## 🚀 Quick Setup

### 1. Install API Dependencies

```bash
# Install API requirements
pip install fastapi uvicorn pydantic PyJWT python-multipart psutil

# Or install from requirements file
pip install -r api/requirements.txt
```

### 2. Start the API Server

#### Option A: Direct Python
```bash
# Simple start
python start_api.py

# With custom configuration
python start_api.py --host 0.0.0.0 --port 8000 --log-level info
```

#### Option B: Docker Compose
```bash
# Start API server
docker-compose up pv-hawk-api

# Or build and start
docker-compose up --build pv-hawk-api

# Run in background
docker-compose up -d pv-hawk-api
```

### 3. Test the API

```bash
# Health check
curl http://localhost:8000/health

# System information
curl http://localhost:8000/system/info

# Interactive documentation
# Open: http://localhost:8000/docs
```

## 📝 Basic Usage Examples

### Example 1: Health Check

```bash
curl -X GET "http://localhost:8000/health" | jq
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2023-12-01T10:30:00Z",
  "version": "2.0.0",
  "gpu_available": true
}
```

### Example 2: Run Inference

```bash
curl -X POST "http://localhost:8000/inference/segment" \
  -H "Content-Type: application/json" \
  -d '{
    "frames_root": "/data/input_frames",
    "output_dir": "/data/output",
    "ir_or_rgb": "ir",
    "settings": {
      "gpu_count": 1,
      "images_per_gpu": 2,
      "detection_min_confidence": 0.9
    }
  }' | jq
```

Response:
```json
{
  "job_id": "abc123-def456-ghi789",
  "message": "Segmentation inference started successfully"
}
```

### Example 3: Check Job Status

```bash
curl -X GET "http://localhost:8000/jobs/abc123-def456-ghi789" | jq
```

Response:
```json
{
  "job_id": "abc123-def456-ghi789",
  "job_type": "inference_segmentation",
  "status": "running",
  "progress": 45,
  "message": "Processing frame 450/1000",
  "created_at": "2023-12-01T10:30:00Z",
  "started_at": "2023-12-01T10:31:00Z"
}
```

### Example 4: Run Full Pipeline

```bash
curl -X POST "http://localhost:8000/pipeline/run" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "plant_name": "Test Installation",
      "groups": [{
        "cam_params_dir": "/calibration",
        "ir_or_rgb": "ir",
        "clusters": [{
          "cluster_idx": 0,
          "frame_idx_start": 0,
          "frame_idx_end": 100
        }]
      }],
      "tasks": ["split_sequences", "segment_pv_modules"]
    },
    "work_dir": "/workdir/test_run"
  }' | jq
```

## 🐍 Python Client Usage

```python
import requests
import time

# Simple client example
def run_pv_hawk_inference(frames_path, output_path):
    base_url = "http://localhost:8000"
    
    # Start inference job
    response = requests.post(f"{base_url}/inference/segment", json={
        "frames_root": frames_path,
        "output_dir": output_path,
        "ir_or_rgb": "ir",
        "settings": {
            "gpu_count": 1,
            "images_per_gpu": 2,
            "detection_min_confidence": 0.9
        }
    })
    
    job_id = response.json()["job_id"]
    print(f"Started job: {job_id}")
    
    # Wait for completion
    while True:
        status_response = requests.get(f"{base_url}/jobs/{job_id}")
        status = status_response.json()
        
        print(f"Status: {status['status']} - Progress: {status['progress']}%")
        
        if status["status"] in ["completed", "failed", "cancelled"]:
            break
            
        time.sleep(10)  # Check every 10 seconds
    
    if status["status"] == "completed":
        # Get results
        results_response = requests.get(f"{base_url}/results/{job_id}/summary")
        results = results_response.json()
        print(f"Processing completed! Generated {results['total_files']} files")
        return results
    else:
        print(f"Job failed: {status.get('error', 'Unknown error')}")
        return None

# Usage
results = run_pv_hawk_inference("/data/input", "/data/output")
```

## 🐳 Docker Usage

### Start API Server
```bash
# Using docker-compose
docker-compose up pv-hawk-api

# Using docker directly
docker run --gpus all -p 8000:8000 \
  -v ./workdir:/workdir \
  -v ./data:/data \
  -v ./models:/models \
  pv-hawk-tf2:latest \
  python start_api.py --host 0.0.0.0 --port 8000
```

### Start CLI Mode
```bash
# Using docker-compose
docker-compose --profile cli up pv-hawk-cli

# Interactive mode
docker-compose --profile cli run --rm pv-hawk-cli bash
```

### Both Modes Together
```bash
# API server in background
docker-compose up -d pv-hawk-api

# CLI for one-off tasks
docker-compose --profile cli run --rm pv-hawk-cli python main.py /workdir
```

## 🔧 Configuration

### Environment Variables

Create `.env` file:
```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
nano .env
```

Key settings:
```bash
# Data directories
DATA_DIR=./data
WORK_DIR=./workdir
MODELS_DIR=./models

# API settings
API_PORT=8000
API_SECRET_KEY=your-secret-key

# GPU settings
CUDA_VISIBLE_DEVICES=0
TF_FORCE_GPU_ALLOW_GROWTH=true
```

## 📊 Monitoring

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Health Monitoring
```bash
# Check API health
curl http://localhost:8000/health

# System information
curl http://localhost:8000/system/info

# GPU status
curl http://localhost:8000/system/gpu

# List all jobs
curl http://localhost:8000/jobs
```

### Log Monitoring
```bash
# Docker logs
docker-compose logs -f pv-hawk-api

# Direct Python logs (when running with start_api.py)
# Logs appear in console
```

## 🔍 Troubleshooting

### Common Issues

1. **API not starting**
   ```bash
   # Check dependencies
   pip install -r api/requirements.txt
   
   # Check port availability
   netstat -tulpn | grep 8000
   ```

2. **GPU not available**
   ```bash
   # Check NVIDIA setup
   nvidia-smi
   docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi
   ```

3. **Import errors**
   ```bash
   # Check Python path
   export PYTHONPATH=/path/to/PV-Hawk-Fork:$PYTHONPATH
   ```

4. **Permission errors**
   ```bash
   # Fix directory permissions
   sudo chown -R $USER:$USER ./workdir ./data
   chmod -R 755 ./workdir ./data
   ```

### Getting Help

- **API Documentation**: http://localhost:8000/docs
- **System Status**: http://localhost:8000/system/info
- **Health Check**: http://localhost:8000/health
- **Job Status**: http://localhost:8000/jobs

## ⚡ Quick Commands Reference

```bash
# Start API server
python start_api.py

# Health check
curl http://localhost:8000/health

# Run inference
curl -X POST http://localhost:8000/inference/segment -H "Content-Type: application/json" -d '{"frames_root":"/data/input","output_dir":"/data/output","ir_or_rgb":"ir","settings":{}}'

# Check job status
curl http://localhost:8000/jobs/{job_id}

# List all jobs
curl http://localhost:8000/jobs

# System info
curl http://localhost:8000/system/info

# Stop API server (Ctrl+C or)
docker-compose down
```

You're now ready to integrate PV-Hawk with other systems through the REST API!