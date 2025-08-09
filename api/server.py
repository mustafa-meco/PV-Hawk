"""
PV-Hawk REST API Server

This FastAPI application provides REST endpoints to control and monitor
PV-Hawk processing pipeline tasks. It supports:

- Triggering individual processing steps
- Managing configurations
- Monitoring job progress
- Retrieving processing results
"""

import os
import sys
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import yaml
import json

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append('/pvextractor')

from api.models import *
from api.processors import PVHawkProcessor
from api.job_manager import JobManager
from api.auth import verify_token

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PV-Hawk API",
    description="REST API for controlling PV-Hawk solar panel detection and analysis pipeline",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
security = HTTPBearer(auto_error=False)
job_manager = JobManager()
processor = PVHawkProcessor(job_manager)

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Check API health status"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "gpu_available": processor.check_gpu_availability()
    }

# Configuration endpoints
@app.get("/config/defaults", response_model=Dict[str, Any], tags=["Configuration"])
async def get_default_config():
    """Get default configuration settings"""
    return processor.get_default_config()

@app.post("/config/validate", response_model=ConfigValidationResponse, tags=["Configuration"])
async def validate_config(config: PipelineConfig):
    """Validate a pipeline configuration"""
    try:
        processor.validate_config(config.dict())
        return ConfigValidationResponse(valid=True, message="Configuration is valid")
    except Exception as e:
        return ConfigValidationResponse(valid=False, message=str(e))

# Job management endpoints
@app.get("/jobs", response_model=List[JobStatus], tags=["Jobs"])
async def list_jobs():
    """List all jobs with their current status"""
    return job_manager.list_jobs()

@app.get("/jobs/{job_id}", response_model=JobStatus, tags=["Jobs"])
async def get_job_status(job_id: str):
    """Get detailed status of a specific job"""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job

@app.delete("/jobs/{job_id}", response_model=Dict[str, str], tags=["Jobs"])
async def cancel_job(job_id: str):
    """Cancel a running job"""
    success = job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found or cannot be cancelled")
    return {"message": f"Job {job_id} cancelled successfully"}

@app.delete("/jobs", response_model=Dict[str, str], tags=["Jobs"])
async def clear_completed_jobs():
    """Clear all completed jobs from the queue"""
    count = job_manager.clear_completed_jobs()
    return {"message": f"Cleared {count} completed jobs"}

# Processing pipeline endpoints
@app.post("/pipeline/run", response_model=JobResponse, tags=["Pipeline"])
async def run_full_pipeline(
    request: PipelineRequest,
    background_tasks: BackgroundTasks
):
    """Run the complete PV-Hawk processing pipeline"""
    job_id = str(uuid.uuid4())
    
    # Create job
    job = job_manager.create_job(
        job_id=job_id,
        job_type="full_pipeline",
        config=request.config.dict(),
        work_dir=request.work_dir
    )
    
    # Start processing in background
    background_tasks.add_task(
        processor.run_full_pipeline, 
        job_id, 
        request.config.dict(), 
        request.work_dir
    )
    
    return JobResponse(job_id=job_id, message="Pipeline started successfully")

@app.post("/pipeline/step/{step_name}", response_model=JobResponse, tags=["Pipeline"])
async def run_pipeline_step(
    step_name: str,
    request: StepRequest,
    background_tasks: BackgroundTasks
):
    """Run a specific pipeline step"""
    valid_steps = [
        "split_sequences", "interpolate_gps", "segment_pv_modules",
        "track_pv_modules", "compute_pv_module_quadrilaterals",
        "prepare_opensfm", "opensfm_extract_metadata", "opensfm_detect_features",
        "opensfm_match_features", "opensfm_create_tracks", "opensfm_reconstruct",
        "triangulate_pv_modules", "refine_triangulation", "crop_pv_modules"
    ]
    
    if step_name not in valid_steps:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid step name. Valid steps: {valid_steps}"
        )
    
    job_id = str(uuid.uuid4())
    
    # Create job
    job = job_manager.create_job(
        job_id=job_id,
        job_type=f"step_{step_name}",
        config=request.config,
        work_dir=request.work_dir,
        group_name=request.group_name
    )
    
    # Start processing in background
    background_tasks.add_task(
        processor.run_single_step,
        job_id,
        step_name,
        request.config,
        request.work_dir,
        request.group_name
    )
    
    return JobResponse(job_id=job_id, message=f"Step {step_name} started successfully")

# Inference endpoints
@app.post("/inference/segment", response_model=JobResponse, tags=["Inference"])
async def segment_images(
    request: InferenceRequest,
    background_tasks: BackgroundTasks
):
    """Run PV module segmentation on a set of images"""
    job_id = str(uuid.uuid4())
    
    # Create job
    job = job_manager.create_job(
        job_id=job_id,
        job_type="inference_segmentation",
        config={
            "frames_root": request.frames_root,
            "output_dir": request.output_dir,
            "ir_or_rgb": request.ir_or_rgb,
            **request.settings
        }
    )
    
    # Start processing in background
    background_tasks.add_task(
        processor.run_inference,
        job_id,
        request.frames_root,
        request.output_dir,
        request.ir_or_rgb,
        request.settings
    )
    
    return JobResponse(job_id=job_id, message="Segmentation inference started successfully")

# Results endpoints
@app.get("/results/{job_id}/summary", response_model=Dict[str, Any], tags=["Results"])
async def get_job_results_summary(job_id: str):
    """Get summary of job results"""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job {job_id} is not completed yet")
    
    return processor.get_results_summary(job_id, job.work_dir)

@app.get("/results/{job_id}/files", response_model=List[str], tags=["Results"])
async def list_job_output_files(job_id: str):
    """List output files created by a job"""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return processor.list_output_files(job_id, job.work_dir)

# System information endpoints
@app.get("/system/info", response_model=Dict[str, Any], tags=["System"])
async def get_system_info():
    """Get system information including GPU status"""
    return processor.get_system_info()

@app.get("/system/gpu", response_model=Dict[str, Any], tags=["System"])
async def get_gpu_info():
    """Get detailed GPU information"""
    return processor.get_gpu_info()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.server:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )