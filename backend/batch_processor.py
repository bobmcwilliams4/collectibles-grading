"""
Batch Processing System
High-performance parallel batch grading with progress tracking
"""

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import aiofiles

logger = logging.getLogger(__name__)


class BatchStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ItemStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BatchItem:
    """Individual item in a batch"""
    id: str
    front_image: str
    back_image: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ItemStatus = ItemStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retries: int = 0


@dataclass
class BatchJob:
    """Batch processing job"""
    id: str
    name: str
    items: List[BatchItem]
    status: BatchStatus = BatchStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    concurrency: int = 3
    max_retries: int = 2
    pause_on_error: bool = False

    # Statistics
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0

    def __post_init__(self):
        self.total_items = len(self.items)


class BatchProcessor:
    """
    High-Performance Batch Processing System

    Features:
    - Parallel processing with configurable concurrency
    - Progress tracking and callbacks
    - Pause/resume support
    - Automatic retry on failure
    - Checkpoint saving for crash recovery
    - Memory-efficient streaming
    """

    def __init__(
        self,
        grader_func: Callable,
        checkpoint_dir: str = "P:/SOVEREIGN_APPS/collectibles_grading_system/data/checkpoints"
    ):
        self.grader_func = grader_func
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self._active_jobs: Dict[str, BatchJob] = {}
        self._pause_events: Dict[str, asyncio.Event] = {}
        self._cancel_events: Dict[str, asyncio.Event] = {}

        self._progress_callbacks: List[Callable] = []
        self._completion_callbacks: List[Callable] = []

    def on_progress(self, callback: Callable):
        """Register progress callback"""
        self._progress_callbacks.append(callback)

    def on_completion(self, callback: Callable):
        """Register completion callback"""
        self._completion_callbacks.append(callback)

    async def create_batch(
        self,
        name: str,
        items: List[Dict[str, Any]],
        concurrency: int = 3,
        max_retries: int = 2,
        pause_on_error: bool = False
    ) -> BatchJob:
        """
        Create a new batch job

        Args:
            name: Human-readable batch name
            items: List of dicts with 'front_image', optional 'back_image', 'metadata'
            concurrency: Number of parallel workers
            max_retries: Max retry attempts per item
            pause_on_error: Pause batch on first error

        Returns:
            BatchJob instance
        """
        batch_id = str(uuid.uuid4())[:8]

        batch_items = [
            BatchItem(
                id=f"{batch_id}-{i:04d}",
                front_image=item['front_image'],
                back_image=item.get('back_image'),
                metadata=item.get('metadata', {})
            )
            for i, item in enumerate(items)
        ]

        job = BatchJob(
            id=batch_id,
            name=name,
            items=batch_items,
            concurrency=concurrency,
            max_retries=max_retries,
            pause_on_error=pause_on_error
        )

        self._active_jobs[batch_id] = job
        self._pause_events[batch_id] = asyncio.Event()
        self._pause_events[batch_id].set()  # Not paused by default
        self._cancel_events[batch_id] = asyncio.Event()

        # Save initial checkpoint
        await self._save_checkpoint(job)

        logger.info(f"Created batch job {batch_id} with {len(batch_items)} items")
        return job

    async def start_batch(self, batch_id: str) -> BatchJob:
        """Start processing a batch"""
        job = self._active_jobs.get(batch_id)
        if not job:
            raise ValueError(f"Batch {batch_id} not found")

        if job.status == BatchStatus.RUNNING:
            logger.warning(f"Batch {batch_id} is already running")
            return job

        job.status = BatchStatus.RUNNING
        job.started_at = datetime.utcnow()

        # Create worker tasks
        asyncio.create_task(self._run_batch(job))

        return job

    async def _run_batch(self, job: BatchJob):
        """Run batch processing with worker pool"""
        semaphore = asyncio.Semaphore(job.concurrency)
        tasks = []

        for item in job.items:
            if item.status == ItemStatus.COMPLETED:
                continue  # Skip already completed items (from checkpoint)

            task = asyncio.create_task(
                self._process_item(job, item, semaphore)
            )
            tasks.append(task)

        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Batch {job.id} failed: {e}")
            job.status = BatchStatus.FAILED

        # Finalize job
        if self._cancel_events[job.id].is_set():
            job.status = BatchStatus.CANCELLED
        elif job.failed_items > 0 and job.pause_on_error:
            job.status = BatchStatus.PAUSED
        elif all(item.status in (ItemStatus.COMPLETED, ItemStatus.SKIPPED) for item in job.items):
            job.status = BatchStatus.COMPLETED
        else:
            job.status = BatchStatus.FAILED

        job.completed_at = datetime.utcnow()
        await self._save_checkpoint(job)

        # Notify completion
        for callback in self._completion_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(job)
                else:
                    callback(job)
            except Exception as e:
                logger.error(f"Completion callback error: {e}")

        logger.info(
            f"Batch {job.id} finished: "
            f"{job.completed_items} completed, "
            f"{job.failed_items} failed, "
            f"{job.skipped_items} skipped"
        )

    async def _process_item(
        self,
        job: BatchJob,
        item: BatchItem,
        semaphore: asyncio.Semaphore
    ):
        """Process a single batch item"""
        async with semaphore:
            # Check for pause
            await self._pause_events[job.id].wait()

            # Check for cancellation
            if self._cancel_events[job.id].is_set():
                item.status = ItemStatus.SKIPPED
                job.skipped_items += 1
                return

            item.status = ItemStatus.PROCESSING
            item.started_at = datetime.utcnow()

            try:
                result = await self.grader_func(
                    item.front_image,
                    item.back_image,
                    item.metadata
                )

                item.result = result
                item.status = ItemStatus.COMPLETED
                item.completed_at = datetime.utcnow()
                job.completed_items += 1

            except Exception as e:
                logger.error(f"Item {item.id} failed: {e}")
                item.error = str(e)

                # Retry logic
                if item.retries < job.max_retries:
                    item.retries += 1
                    item.status = ItemStatus.PENDING
                    logger.info(f"Retrying item {item.id} (attempt {item.retries})")
                    await self._process_item(job, item, semaphore)
                    return

                item.status = ItemStatus.FAILED
                item.completed_at = datetime.utcnow()
                job.failed_items += 1

                if job.pause_on_error:
                    self._pause_events[job.id].clear()
                    job.status = BatchStatus.PAUSED

            # Update progress
            processed = job.completed_items + job.failed_items + job.skipped_items
            job.progress = processed / job.total_items

            # Notify progress
            for callback in self._progress_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(job, item)
                    else:
                        callback(job, item)
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")

            # Periodic checkpoint
            if processed % 10 == 0:
                await self._save_checkpoint(job)

    async def pause_batch(self, batch_id: str):
        """Pause a running batch"""
        if batch_id in self._pause_events:
            self._pause_events[batch_id].clear()
            if batch_id in self._active_jobs:
                self._active_jobs[batch_id].status = BatchStatus.PAUSED
            logger.info(f"Batch {batch_id} paused")

    async def resume_batch(self, batch_id: str):
        """Resume a paused batch"""
        if batch_id in self._pause_events:
            self._pause_events[batch_id].set()
            if batch_id in self._active_jobs:
                job = self._active_jobs[batch_id]
                if job.status == BatchStatus.PAUSED:
                    job.status = BatchStatus.RUNNING
            logger.info(f"Batch {batch_id} resumed")

    async def cancel_batch(self, batch_id: str):
        """Cancel a batch"""
        if batch_id in self._cancel_events:
            self._cancel_events[batch_id].set()
            # Also unblock pause if set
            if batch_id in self._pause_events:
                self._pause_events[batch_id].set()
            logger.info(f"Batch {batch_id} cancelled")

    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get batch status"""
        job = self._active_jobs.get(batch_id)
        if not job:
            return None

        return {
            'id': job.id,
            'name': job.name,
            'status': job.status.value,
            'progress': job.progress,
            'total_items': job.total_items,
            'completed_items': job.completed_items,
            'failed_items': job.failed_items,
            'skipped_items': job.skipped_items,
            'created_at': job.created_at.isoformat(),
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None
        }

    def get_batch_results(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get all results from a batch"""
        job = self._active_jobs.get(batch_id)
        if not job:
            return []

        return [
            {
                'id': item.id,
                'front_image': item.front_image,
                'status': item.status.value,
                'result': item.result,
                'error': item.error
            }
            for item in job.items
        ]

    async def _save_checkpoint(self, job: BatchJob):
        """Save batch checkpoint for crash recovery"""
        checkpoint_path = self.checkpoint_dir / f"{job.id}.json"

        checkpoint_data = {
            'id': job.id,
            'name': job.name,
            'status': job.status.value,
            'created_at': job.created_at.isoformat(),
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'concurrency': job.concurrency,
            'max_retries': job.max_retries,
            'pause_on_error': job.pause_on_error,
            'items': [
                {
                    'id': item.id,
                    'front_image': item.front_image,
                    'back_image': item.back_image,
                    'metadata': item.metadata,
                    'status': item.status.value,
                    'result': item.result,
                    'error': item.error,
                    'retries': item.retries
                }
                for item in job.items
            ]
        }

        async with aiofiles.open(checkpoint_path, 'w') as f:
            await f.write(json.dumps(checkpoint_data, indent=2))

    async def load_checkpoint(self, batch_id: str) -> Optional[BatchJob]:
        """Load batch from checkpoint"""
        checkpoint_path = self.checkpoint_dir / f"{batch_id}.json"

        if not checkpoint_path.exists():
            return None

        try:
            async with aiofiles.open(checkpoint_path, 'r') as f:
                data = json.loads(await f.read())

            items = [
                BatchItem(
                    id=item['id'],
                    front_image=item['front_image'],
                    back_image=item['back_image'],
                    metadata=item['metadata'],
                    status=ItemStatus(item['status']),
                    result=item['result'],
                    error=item['error'],
                    retries=item['retries']
                )
                for item in data['items']
            ]

            job = BatchJob(
                id=data['id'],
                name=data['name'],
                items=items,
                status=BatchStatus(data['status']),
                created_at=datetime.fromisoformat(data['created_at']),
                concurrency=data['concurrency'],
                max_retries=data['max_retries'],
                pause_on_error=data['pause_on_error']
            )

            if data['started_at']:
                job.started_at = datetime.fromisoformat(data['started_at'])
            if data['completed_at']:
                job.completed_at = datetime.fromisoformat(data['completed_at'])

            # Recalculate stats
            job.completed_items = sum(1 for i in items if i.status == ItemStatus.COMPLETED)
            job.failed_items = sum(1 for i in items if i.status == ItemStatus.FAILED)
            job.skipped_items = sum(1 for i in items if i.status == ItemStatus.SKIPPED)
            job.progress = (job.completed_items + job.failed_items + job.skipped_items) / job.total_items

            self._active_jobs[job.id] = job
            self._pause_events[job.id] = asyncio.Event()
            self._pause_events[job.id].set()
            self._cancel_events[job.id] = asyncio.Event()

            logger.info(f"Loaded batch {job.id} from checkpoint")
            return job

        except Exception as e:
            logger.error(f"Failed to load checkpoint {batch_id}: {e}")
            return None

    async def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints"""
        checkpoints = []

        for path in self.checkpoint_dir.glob("*.json"):
            try:
                async with aiofiles.open(path, 'r') as f:
                    data = json.loads(await f.read())

                checkpoints.append({
                    'id': data['id'],
                    'name': data['name'],
                    'status': data['status'],
                    'total_items': len(data['items']),
                    'created_at': data['created_at']
                })
            except Exception as e:
                logger.warning(f"Failed to read checkpoint {path}: {e}")

        return sorted(checkpoints, key=lambda x: x['created_at'], reverse=True)


class BatchImporter:
    """
    Batch Import from Various Sources

    Supports:
    - Directory scanning
    - CSV import
    - JSON import
    - Zip archive extraction
    """

    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.tiff', '.bmp'}

    @staticmethod
    async def from_directory(
        directory: str,
        pattern: str = "*_front.*",
        back_pattern: str = "*_back.*"
    ) -> List[Dict[str, Any]]:
        """
        Import from directory with front/back naming convention

        Args:
            directory: Source directory
            pattern: Glob pattern for front images
            back_pattern: Glob pattern for back images

        Returns:
            List of item dicts
        """
        dir_path = Path(directory)
        items = []

        # Find front images
        for ext in BatchImporter.SUPPORTED_EXTENSIONS:
            for front_path in dir_path.glob(f"*_front{ext}"):
                stem = front_path.stem.replace('_front', '')

                # Look for matching back
                back_path = None
                for back_ext in BatchImporter.SUPPORTED_EXTENSIONS:
                    potential_back = dir_path / f"{stem}_back{back_ext}"
                    if potential_back.exists():
                        back_path = str(potential_back)
                        break

                items.append({
                    'front_image': str(front_path),
                    'back_image': back_path,
                    'metadata': {'source_name': stem}
                })

        # Also find images without front/back naming
        for ext in BatchImporter.SUPPORTED_EXTENSIONS:
            for img_path in dir_path.glob(f"*{ext}"):
                if '_front' not in img_path.stem and '_back' not in img_path.stem:
                    # Check if not already captured
                    if not any(str(img_path) in str(item.values()) for item in items):
                        items.append({
                            'front_image': str(img_path),
                            'back_image': None,
                            'metadata': {'source_name': img_path.stem}
                        })

        return items

    @staticmethod
    async def from_csv(csv_path: str) -> List[Dict[str, Any]]:
        """
        Import from CSV file

        Expected columns: front_image, back_image (optional), title, issue_number, publisher
        """
        import csv

        items = []

        async with aiofiles.open(csv_path, 'r') as f:
            content = await f.read()

        reader = csv.DictReader(content.splitlines())

        for row in reader:
            if 'front_image' not in row:
                continue

            items.append({
                'front_image': row['front_image'],
                'back_image': row.get('back_image'),
                'metadata': {
                    'title': row.get('title'),
                    'issue_number': row.get('issue_number'),
                    'publisher': row.get('publisher'),
                    **{k: v for k, v in row.items()
                       if k not in ('front_image', 'back_image', 'title', 'issue_number', 'publisher')}
                }
            })

        return items

    @staticmethod
    async def from_json(json_path: str) -> List[Dict[str, Any]]:
        """Import from JSON file"""
        async with aiofiles.open(json_path, 'r') as f:
            data = json.loads(await f.read())

        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'items' in data:
            return data['items']
        else:
            raise ValueError("Invalid JSON format")


# Export functions
async def create_batch_processor(grader_func: Callable) -> BatchProcessor:
    """Create a batch processor instance"""
    return BatchProcessor(grader_func)
