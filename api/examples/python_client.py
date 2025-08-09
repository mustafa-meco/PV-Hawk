#!/usr/bin/env python3
"""
PV-Hawk API Python Client Example

This script demonstrates how to interact with the PV-Hawk API using Python.
"""

import requests
import json
import time
import yaml
from typing import Dict, Any, Optional


class PVHawkAPIClient:
    """Python client for PV-Hawk API"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health status"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        response = self.session.get(f"{self.base_url}/config/defaults")
        response.raise_for_status()
        return response.json()
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a configuration"""
        response = self.session.post(
            f"{self.base_url}/config/validate",
            json=config
        )
        response.raise_for_status()
        return response.json()
    
    def run_full_pipeline(self, config: Dict[str, Any], work_dir: str) -> str:
        """Run the full processing pipeline"""
        request_data = {
            "config": config,
            "work_dir": work_dir
        }
        
        response = self.session.post(
            f"{self.base_url}/pipeline/run",
            json=request_data
        )
        response.raise_for_status()
        result = response.json()
        return result["job_id"]
    
    def run_pipeline_step(
        self, 
        step_name: str, 
        config: Dict[str, Any], 
        work_dir: str,
        group_name: Optional[str] = None
    ) -> str:
        """Run a single pipeline step"""
        request_data = {
            "config": config,
            "work_dir": work_dir
        }
        
        if group_name:
            request_data["group_name"] = group_name
        
        response = self.session.post(
            f"{self.base_url}/pipeline/step/{step_name}",
            json=request_data
        )
        response.raise_for_status()
        result = response.json()
        return result["job_id"]
    
    def run_inference(
        self,
        frames_root: str,
        output_dir: str,
        ir_or_rgb: str,
        settings: Optional[Dict[str, Any]] = None
    ) -> str:
        """Run inference on images"""
        request_data = {
            "frames_root": frames_root,
            "output_dir": output_dir,
            "ir_or_rgb": ir_or_rgb,
            "settings": settings or {}
        }
        
        response = self.session.post(
            f"{self.base_url}/inference/segment",
            json=request_data
        )
        response.raise_for_status()
        result = response.json()
        return result["job_id"]
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status"""
        response = self.session.get(f"{self.base_url}/jobs/{job_id}")
        response.raise_for_status()
        return response.json()
    
    def list_jobs(self) -> list:
        """List all jobs"""
        response = self.session.get(f"{self.base_url}/jobs")
        response.raise_for_status()
        return response.json()
    
    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a job"""
        response = self.session.delete(f"{self.base_url}/jobs/{job_id}")
        response.raise_for_status()
        return response.json()
    
    def get_job_results(self, job_id: str) -> Dict[str, Any]:
        """Get job results summary"""
        response = self.session.get(f"{self.base_url}/results/{job_id}/summary")
        response.raise_for_status()
        return response.json()
    
    def list_job_files(self, job_id: str) -> list:
        """List job output files"""
        response = self.session.get(f"{self.base_url}/results/{job_id}/files")
        response.raise_for_status()
        return response.json()
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        response = self.session.get(f"{self.base_url}/system/info")
        response.raise_for_status()
        return response.json()
    
    def get_gpu_info(self) -> Dict[str, Any]:
        """Get GPU information"""
        response = self.session.get(f"{self.base_url}/system/gpu")
        response.raise_for_status()
        return response.json()
    
    def wait_for_job_completion(self, job_id: str, poll_interval: int = 5) -> Dict[str, Any]:
        """Wait for job to complete and return final status"""
        while True:
            status = self.get_job_status(job_id)
            
            if status["status"] in ["completed", "failed", "cancelled"]:
                return status
            
            print(f"Job {job_id}: {status['status']} - {status.get('message', '')}")
            time.sleep(poll_interval)


def main():
    """Example usage of the PV-Hawk API client"""
    
    # Initialize client
    client = PVHawkAPIClient("http://localhost:8000")
    
    # Check API health
    print("Checking API health...")
    health = client.health_check()
    print(f"API Status: {health['status']}")
    print(f"GPU Available: {health['gpu_available']}")
    
    # Get system information
    print("\nSystem Information:")
    system_info = client.get_system_info()
    print(f"TensorFlow Version: {system_info.get('tensorflow_version', 'N/A')}")
    print(f"GPU Count: {system_info.get('gpu_count', 0)}")
    
    # Example 1: Run inference only
    print("\n=== Example 1: Running inference ===")
    
    inference_settings = {
        "gpu_count": 1,
        "images_per_gpu": 2,
        "detection_min_confidence": 0.9,
        "weights_file_ir": "/models/mask_rcnn_pv_modules_0120.h5"
    }
    
    # Note: Replace these paths with actual paths
    frames_path = "/data/frames"
    output_path = "/data/output"
    
    try:
        job_id = client.run_inference(
            frames_root=frames_path,
            output_dir=output_path,
            ir_or_rgb="ir",
            settings=inference_settings
        )
        
        print(f"Started inference job: {job_id}")
        
        # Wait for completion (in real usage, you might not want to block)
        final_status = client.wait_for_job_completion(job_id)
        print(f"Job completed with status: {final_status['status']}")
        
        if final_status['status'] == 'completed':
            results = client.get_job_results(job_id)
            print(f"Results: {json.dumps(results, indent=2)}")
        
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
    
    # Example 2: Run full pipeline
    print("\n=== Example 2: Running full pipeline ===")
    
    # Create a sample configuration
    pipeline_config = {
        "plant_name": "Test Solar Installation",
        "groups": [
            {
                "cam_params_dir": "/calibration",
                "ir_or_rgb": "ir",
                "clusters": [
                    {
                        "cluster_idx": 0,
                        "frame_idx_start": 0,
                        "frame_idx_end": 100
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
            "track_pv_modules"
        ]
    }
    
    try:
        # Validate configuration first
        validation = client.validate_config(pipeline_config)
        
        if validation["valid"]:
            print("Configuration is valid")
            
            # Start pipeline
            work_dir = "/workdir/test_run"
            job_id = client.run_full_pipeline(pipeline_config, work_dir)
            print(f"Started pipeline job: {job_id}")
            
            # Monitor progress
            final_status = client.wait_for_job_completion(job_id)
            print(f"Pipeline completed with status: {final_status['status']}")
            
        else:
            print(f"Configuration validation failed: {validation['message']}")
    
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
    
    # Example 3: List all jobs
    print("\n=== Example 3: Listing all jobs ===")
    
    try:
        jobs = client.list_jobs()
        print(f"Total jobs: {len(jobs)}")
        
        for job in jobs[-5:]:  # Show last 5 jobs
            print(f"Job {job['job_id']}: {job['job_type']} - {job['status']}")
    
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")


if __name__ == "__main__":
    main()