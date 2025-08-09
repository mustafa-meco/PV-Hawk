"""
PV-Hawk Processing Engine

Handles the execution of PV-Hawk processing tasks through the API.
Integrates with the existing main.py processing logic.
"""

import os
import sys
import yaml
import json
import logging
import traceback
import subprocess
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from extractor.common import get_group_name, merge_dicts, remove_none, replace_empty_fields
from extractor.preprocessing import split_tiffs, interpolation
from extractor import tracking, quadrilaterals, cropping
from extractor.mapping import prepare_opensfm, triangulate_modules, refine_triangulation

from api.job_manager import JobManager
from api.models import JobStatusEnum

logger = logging.getLogger(__name__)


class PVHawkProcessor:
    """Handles PV-Hawk processing tasks"""
    
    def __init__(self, job_manager: JobManager):
        self.job_manager = job_manager
        self.default_config = self._load_default_config()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        try:
            defaults_path = os.path.join(os.path.dirname(__file__), '..', 'defaults.yml')
            with open(defaults_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load default config: {e}")
            return {}
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return self.default_config.copy()
    
    def validate_config(self, config: Dict[str, Any]):
        """Validate pipeline configuration"""
        required_fields = ['plant_name', 'groups', 'tasks']
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate groups
        for i, group in enumerate(config['groups']):
            if 'clusters' not in group:
                raise ValueError(f"Group {i} missing 'clusters' field")
            
            for j, cluster in enumerate(group['clusters']):
                required_cluster_fields = ['cluster_idx', 'frame_idx_start', 'frame_idx_end']
                for field in required_cluster_fields:
                    if field not in cluster:
                        raise ValueError(f"Group {i} cluster {j} missing '{field}' field")
        
        # Validate tasks
        valid_tasks = [
            "split_sequences", "interpolate_gps", "segment_pv_modules",
            "track_pv_modules", "compute_pv_module_quadrilaterals",
            "prepare_opensfm", "opensfm_extract_metadata", "opensfm_detect_features",
            "opensfm_match_features", "opensfm_create_tracks", "opensfm_reconstruct",
            "triangulate_pv_modules", "refine_triangulation", "crop_pv_modules"
        ]
        
        for task in config['tasks']:
            if task not in valid_tasks:
                raise ValueError(f"Invalid task: {task}. Valid tasks: {valid_tasks}")
    
    def check_gpu_availability(self) -> bool:
        """Check if GPU is available"""
        try:
            import tensorflow as tf
            return len(tf.config.list_physical_devices('GPU')) > 0
        except Exception:
            return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            import tensorflow as tf
            gpu_devices = tf.config.list_physical_devices('GPU')
            gpu_names = []
            
            for gpu in gpu_devices:
                try:
                    gpu_names.append(gpu.name)
                except Exception:
                    gpu_names.append("Unknown GPU")
            
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "python_version": sys.version,
                "tensorflow_version": tf.__version__,
                "gpu_available": len(gpu_devices) > 0,
                "gpu_count": len(gpu_devices),
                "gpu_names": gpu_names,
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "disk_space_gb": round(disk.total / (1024**3), 2)
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {"error": str(e)}
    
    def get_gpu_info(self) -> Dict[str, Any]:
        """Get detailed GPU information"""
        try:
            import tensorflow as tf
            
            gpu_info = {
                "gpu_available": False,
                "gpu_count": 0,
                "gpus": [],
                "cuda_version": None,
                "memory_info": None
            }
            
            # Get GPU devices
            gpu_devices = tf.config.list_physical_devices('GPU')
            gpu_info["gpu_available"] = len(gpu_devices) > 0
            gpu_info["gpu_count"] = len(gpu_devices)
            
            # Try to get detailed GPU information
            try:
                import pynvml
                pynvml.nvmlInit()
                
                for i in range(len(gpu_devices)):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                    memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    
                    gpu_info["gpus"].append({
                        "index": i,
                        "name": name,
                        "memory_total": memory_info.total,
                        "memory_used": memory_info.used,
                        "memory_free": memory_info.free
                    })
                
                # Get CUDA version
                try:
                    cuda_version = pynvml.nvmlSystemGetCudaDriverVersion()
                    gpu_info["cuda_version"] = f"{cuda_version // 1000}.{(cuda_version % 1000) // 10}"
                except Exception:
                    pass
                    
            except ImportError:
                # pynvml not available, use basic TensorFlow info
                for i, gpu in enumerate(gpu_devices):
                    gpu_info["gpus"].append({
                        "index": i,
                        "name": gpu.name,
                        "device_type": gpu.device_type
                    })
            
            return gpu_info
            
        except Exception as e:
            logger.error(f"Failed to get GPU info: {e}")
            return {"error": str(e)}
    
    async def run_full_pipeline(self, job_id: str, config: Dict[str, Any], work_dir: str):
        """Run the complete PV-Hawk processing pipeline"""
        try:
            self.job_manager.update_job_status(job_id, JobStatusEnum.running, 0, "Starting full pipeline")
            
            # Save configuration to work directory
            os.makedirs(work_dir, exist_ok=True)
            config_path = os.path.join(work_dir, "config.yml")
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
            
            # Run the main processing logic
            await self._run_main_processing(job_id, work_dir)
            
            self.job_manager.update_job_status(
                job_id, JobStatusEnum.completed, 100, "Pipeline completed successfully"
            )
            
        except Exception as e:
            error_msg = f"Pipeline failed: {str(e)}"
            logger.error(f"Job {job_id} failed: {error_msg}")
            logger.error(traceback.format_exc())
            self.job_manager.update_job_status(job_id, JobStatusEnum.failed, error=error_msg)
    
    async def run_single_step(
        self, 
        job_id: str, 
        step_name: str, 
        config: Dict[str, Any], 
        work_dir: str, 
        group_name: Optional[str] = None
    ):
        """Run a single pipeline step"""
        try:
            self.job_manager.update_job_status(
                job_id, JobStatusEnum.running, 0, f"Starting step: {step_name}"
            )
            
            # Merge with defaults
            settings = merge_dicts(self.default_config, remove_none(config.get('settings', {})))
            replace_empty_fields(settings)
            
            # Determine group name
            if not group_name and 'groups' in config and len(config['groups']) > 0:
                group_name = get_group_name(config['groups'][0])
            
            if not group_name:
                group_name = "group_001"
            
            # Create group directory
            group_dir = os.path.join(work_dir, group_name)
            os.makedirs(group_dir, exist_ok=True)
            
            # Get IR/RGB setting
            ir_or_rgb = config.get('ir_or_rgb', 'ir')
            if 'groups' in config and len(config['groups']) > 0:
                ir_or_rgb = config['groups'][0].get('ir_or_rgb', ir_or_rgb)
            
            # Run the specific step
            await self._run_single_processing_step(
                job_id, step_name, settings, work_dir, group_name, ir_or_rgb, config
            )
            
            self.job_manager.update_job_status(
                job_id, JobStatusEnum.completed, 100, f"Step {step_name} completed successfully"
            )
            
        except Exception as e:
            error_msg = f"Step {step_name} failed: {str(e)}"
            logger.error(f"Job {job_id} failed: {error_msg}")
            logger.error(traceback.format_exc())
            self.job_manager.update_job_status(job_id, JobStatusEnum.failed, error=error_msg)
    
    async def run_inference(
        self, 
        job_id: str, 
        frames_root: str, 
        output_dir: str, 
        ir_or_rgb: str,
        settings: Dict[str, Any]
    ):
        """Run inference-only processing"""
        try:
            self.job_manager.update_job_status(
                job_id, JobStatusEnum.running, 0, "Starting inference"
            )
            
            # Import and run inference
            from extractor.segmentation import inference
            
            # Merge settings with defaults
            inference_settings = merge_dicts(
                self.default_config.get('segment_pv_modules', {}),
                settings
            )
            
            self.job_manager.update_job_status(job_id, JobStatusEnum.running, 50, "Running segmentation")
            
            # Run inference
            inference.run(frames_root, output_dir, ir_or_rgb, **inference_settings)
            
            self.job_manager.update_job_status(
                job_id, JobStatusEnum.completed, 100, "Inference completed successfully"
            )
            
        except Exception as e:
            error_msg = f"Inference failed: {str(e)}"
            logger.error(f"Job {job_id} failed: {error_msg}")
            logger.error(traceback.format_exc())
            self.job_manager.update_job_status(job_id, JobStatusEnum.failed, error=error_msg)
    
    async def _run_main_processing(self, job_id: str, work_dir: str):
        """Run the main processing logic (adapted from main.py)"""
        # Load config file
        config_path = os.path.join(work_dir, "config.yml")
        config = yaml.safe_load(open(config_path, "r"))
        tasks = config["tasks"]
        
        total_tasks = len(tasks) if tasks else 0
        completed_tasks = 0
        
        for videogroup in config["groups"]:
            group_name = get_group_name(videogroup)
            
            # IR/RGB selection
            ir_or_rgb = videogroup.get("ir_or_rgb", "ir")
            
            # Load algorithm settings and merge with defaults
            settings = videogroup.get("settings", {})
            replace_empty_fields(self.default_config)
            settings = merge_dicts(self.default_config, remove_none(settings))
            
            # Write dataset version info
            os.makedirs(os.path.join(work_dir, group_name), exist_ok=True)
            version_info = {"dataset_version": "v2"}
            json.dump(version_info, open(os.path.join(work_dir, group_name, "version.json"), "w"))
            
            if tasks is None:
                continue
            
            # Process each task
            for i, task in enumerate(tasks):
                progress = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
                self.job_manager.update_job_status(
                    job_id, JobStatusEnum.running, progress, f"Running task: {task}"
                )
                
                await self._run_single_processing_step(
                    job_id, task, settings, work_dir, group_name, ir_or_rgb, videogroup
                )
                
                completed_tasks += 1
    
    async def _run_single_processing_step(
        self, 
        job_id: str, 
        task: str, 
        settings: Dict[str, Any], 
        work_dir: str, 
        group_name: str, 
        ir_or_rgb: str,
        videogroup: Dict[str, Any]
    ):
        """Run a single processing step"""
        
        if task == "split_sequences":
            video_dir = os.path.join(work_dir, group_name, "videos")
            output_dir = os.path.join(work_dir, group_name, "splitted")
            split_tiffs.run(video_dir, output_dir, **settings["split_sequences"])
        
        elif task == "interpolate_gps":
            frames_root = os.path.join(work_dir, group_name, "splitted")
            interpolation.run(frames_root, **settings["interpolate_gps"])
        
        elif task == "segment_pv_modules":
            from extractor.segmentation import inference
            frames_root = os.path.join(work_dir, group_name, "splitted")
            output_dir = os.path.join(work_dir, group_name, "segmented")
            inference.run(frames_root, output_dir, ir_or_rgb, **settings["segment_pv_modules"])
        
        elif task == "track_pv_modules":
            frames_root = os.path.join(work_dir, group_name, "splitted")
            inference_root = os.path.join(work_dir, group_name, "segmented")
            output_dir = os.path.join(work_dir, group_name, "tracking")
            tracking.run(frames_root, inference_root, output_dir, ir_or_rgb, **settings["track_pv_modules"])
        
        elif task == "compute_pv_module_quadrilaterals":
            frames_root = os.path.join(work_dir, group_name, "splitted")
            inference_root = os.path.join(work_dir, group_name, "segmented")
            tracks_root = os.path.join(work_dir, group_name, "tracking")
            output_dir = os.path.join(work_dir, group_name, "quadrilaterals")
            quadrilaterals.run(frames_root, inference_root, tracks_root, output_dir, 
                             ir_or_rgb, **settings["compute_pv_module_quadrilaterals"])
        
        elif task == "prepare_opensfm":
            for cluster in videogroup.get("clusters", []):
                frames_root = os.path.join(work_dir, group_name, "splitted")
                calibration_root = videogroup.get("cam_params_dir", "/calibration")
                output_dir = os.path.join(work_dir, group_name, "mapping")
                opensfm_settings = settings["opensfm"]
                prepare_opensfm.run(cluster, frames_root, calibration_root, output_dir, 
                                  opensfm_settings, ir_or_rgb, **settings["prepare_opensfm"])
        
        elif task.startswith("opensfm_"):
            opensfm_bin = "/pvextractor/extractor/mapping/OpenSfM/bin/opensfm"
            opensfm_command = task[8:]  # Remove 'opensfm_' prefix
            
            for cluster in videogroup.get("clusters", []):
                mapping_root = os.path.join(
                    work_dir, group_name, "mapping", 
                    f"cluster_{cluster['cluster_idx']:06d}"
                )
                
                command = f'{opensfm_bin} {opensfm_command} "{mapping_root}"'
                proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, 
                                      stderr=subprocess.STDOUT)
                
                for line in proc.stdout:
                    output_line = line.decode("utf-8").strip()
                    if output_line:
                        self.job_manager.update_job_status(
                            job_id, JobStatusEnum.running, message=output_line
                        )
        
        elif task == "triangulate_pv_modules":
            mapping_root = os.path.join(work_dir, group_name, "mapping")
            tracks_root = os.path.join(work_dir, group_name, "tracking")
            quads_root = os.path.join(work_dir, group_name, "quadrilaterals")
            triangulate_modules.run(mapping_root, tracks_root, quads_root, 
                                  **settings["triangulate_pv_modules"])
        
        elif task == "refine_triangulation":
            mapping_root = os.path.join(work_dir, group_name, "mapping")
            refine_triangulation.run(mapping_root, **settings["refine_triangulation"])
        
        elif task == "crop_pv_modules":
            frames_root = os.path.join(work_dir, group_name, "splitted")
            quads_root = os.path.join(work_dir, group_name, "quadrilaterals")
            mapping_root = os.path.join(work_dir, group_name, "mapping")
            output_dir = os.path.join(work_dir, group_name, "patches")
            cropping.run(frames_root, quads_root, mapping_root, output_dir, 
                        ir_or_rgb, **settings["crop_pv_modules"])
    
    def get_results_summary(self, job_id: str, work_dir: str) -> Dict[str, Any]:
        """Get summary of job results"""
        try:
            summary = {
                "job_id": job_id,
                "work_dir": work_dir,
                "output_directories": [],
                "file_counts": {},
                "total_files": 0
            }
            
            # Check for common output directories
            common_dirs = ["splitted", "segmented", "tracking", "quadrilaterals", 
                          "mapping", "patches"]
            
            work_path = Path(work_dir)
            for group_dir in work_path.iterdir():
                if group_dir.is_dir():
                    for output_dir in common_dirs:
                        output_path = group_dir / output_dir
                        if output_path.exists():
                            files = list(output_path.rglob("*"))
                            file_count = len([f for f in files if f.is_file()])
                            
                            summary["output_directories"].append(str(output_path))
                            summary["file_counts"][str(output_path)] = file_count
                            summary["total_files"] += file_count
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get results summary: {e}")
            return {"error": str(e)}
    
    def list_output_files(self, job_id: str, work_dir: str) -> List[str]:
        """List output files created by a job"""
        try:
            files = []
            work_path = Path(work_dir)
            
            for file_path in work_path.rglob("*"):
                if file_path.is_file():
                    files.append(str(file_path))
            
            return sorted(files)
            
        except Exception as e:
            logger.error(f"Failed to list output files: {e}")
            return []