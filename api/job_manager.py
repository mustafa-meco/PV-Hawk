"""
Job Manager for PV-Hawk API

Handles job creation, tracking, and management for asynchronous processing tasks.
"""

import asyncio
import threading
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import json
import os

from api.models import JobStatus, JobStatusEnum

logger = logging.getLogger(__name__)


class JobManager:
    """Manages background processing jobs"""
    
    def __init__(self, max_workers: int = 4):
        self.jobs: Dict[str, JobStatus] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()
        
    def create_job(
        self, 
        job_id: str, 
        job_type: str, 
        config: Dict[str, Any],
        work_dir: Optional[str] = None,
        group_name: Optional[str] = None
    ) -> JobStatus:
        """Create a new job"""
        with self.lock:
            job = JobStatus(
                job_id=job_id,
                job_type=job_type,
                status=JobStatusEnum.pending,
                created_at=datetime.utcnow(),
                work_dir=work_dir,
                group_name=group_name,
                config=config
            )
            self.jobs[job_id] = job
            logger.info(f"Created job {job_id} of type {job_type}")
            return job
    
    def get_job(self, job_id: str) -> Optional[JobStatus]:
        """Get job by ID"""
        with self.lock:
            return self.jobs.get(job_id)
    
    def list_jobs(self) -> List[JobStatus]:
        """List all jobs"""
        with self.lock:
            return list(self.jobs.values())
    
    def update_job_status(
        self, 
        job_id: str, 
        status: JobStatusEnum, 
        progress: Optional[int] = None,
        message: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Update job status"""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = status
                
                if progress is not None:
                    job.progress = progress
                
                if message is not None:
                    job.message = message
                
                if error is not None:
                    job.error = error
                
                # Set timestamps
                if status == JobStatusEnum.running and job.started_at is None:
                    job.started_at = datetime.utcnow()
                elif status in [JobStatusEnum.completed, JobStatusEnum.failed, JobStatusEnum.cancelled]:
                    job.completed_at = datetime.utcnow()
                
                logger.info(f"Updated job {job_id} status to {status}")
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                if job.status in [JobStatusEnum.pending, JobStatusEnum.running]:
                    job.status = JobStatusEnum.cancelled
                    job.completed_at = datetime.utcnow()
                    logger.info(f"Cancelled job {job_id}")
                    return True
        return False
    
    def clear_completed_jobs(self) -> int:
        """Remove completed jobs from memory"""
        with self.lock:
            completed_jobs = [
                job_id for job_id, job in self.jobs.items() 
                if job.status in [JobStatusEnum.completed, JobStatusEnum.failed, JobStatusEnum.cancelled]
            ]
            
            for job_id in completed_jobs:
                del self.jobs[job_id]
            
            logger.info(f"Cleared {len(completed_jobs)} completed jobs")
            return len(completed_jobs)
    
    def save_job_state(self, work_dir: str):
        """Save job states to disk"""
        try:
            os.makedirs(work_dir, exist_ok=True)
            jobs_file = os.path.join(work_dir, "jobs_state.json")
            
            with self.lock:
                jobs_data = {}
                for job_id, job in self.jobs.items():
                    jobs_data[job_id] = {
                        "job_id": job.job_id,
                        "job_type": job.job_type,
                        "status": job.status.value,
                        "created_at": job.created_at.isoformat(),
                        "started_at": job.started_at.isoformat() if job.started_at else None,
                        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                        "progress": job.progress,
                        "message": job.message,
                        "error": job.error,
                        "work_dir": job.work_dir,
                        "group_name": job.group_name,
                        "config": job.config
                    }
            
            with open(jobs_file, 'w') as f:
                json.dump(jobs_data, f, indent=2)
                
            logger.info(f"Saved job state to {jobs_file}")
            
        except Exception as e:
            logger.error(f"Failed to save job state: {e}")
    
    def load_job_state(self, work_dir: str):
        """Load job states from disk"""
        try:
            jobs_file = os.path.join(work_dir, "jobs_state.json")
            
            if not os.path.exists(jobs_file):
                return
            
            with open(jobs_file, 'r') as f:
                jobs_data = json.load(f)
            
            with self.lock:
                for job_id, job_data in jobs_data.items():
                    job = JobStatus(
                        job_id=job_data["job_id"],
                        job_type=job_data["job_type"],
                        status=JobStatusEnum(job_data["status"]),
                        created_at=datetime.fromisoformat(job_data["created_at"]),
                        started_at=datetime.fromisoformat(job_data["started_at"]) if job_data.get("started_at") else None,
                        completed_at=datetime.fromisoformat(job_data["completed_at"]) if job_data.get("completed_at") else None,
                        progress=job_data.get("progress", 0),
                        message=job_data.get("message"),
                        error=job_data.get("error"),
                        work_dir=job_data.get("work_dir"),
                        group_name=job_data.get("group_name"),
                        config=job_data.get("config")
                    )
                    self.jobs[job_id] = job
            
            logger.info(f"Loaded job state from {jobs_file}")
            
        except Exception as e:
            logger.error(f"Failed to load job state: {e}")
    
    def get_job_statistics(self) -> Dict[str, int]:
        """Get job statistics"""
        with self.lock:
            stats = {
                "total": len(self.jobs),
                "pending": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0
            }
            
            for job in self.jobs.values():
                stats[job.status.value] += 1
            
            return stats