import asyncio
from contextlib import asynccontextmanager
from typing import Optional
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import uvicorn

from config import get_settings
from queue_manager import queue_manager, Task, TaskStatus
from comfyui_client import comfyui_client


# 请求模型
class Text2ImageRequest(BaseModel):
    prompt: str = Field(..., description="正向提示词")
    negative_prompt: str = Field(default="", description="反向提示词")
    width: int = Field(default=1024, ge=512, le=2048, description="图片宽度")
    height: int = Field(default=1024, ge=512, le=2048, description="图片高度")
    steps: int = Field(default=20, ge=1, le=100, description="迭代步数")
    guidance_scale: float = Field(default=4.5, ge=1.0, le=20.0, description="CFG Scale")
    seed: int = Field(default=0, ge=0, description="随机种子，0 表示随机")
    num_images: int = Field(default=1, ge=1, le=4, description="一次生成图片数量，1-4张")


class Image2ImageRequest(BaseModel):
    prompt: str = Field(..., description="正向提示词")
    negative_prompt: str = Field(default="", description="反向提示词")
    steps: int = Field(default=50, ge=1, le=100, description="迭代步数")
    guidance_scale: float = Field(default=4.5, ge=1.0, le=20.0, description="CFG Scale")
    seed: int = Field(default=0, ge=0, description="随机种子，0 表示随机")
    num_images: int = Field(default=1, ge=1, le=4, description="一次生成图片数量，1-4张")


# WebSocket 连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


# 后台任务处理器
async def process_queue():
    """处理队列中的任务"""
    while True:
        try:
            task = await queue_manager.get_next_task()
            if task:
                await process_task(task)
            else:
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"队列处理错误: {e}")
            await asyncio.sleep(1)


async def process_task(task: Task):
    """处理单个任务"""
    try:
        # 定义进度回调
        def progress_callback(progress: int):
            asyncio.create_task(queue_manager.update_progress(task.id, progress))
            # 广播进度更新
            asyncio.create_task(manager.broadcast({
                "type": "progress",
                "task_id": task.id,
                "progress": progress
            }))

        # 定义取消检查回调
        def is_cancelled_callback():
            # 使用 asyncio.run_coroutine_thread_safe 或检查同步状态
            # 这里简单起见，直接返回 False，实际取消通过异常处理
            return False

        # 根据任务类型执行生成
        if task.type == "text2image":
            result_paths = await comfyui_client.generate_text2image(
                task.params,
                progress_callback=progress_callback,
                is_cancelled_callback=lambda: False  # 简化处理，通过异常中断
            )
        elif task.type == "image2image":
            image_data = task.params.pop("_image_data")
            filename = task.params.pop("_filename")
            result_paths = await comfyui_client.generate_image2image(
                task.params,
                image_data,
                filename,
                progress_callback=progress_callback,
                is_cancelled_callback=lambda: False
            )
        else:
            raise ValueError(f"未知任务类型: {task.type}")

        # 标记任务完成（支持多张图片）
        await queue_manager.complete_task(
            task.id,
            result_url=result_paths[0] if result_paths else None,
            result_urls=result_paths
        )

        # 广播完成消息
        await manager.broadcast({
            "type": "completed",
            "task_id": task.id,
            "result_url": f"/api/images/{task.id}",
            "result_urls": [f"/api/images/{task.id}/{i}" for i in range(len(result_paths))] if len(result_paths) > 1 else None
        })

    except Exception as e:
        error_msg = str(e)
        await queue_manager.fail_task(task.id, error_msg)

        # 广播失败消息
        await manager.broadcast({
            "type": "failed",
            "task_id": task.id,
            "error": error_msg
        })


# 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时开始队列处理
    task = asyncio.create_task(process_queue())
    yield
    # 关闭时取消任务
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# 创建应用
app = FastAPI(
    title="AI 图像生成 API",
    description="基于 ComfyUI + LongCat 模型的图像生成服务",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API 路由
@app.post("/api/text2image")
async def create_text2image_task(request: Text2ImageRequest):
    """创建文生图任务"""
    task = await queue_manager.submit_task("text2image", request.dict())

    if not task:
        raise HTTPException(status_code=503, detail="队列已满，请稍后重试")

    return {
        "success": True,
        "task_id": task.id,
        "status": task.status.value,
        "message": "任务已提交到队列"
    }


@app.post("/api/image2image")
async def create_image2image_task(
    prompt: str = Form(...),
    negative_prompt: str = Form(default=""),
    steps: int = Form(default=50),
    guidance_scale: float = Form(default=4.5),
    seed: int = Form(default=0),
    num_images: int = Form(default=1),
    image: UploadFile = File(...)
):
    """创建图生图任务"""
    # 读取上传的图片
    image_data = await image.read()

    if len(image_data) > 10 * 1024 * 1024:  # 限制 10MB
        raise HTTPException(status_code=400, detail="图片大小超过 10MB 限制")

    params = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "guidance_scale": guidance_scale,
        "seed": seed,
        "num_images": num_images,
        "_image_data": image_data,
        "_filename": image.filename or "upload.png"
    }

    task = await queue_manager.submit_task("image2image", params)

    if not task:
        raise HTTPException(status_code=503, detail="队列已满，请稍后重试")

    return {
        "success": True,
        "task_id": task.id,
        "status": task.status.value,
        "message": "任务已提交到队列"
    }


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    task = await queue_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return task.to_dict()


@app.get("/api/queue/status")
async def get_queue_status():
    """获取队列状态"""
    return queue_manager.get_queue_status()


@app.get("/api/tasks")
async def get_recent_tasks(limit: int = 20):
    """获取最近的任务列表"""
    return queue_manager.get_recent_tasks(limit)


@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消任务"""
    task = await queue_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 检查任务状态
    if task.status.value not in ["pending", "processing"]:
        raise HTTPException(status_code=400, detail=f"任务状态为 {task.status.value}，无法取消")

    # 取消任务
    success = await queue_manager.cancel_task(task_id)

    if success:
        # 广播取消消息
        await manager.broadcast({
            "type": "cancelled",
            "task_id": task_id
        })
        return {
            "success": True,
            "message": "任务已取消"
        }
    else:
        raise HTTPException(status_code=400, detail="取消任务失败")


@app.get("/api/images/{task_id}")
async def get_image(task_id: str, index: int = 0):
    """获取生成的图片（默认第一张，可通过 index 参数获取其他图片）"""
    task = await queue_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="图片尚未生成完成")

    # 支持多张图片
    if task.result_urls and 0 <= index < len(task.result_urls):
        return FileResponse(task.result_urls[index])
    elif task.result_url and index == 0:
        return FileResponse(task.result_url)
    else:
        raise HTTPException(status_code=404, detail="图片文件不存在")


# WebSocket 路由
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            try:
                message = json.loads(data)

                # 处理订阅请求
                if message.get("type") == "subscribe" and "task_id" in message:
                    task_id = message["task_id"]

                    # 注册进度回调
                    def make_callback(ws):
                        def callback(task: Task):
                            asyncio.create_task(ws.send_json({
                                "type": "progress",
                                "task_id": task.id,
                                "progress": task.progress,
                                "status": task.status.value
                            }))
                        return callback

                    queue_manager.register_progress_callback(task_id, make_callback(websocket))

                    # 发送确认
                    await websocket.send_json({
                        "type": "subscribed",
                        "task_id": task_id
                    })

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# 主入口
if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )