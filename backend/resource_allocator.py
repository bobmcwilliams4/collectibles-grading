"""
Dynamic Resource Allocator
Automatically detects and allocates between GPU and CPU based on availability and load.
Authority Level: 11.0
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import GPU libraries
CUDA_AVAILABLE = False
TORCH_AVAILABLE = False
GPU_MEMORY_GB = 0.0
GPU_NAME = "None"

try:
    import torch
    TORCH_AVAILABLE = True
    if torch.cuda.is_available():
        CUDA_AVAILABLE = True
        GPU_NAME = torch.cuda.get_device_name(0)
        GPU_MEMORY_GB = torch.cuda.get_device_properties(0).total_memory / (1024**3)
except ImportError:
    pass

# Try to import system monitoring
PSUTIL_AVAILABLE = False
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    pass


class ComputeDevice(Enum):
    """Available compute devices"""
    CPU = "cpu"
    GPU = "cuda"
    AUTO = "auto"


@dataclass
class ResourceStatus:
    """Current resource availability"""
    cpu_percent_used: float
    cpu_percent_available: float
    cpu_cores: int
    ram_total_gb: float
    ram_available_gb: float
    ram_percent_available: float
    gpu_available: bool
    gpu_name: str
    gpu_memory_total_gb: float
    gpu_memory_available_gb: float
    gpu_memory_percent_available: float
    recommended_device: ComputeDevice
    recommendation_reason: str


class DynamicResourceAllocator:
    """
    Dynamically allocates compute resources between GPU and CPU
    based on current availability and workload.
    """

    def __init__(
        self,
        gpu_memory_threshold: float = 0.2,  # Minimum 20% GPU memory free
        cpu_threshold: float = 0.3,  # Minimum 30% CPU available
        ram_threshold: float = 0.2,  # Minimum 20% RAM available
        prefer_gpu: bool = True
    ):
        """
        Initialize resource allocator.

        Args:
            gpu_memory_threshold: Minimum fraction of GPU memory that should be free
            cpu_threshold: Minimum fraction of CPU that should be available
            ram_threshold: Minimum fraction of RAM that should be available
            prefer_gpu: Prefer GPU when both are available
        """
        self.gpu_memory_threshold = gpu_memory_threshold
        self.cpu_threshold = cpu_threshold
        self.ram_threshold = ram_threshold
        self.prefer_gpu = prefer_gpu

        # Cache system info
        self._cpu_cores = os.cpu_count() or 1
        self._ram_total_gb = self._get_total_ram()

        logger.info(f"Resource Allocator initialized")
        logger.info(f"  CPU Cores: {self._cpu_cores}")
        logger.info(f"  RAM Total: {self._ram_total_gb:.1f} GB")
        logger.info(f"  GPU Available: {CUDA_AVAILABLE}")
        if CUDA_AVAILABLE:
            logger.info(f"  GPU: {GPU_NAME} ({GPU_MEMORY_GB:.1f} GB)")

    def _get_total_ram(self) -> float:
        """Get total system RAM in GB"""
        if PSUTIL_AVAILABLE:
            return psutil.virtual_memory().total / (1024**3)
        # Fallback estimate
        return 8.0

    def _get_cpu_usage(self) -> Tuple[float, float]:
        """Get CPU usage (percent used, percent available)"""
        if PSUTIL_AVAILABLE:
            used = psutil.cpu_percent(interval=0.1)
            return used, 100.0 - used
        return 50.0, 50.0  # Assume 50% if can't measure

    def _get_ram_status(self) -> Tuple[float, float, float]:
        """Get RAM status (total GB, available GB, percent available)"""
        if PSUTIL_AVAILABLE:
            mem = psutil.virtual_memory()
            total_gb = mem.total / (1024**3)
            available_gb = mem.available / (1024**3)
            percent_available = (mem.available / mem.total) * 100
            return total_gb, available_gb, percent_available
        return self._ram_total_gb, self._ram_total_gb * 0.5, 50.0

    def _get_gpu_memory_status(self) -> Tuple[float, float, float]:
        """Get GPU memory status (total GB, available GB, percent available)"""
        if not CUDA_AVAILABLE or not TORCH_AVAILABLE:
            return 0.0, 0.0, 0.0

        try:
            import torch
            total = torch.cuda.get_device_properties(0).total_memory
            allocated = torch.cuda.memory_allocated(0)
            cached = torch.cuda.memory_reserved(0)
            available = total - allocated - cached

            total_gb = total / (1024**3)
            available_gb = available / (1024**3)
            percent_available = (available / total) * 100 if total > 0 else 0

            return total_gb, available_gb, percent_available
        except Exception as e:
            logger.warning(f"Could not get GPU memory status: {e}")
            return GPU_MEMORY_GB, GPU_MEMORY_GB, 100.0

    def get_resource_status(self) -> ResourceStatus:
        """
        Get current resource status and recommendation.

        Returns:
            ResourceStatus with current availability and recommendation
        """
        # Get current stats
        cpu_used, cpu_available = self._get_cpu_usage()
        ram_total, ram_available, ram_percent = self._get_ram_status()
        gpu_total, gpu_available, gpu_percent = self._get_gpu_memory_status()

        # Determine recommendation
        device, reason = self._get_recommendation(
            cpu_available, ram_percent, gpu_percent
        )

        return ResourceStatus(
            cpu_percent_used=cpu_used,
            cpu_percent_available=cpu_available,
            cpu_cores=self._cpu_cores,
            ram_total_gb=ram_total,
            ram_available_gb=ram_available,
            ram_percent_available=ram_percent,
            gpu_available=CUDA_AVAILABLE,
            gpu_name=GPU_NAME,
            gpu_memory_total_gb=gpu_total,
            gpu_memory_available_gb=gpu_available,
            gpu_memory_percent_available=gpu_percent,
            recommended_device=device,
            recommendation_reason=reason
        )

    def _get_recommendation(
        self,
        cpu_available: float,
        ram_percent: float,
        gpu_percent: float
    ) -> Tuple[ComputeDevice, str]:
        """
        Determine recommended compute device.

        Returns:
            Tuple of (device, reason)
        """
        gpu_ok = CUDA_AVAILABLE and gpu_percent >= (self.gpu_memory_threshold * 100)
        cpu_ok = cpu_available >= (self.cpu_threshold * 100)
        ram_ok = ram_percent >= (self.ram_threshold * 100)

        # Decision logic
        if gpu_ok and self.prefer_gpu:
            if gpu_percent > ram_percent:
                return ComputeDevice.GPU, f"GPU has more headroom ({gpu_percent:.0f}% vs {ram_percent:.0f}% RAM)"
            else:
                return ComputeDevice.GPU, f"GPU preferred and available ({gpu_percent:.0f}% free)"

        if not gpu_ok and CUDA_AVAILABLE:
            reason = f"GPU memory low ({gpu_percent:.0f}% free, need {self.gpu_memory_threshold*100:.0f}%)"
            if cpu_ok and ram_ok:
                return ComputeDevice.CPU, f"{reason} - using CPU"
            elif ram_ok:
                return ComputeDevice.CPU, f"{reason} - CPU busy but RAM available"
            else:
                return ComputeDevice.CPU, f"{reason} - resources constrained, using CPU"

        if not CUDA_AVAILABLE:
            if cpu_ok and ram_ok:
                return ComputeDevice.CPU, "No GPU - CPU and RAM available"
            elif ram_ok:
                return ComputeDevice.CPU, "No GPU - RAM available, CPU busy"
            else:
                return ComputeDevice.CPU, "No GPU - resources constrained"

        # Fallback
        if ram_percent > gpu_percent and ram_ok:
            return ComputeDevice.CPU, f"RAM has more headroom ({ram_percent:.0f}% vs {gpu_percent:.0f}% GPU)"

        return ComputeDevice.GPU if CUDA_AVAILABLE else ComputeDevice.CPU, "Default selection"

    def get_optimal_device(self) -> str:
        """
        Get the optimal device string for the current workload.

        Returns:
            'cuda' or 'cpu'
        """
        status = self.get_resource_status()
        return status.recommended_device.value

    def get_optimal_batch_size(self, base_batch_size: int = 32) -> int:
        """
        Calculate optimal batch size based on available memory.

        Args:
            base_batch_size: Default batch size for 8GB RAM/VRAM

        Returns:
            Adjusted batch size
        """
        status = self.get_resource_status()

        if status.recommended_device == ComputeDevice.GPU:
            # Scale based on GPU memory
            memory_gb = status.gpu_memory_available_gb
        else:
            # Scale based on RAM
            memory_gb = status.ram_available_gb

        # Scale: 8GB = base, 16GB = 2x, 4GB = 0.5x
        scale_factor = memory_gb / 8.0
        optimal = int(base_batch_size * scale_factor)

        # Clamp to reasonable range
        return max(1, min(optimal, base_batch_size * 4))

    def get_optimal_workers(self) -> int:
        """
        Get optimal number of worker threads/processes.

        Returns:
            Recommended worker count
        """
        status = self.get_resource_status()

        # Base on CPU cores and availability
        max_workers = status.cpu_cores

        if status.cpu_percent_available < 30:
            # System is busy, use fewer workers
            return max(1, max_workers // 4)
        elif status.cpu_percent_available < 50:
            return max(1, max_workers // 2)
        else:
            # Good availability, use most cores
            return max(1, max_workers - 1)

    def allocate_for_task(self, task_type: str = "inference") -> Dict[str, Any]:
        """
        Get allocation settings for a specific task type.

        Args:
            task_type: Type of task ('inference', 'training', 'batch_processing')

        Returns:
            Dict with device, batch_size, workers, and other settings
        """
        status = self.get_resource_status()
        device = status.recommended_device.value

        if task_type == "inference":
            # Single item inference - prioritize latency
            return {
                "device": device,
                "batch_size": 1,
                "workers": 1,
                "pin_memory": device == "cuda",
                "reason": status.recommendation_reason
            }

        elif task_type == "batch_processing":
            # Batch processing - prioritize throughput
            return {
                "device": device,
                "batch_size": self.get_optimal_batch_size(32),
                "workers": self.get_optimal_workers(),
                "pin_memory": device == "cuda",
                "prefetch_factor": 2 if device == "cuda" else 1,
                "reason": status.recommendation_reason
            }

        elif task_type == "training":
            # Training - balance memory and speed
            return {
                "device": device,
                "batch_size": self.get_optimal_batch_size(16),
                "workers": self.get_optimal_workers(),
                "pin_memory": device == "cuda",
                "gradient_accumulation": 1 if status.gpu_memory_available_gb > 4 else 2,
                "mixed_precision": device == "cuda" and status.gpu_memory_total_gb >= 6,
                "reason": status.recommendation_reason
            }

        else:
            # Default
            return {
                "device": device,
                "batch_size": self.get_optimal_batch_size(),
                "workers": self.get_optimal_workers(),
                "reason": status.recommendation_reason
            }

    def print_status(self):
        """Print current resource status"""
        status = self.get_resource_status()

        print("=" * 60)
        print("RESOURCE ALLOCATION STATUS")
        print("=" * 60)
        print()
        print("CPU:")
        print(f"  Cores: {status.cpu_cores}")
        print(f"  Usage: {status.cpu_percent_used:.1f}%")
        print(f"  Available: {status.cpu_percent_available:.1f}%")
        print()
        print("RAM:")
        print(f"  Total: {status.ram_total_gb:.1f} GB")
        print(f"  Available: {status.ram_available_gb:.1f} GB ({status.ram_percent_available:.1f}%)")
        print()
        print("GPU:")
        if status.gpu_available:
            print(f"  Device: {status.gpu_name}")
            print(f"  Memory Total: {status.gpu_memory_total_gb:.1f} GB")
            print(f"  Memory Available: {status.gpu_memory_available_gb:.1f} GB ({status.gpu_memory_percent_available:.1f}%)")
        else:
            print("  Not available")
        print()
        print("RECOMMENDATION:")
        print(f"  Device: {status.recommended_device.value.upper()}")
        print(f"  Reason: {status.recommendation_reason}")
        print("=" * 60)


# Singleton instance
_allocator_instance: Optional[DynamicResourceAllocator] = None


def get_resource_allocator() -> DynamicResourceAllocator:
    """Get or create the resource allocator singleton"""
    global _allocator_instance
    if _allocator_instance is None:
        _allocator_instance = DynamicResourceAllocator()
    return _allocator_instance


def get_optimal_device() -> str:
    """Quick function to get optimal device"""
    return get_resource_allocator().get_optimal_device()


def allocate_resources(task_type: str = "inference") -> Dict[str, Any]:
    """Quick function to get resource allocation for a task"""
    return get_resource_allocator().allocate_for_task(task_type)


# Export
__all__ = [
    'DynamicResourceAllocator',
    'ResourceStatus',
    'ComputeDevice',
    'get_resource_allocator',
    'get_optimal_device',
    'allocate_resources',
    'CUDA_AVAILABLE',
    'GPU_NAME',
    'GPU_MEMORY_GB',
]


if __name__ == "__main__":
    # Test the allocator
    allocator = get_resource_allocator()
    allocator.print_status()

    print()
    print("Task Allocations:")
    print("-" * 40)
    for task in ["inference", "batch_processing", "training"]:
        alloc = allocator.allocate_for_task(task)
        print(f"\n{task.upper()}:")
        for k, v in alloc.items():
            print(f"  {k}: {v}")
