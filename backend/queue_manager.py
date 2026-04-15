import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
import asyncio


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    id: str
    type: str  # "text2image" or "image2image"
    params: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_url: Optional[str] = None  # 单张图片结果（向后兼容）
    result_urls: list = field(default_factory=list)  # 多张图片结果
    error_message: Optional[str] = None
    progress: int = 0  # 0-100
    comfyui_prompt_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "type": self.type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result_url": self.result_url,
            "result_urls": self.result_urls,
            "error_message": self.error_message,
            "progress": self.progress,
        }
        # 如果有多张图片但没有单张结果，使用第一张作为兼容
        if not self.result_url and self.result_urls:
            result["result_url"] = self.result_urls[0]
        return result


class QueueManager:
    """任务队列管理器"""

    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.queue: asyncio.Queue[Task] = asyncio.Queue()
        self.tasks: Dict[str, Task] = {}
        self._progress_callbacks: Dict[str, Callable[[Task], None]] = {}
        self._lock = asyncio.Lock()

    async def submit_task(self, task_type: str, params: Dict[str, Any]) -> Optional[Task]:
        """提交任务到队列"""
        async with self._lock:
            # 检查队列是否已满
            pending_count = sum(
                1 for t in self.tasks.values()
                if t.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]
            )
            if pending_count >= self.max_size:
                return None

            task = Task(
                id=str(uuid.uuid4()),
                type=task_type,
                params=params,
            )
            self.tasks[task.id] = task
            await self.queue.put(task)
            return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务信息"""
        return self.tasks.get(task_id)

    async def get_next_task(self) -> Optional[Task]:
        """获取下一个待处理任务"""
        try:
            task = await self.queue.get()
            async with self._lock:
                # 检查任务是否已被取消
                if task.status == TaskStatus.CANCELLED:
                    return None
                task.status = TaskStatus.PROCESSING
                task.started_at = datetime.now()
            return task
        except asyncio.CancelledError:
            return None

    async def is_task_cancelled(self, task_id: str) -> bool:
        """检查任务是否已被取消"""
        async with self._lock:
            if task_id not in self.tasks:
                return True
            return self.tasks[task_id].status == TaskStatus.CANCELLED

    async def complete_task(self, task_id: str, result_url: str = None, result_urls: list = None):
        """标记任务完成"""
        async with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.progress = 100
                if result_url:
                    task.result_url = result_url
                if result_urls:
                    task.result_urls = result_urls
                    # 向后兼容：如果没有单张结果，使用第一张
                    if not task.result_url:
                        task.result_url = result_urls[0] if result_urls else None
                await self._notify_progress(task)

    async def fail_task(self, task_id: str, error_message: str):
        """标记任务失败"""
        async with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                task.error_message = error_message
                await self._notify_progress(task)

    async def update_progress(self, task_id: str, progress: int):
        """更新任务进度"""
        async with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.progress = min(max(progress, 0), 100)
                await self._notify_progress(task)

    async def set_comfyui_prompt_id(self, task_id: str, prompt_id: str):
        """设置 ComfyUI prompt ID"""
        async with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].comfyui_prompt_id = prompt_id

    def register_progress_callback(self, task_id: str, callback: Callable[[Task], None]):
        """注册进度回调"""
        self._progress_callbacks[task_id] = callback

    def unregister_progress_callback(self, task_id: str):
        """取消注册进度回调"""
        if task_id in self._progress_callbacks:
            del self._progress_callbacks[task_id]

    async def _notify_progress(self, task: Task):
        """通知进度更新"""
        callback = self._progress_callbacks.get(task.id)
        if callback:
            try:
                callback(task)
            except Exception:
                pass

    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        pending = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
        processing = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PROCESSING)
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)

        return {
            "max_size": self.max_size,
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "failed": failed,
            "available_slots": self.max_size - pending - processing,
        }

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        async with self._lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]

            # 只能取消等待中或处理中的任务
            if task.status not in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
                return False

            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            task.error_message = "任务已被用户取消"
            await self._notify_progress(task)
            return True

    def get_recent_tasks(self, limit: int = 20) -> list:
        """获取最近的任务列表"""
        sorted_tasks = sorted(
            self.tasks.values(),
            key=lambda t: t.created_at,
            reverse=True
        )
        return [t.to_dict() for t in sorted_tasks[:limit]]


# 全局队列管理器实例
queue_manager = QueueManager()