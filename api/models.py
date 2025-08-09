"""
Pydantic models for PV-Hawk API requests and responses
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class JobStatusEnum(str, Enum):
    """Job status enumeration"""
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class IROrRGB(str, Enum):
    """Image type enumeration"""
    ir = "ir"
    rgb = "rgb"


class MotionModel(str, Enum):
    """Motion model enumeration for tracking"""
    homography = "homography"
    affine = "affine"


class SelectFramesMode(str, Enum):
    """Frame selection mode for OpenSfM"""
    gps = "gps"
    visual = "visual"
    gps_visual = "gps_visual"


class AlignMethod(str, Enum):
    """Alignment method for OpenSfM"""
    orientation_prior = "orientation_prior"
    auto = "auto"


class AlignOrientation(str, Enum):
    """Alignment orientation"""
    horizontal = "horizontal"
    vertical = "vertical"


# Configuration Models
class SplitSequencesConfig(BaseModel):
    """Configuration for split_sequences task"""
    ir_file_extension: str = "TIFF"
    rgb_file_extension: str = "mov"
    extract_timestamps: bool = True
    extract_gps: bool = True
    extract_gps_altitude: bool = False
    sync_rgb: bool = False
    subsample: Optional[int] = None
    rotate_rgb: Optional[int] = None
    rotate_ir: Optional[int] = None
    resize_rgb: Optional[Dict[str, Optional[int]]] = {"width": None, "height": None}
    resize_ir: Optional[Dict[str, Optional[int]]] = {"width": None, "height": None}


class SegmentPVModulesConfig(BaseModel):
    """Configuration for segment_pv_modules task"""
    gpu_count: int = 1
    images_per_gpu: int = 8
    detection_min_confidence: float = 0.9
    weights_file_ir: str = "/pvextractor/extractor/segmentation/Mask_RCNN_TF2/mask_rcnn_pv_modules_0120.h5"
    weights_file_rgb: str = "/pvextractor/extractor/segmentation/Mask_RCNN_TF2/mask_rcnn_pv_modules_rgb_0059.h5"
    output_video_fps: float = 8.0


class TrackPVModulesConfig(BaseModel):
    """Configuration for track_pv_modules task"""
    motion_model: MotionModel = MotionModel.homography
    orb_nfeatures: int = 5000
    orb_fast_thres: int = 12
    orb_scale_factor: float = 1.2
    orb_nlevels: int = 8
    match_distance_thres: float = 20.0
    max_distance: int = 60
    output_video_fps: float = 8.0
    deterministic_track_ids: bool = True


class ComputeQuadrilateralsConfig(BaseModel):
    """Configuration for compute_pv_module_quadrilaterals task"""
    min_iou: float = 0.9


class PrepareOpenSfMConfig(BaseModel):
    """Configuration for prepare_opensfm task"""
    select_frames_mode: SelectFramesMode = SelectFramesMode.gps
    frame_selection_gps_distance: float = 0.75
    frame_selection_visual_distance: float = 0.15
    orb_nfeatures: int = 5000
    orb_fast_thres: int = 12
    orb_scale_factor: float = 1.2
    orb_nlevels: int = 8
    match_distance_thres: float = 20.0
    gps_dop: float = 0.1
    output_video_fps: float = 5.0


class OpenSfMConfig(BaseModel):
    """Configuration for OpenSfM reconstruction"""
    matching_gps_distance: int = 20
    processes: int = 16
    use_altitude_tag: str = "no"
    align_method: AlignMethod = AlignMethod.orientation_prior
    align_orientation_prior: AlignOrientation = AlignOrientation.horizontal


class TriangulatePVModulesConfig(BaseModel):
    """Configuration for triangulate_pv_modules task"""
    min_track_len: int = 2
    merge_overlapping_modules: bool = True
    merge_threshold: int = 20
    max_module_depth: int = -1
    max_num_modules: int = 300
    max_combinations: int = -1
    reproj_thres: float = 5.0
    min_ray_angle_degrees: float = 1.0


class RefineTriangulationConfig(BaseModel):
    """Configuration for refine_triangulation task"""
    merge_threshold_image: int = 20
    merge_threshold_world: int = 1
    max_module_depth: int = -1
    max_num_modules: int = 300
    optimizer_steps: int = 10


class CropPVModulesConfig(BaseModel):
    """Configuration for crop_pv_modules task"""
    rotate_mode: str = "portrait"


class ClusterConfig(BaseModel):
    """Configuration for a processing cluster"""
    cluster_idx: int
    frame_idx_start: int
    frame_idx_end: int


class GroupConfig(BaseModel):
    """Configuration for a processing group"""
    cam_params_dir: str
    clusters: List[ClusterConfig]
    ir_or_rgb: IROrRGB = IROrRGB.ir
    settings: Optional[Dict[str, Any]] = {}


class TaskSettings(BaseModel):
    """All task-specific settings"""
    split_sequences: Optional[SplitSequencesConfig] = SplitSequencesConfig()
    interpolate_gps: Optional[Dict[str, Any]] = {}
    segment_pv_modules: Optional[SegmentPVModulesConfig] = SegmentPVModulesConfig()
    track_pv_modules: Optional[TrackPVModulesConfig] = TrackPVModulesConfig()
    compute_pv_module_quadrilaterals: Optional[ComputeQuadrilateralsConfig] = ComputeQuadrilateralsConfig()
    prepare_opensfm: Optional[PrepareOpenSfMConfig] = PrepareOpenSfMConfig()
    opensfm: Optional[OpenSfMConfig] = OpenSfMConfig()
    triangulate_pv_modules: Optional[TriangulatePVModulesConfig] = TriangulatePVModulesConfig()
    refine_triangulation: Optional[RefineTriangulationConfig] = RefineTriangulationConfig()
    crop_pv_modules: Optional[CropPVModulesConfig] = CropPVModulesConfig()


class PipelineConfig(BaseModel):
    """Complete pipeline configuration"""
    plant_name: str
    groups: List[GroupConfig]
    tasks: List[str]
    settings: Optional[TaskSettings] = TaskSettings()


# Request Models
class PipelineRequest(BaseModel):
    """Request to run the full pipeline"""
    config: PipelineConfig
    work_dir: str = Field(..., description="Working directory path")


class StepRequest(BaseModel):
    """Request to run a single pipeline step"""
    config: Dict[str, Any] = Field(..., description="Step-specific configuration")
    work_dir: str = Field(..., description="Working directory path")
    group_name: Optional[str] = Field(None, description="Group name for the step")


class InferenceRequest(BaseModel):
    """Request for inference-only processing"""
    frames_root: str = Field(..., description="Path to input frames directory")
    output_dir: str = Field(..., description="Path to output directory")
    ir_or_rgb: IROrRGB = Field(..., description="Image type to process")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Inference settings")


# Response Models
class JobResponse(BaseModel):
    """Response for job creation"""
    job_id: str
    message: str


class JobStatus(BaseModel):
    """Job status information"""
    job_id: str
    job_type: str
    status: JobStatusEnum
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int = Field(0, ge=0, le=100, description="Progress percentage")
    message: Optional[str] = None
    error: Optional[str] = None
    work_dir: Optional[str] = None
    group_name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class ConfigValidationResponse(BaseModel):
    """Response for configuration validation"""
    valid: bool
    message: str
    errors: Optional[List[str]] = None


class SystemInfo(BaseModel):
    """System information response"""
    python_version: str
    tensorflow_version: str
    gpu_available: bool
    gpu_count: int
    gpu_names: List[str]
    cpu_count: int
    memory_total_gb: float
    disk_space_gb: float


class GPUInfo(BaseModel):
    """GPU information response"""
    gpu_available: bool
    gpu_count: int
    gpus: List[Dict[str, Any]]
    cuda_version: Optional[str] = None
    memory_info: Optional[Dict[str, Any]] = None