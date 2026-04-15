import aiohttp
import asyncio
import json
import os
import random
from typing import Optional, Dict, Any, Callable
from pathlib import Path
import base64

from config import get_settings


class ComfyUIClient:
    """ComfyUI API 客户端"""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.comfyui_url
        self.output_dir = Path(self.settings.output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def _get_text2image_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """构建文生图工作流"""
        # 处理 seed：-1 表示随机生成
        seed = params.get("seed", -1)
        if seed is None or seed < 0:
            seed = random.randint(0, 2**32 - 1)

        return {
            "1": {
                "class_type": "LongCatImageModelLoader",
                "inputs": {
                    "model_path": "LongCat-Image",
                    "dtype": "bfloat16",
                    "attention_backend": "default",
                    "enable_cpu_offload": "false"
                }
            },
            "2": {
                "class_type": "LongCatImageTextToImage",
                "inputs": {
                    "longcat_pipeline": ["1", 0],
                    "prompt": params.get("prompt", ""),
                    "negative_prompt": params.get("negative_prompt", ""),
                    "width": params.get("width", 1024),
                    "height": params.get("height", 1024),
                    "steps": params.get("steps", 20),
                    "guidance_scale": params.get("guidance_scale", 4.5),
                    "seed": seed,
                    "enable_cfg_renorm": "true",
                    "enable_prompt_rewrite": "true"
                }
            },
            "3": {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["2", 0],
                    "filename_prefix": "text2image"
                }
            }
        }

    def _get_image2image_workflow(self, params: Dict[str, Any], uploaded_image_name: str) -> Dict[str, Any]:
        """构建图生图工作流"""
        # 处理 seed：-1 表示随机生成
        seed = params.get("seed", -1)
        if seed is None or seed < 0:
            seed = random.randint(0, 2**32 - 1)

        return {
            "2": {
                "inputs": {
                    "model_path": "LongCat-Image-Edit",
                    "dtype": "bfloat16",
                    "enable_cpu_offload": "true",
                    "attention_backend": "default"
                },
                "class_type": "LongCatImageModelLoader"
            },
            "5": {
                "inputs": {
                    "filename_prefix": "image2image",
                    "images": ["6", 0]
                },
                "class_type": "SaveImage"
            },
            "6": {
                "inputs": {
                    "prompt": params.get("prompt", ""),
                    "negative_prompt": params.get("negative_prompt", ""),
                    "steps": params.get("steps", 50),
                    "guidance_scale": params.get("guidance_scale", 4.5),
                    "seed": seed,
                    "longcat_pipeline": ["2", 0],
                    "image": ["14", 0]
                },
                "class_type": "LongCatImageEdit"
            },
            "7": {
                "inputs": {
                    "image": uploaded_image_name
                },
                "class_type": "LoadImage"
            },
            "12": {
                "inputs": {
                    "image": ["7", 0]
                },
                "class_type": "GetImageSize"
            },
            "13": {
                "inputs": {
                    "width": ["12", 0],
                    "height": ["12", 1],
                    "batch_size": 1,
                    "color": 16711680
                },
                "class_type": "EmptyImage"
            },
            "14": {
                "inputs": {
                    "x": 0,
                    "y": 0,
                    "resize_source": False,
                    "destination": ["7", 0],
                    "source": ["13", 0],
                    "mask": ["7", 1]
                },
                "class_type": "ImageCompositeMasked"
            }
        }

    async def upload_image(self, image_data: bytes, filename: str) -> Optional[str]:
        """上传图片到 ComfyUI"""
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('image', image_data, filename=filename,
                             content_type='image/png')

                async with session.post(f"{self.base_url}/upload/image", data=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get('name')
                    else:
                        error_text = await resp.text()
                        raise Exception(f"上传失败: {error_text}")
        except Exception as e:
            raise Exception(f"上传图片失败: {str(e)}")

    async def submit_prompt(self, workflow: Dict[str, Any]) -> str:
        """提交工作流到 ComfyUI"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/prompt",
                    json={"prompt": workflow}
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result["prompt_id"]
                    else:
                        error_text = await resp.text()
                        raise Exception(f"提交失败: {error_text}")
        except Exception as e:
            raise Exception(f"提交工作流失败: {str(e)}")

    async def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """获取任务历史"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/history/{prompt_id}") as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None
        except Exception:
            return None

    async def download_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> str:
        """下载生成的图片到本地"""
        try:
            url = f"{self.base_url}/view?filename={filename}"
            if subfolder:
                url += f"&subfolder={subfolder}"
            url += f"&type={folder_type}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        # 生成本地文件名
                        local_filename = f"{Path(filename).stem}_{asyncio.get_event_loop().time()}.png"
                        local_path = self.output_dir / local_filename

                        with open(local_path, 'wb') as f:
                            f.write(await resp.read())

                        return str(local_path)
                    else:
                        raise Exception(f"下载图片失败: {resp.status}")
        except Exception as e:
            raise Exception(f"下载图片失败: {str(e)}")

    async def interrupt(self) -> bool:
        """中断 ComfyUI 当前正在运行的任务"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/interrupt") as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def wait_for_completion(
        self,
        prompt_id: str,
        progress_callback: Optional[Callable[[int], None]] = None,
        is_cancelled_callback: Optional[Callable[[], bool]] = None,
        check_interval: float = 1.0
    ) -> str:
        """等待任务完成并返回结果图片路径"""
        max_retries = 600  # 最多等待 600 秒（10 分钟）
        retries = 0

        while retries < max_retries:
            # 检查是否被取消
            if is_cancelled_callback and is_cancelled_callback():
                # 尝试中断 ComfyUI 任务
                await self.interrupt()
                raise Exception("任务已被用户取消")

            history = await self.get_history(prompt_id)

            if history and prompt_id in history:
                task_data = history[prompt_id]

                # 检查是否有输出
                if "outputs" in task_data:
                    outputs = task_data["outputs"]

                    # 查找保存的图片
                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            image_info = node_output["images"][0]
                            filename = image_info["filename"]
                            subfolder = image_info.get("subfolder", "")
                            folder_type = image_info.get("type", "output")

                            # 下载图片到本地
                            local_path = await self.download_image(
                                filename, subfolder, folder_type
                            )
                            return local_path

                # 检查是否失败
                if task_data.get("status", {}).get("status_str") == "error":
                    error_msg = task_data.get("status", {}).get("messages", [["", "未知错误"]])[-1][-1]
                    raise Exception(f"生成失败: {error_msg}")

                # 更新进度（模拟，因为 ComfyUI 不直接提供进度）
                if progress_callback:
                    # 基于时间估算进度
                    estimated_progress = min(int((retries / 100) * 100), 95)
                    progress_callback(estimated_progress)

            await asyncio.sleep(check_interval)
            retries += 1

        raise Exception("生成超时，请稍后查看结果")

    async def generate_text2image(
        self,
        params: Dict[str, Any],
        progress_callback: Optional[Callable[[int], None]] = None,
        is_cancelled_callback: Optional[Callable[[], bool]] = None
    ) -> list[str]:
        """文生图，支持生成多张"""
        num_images = params.get("num_images", 1)
        base_seed = params.get("seed", 0)
        result_paths = []

        for i in range(num_images):
            # 检查是否被取消
            if is_cancelled_callback and is_cancelled_callback():
                raise Exception("任务已被用户取消")

            # 每张图片使用不同的种子
            current_params = params.copy()
            if num_images > 1:
                current_params["seed"] = base_seed + i if base_seed > 0 else random.randint(0, 2**32 - 1)

            workflow = self._get_text2image_workflow(current_params)
            prompt_id = await self.submit_prompt(workflow)
            result_path = await self.wait_for_completion(
                prompt_id,
                lambda p: progress_callback(int(p * (i + 1) / num_images)) if progress_callback else None,
                is_cancelled_callback
            )
            result_paths.append(result_path)

        return result_paths

    async def generate_image2image(
        self,
        params: Dict[str, Any],
        image_data: bytes,
        filename: str,
        progress_callback: Optional[Callable[[int], None]] = None,
        is_cancelled_callback: Optional[Callable[[], bool]] = None
    ) -> list[str]:
        """图生图，支持生成多张"""
        num_images = params.get("num_images", 1)
        base_seed = params.get("seed", 0)

        # 上传图片（只需上传一次）
        uploaded_name = await self.upload_image(image_data, filename)

        result_paths = []
        for i in range(num_images):
            # 检查是否被取消
            if is_cancelled_callback and is_cancelled_callback():
                raise Exception("任务已被用户取消")

            # 每张图片使用不同的种子
            current_params = params.copy()
            if num_images > 1:
                current_params["seed"] = base_seed + i if base_seed > 0 else random.randint(0, 2**32 - 1)

            workflow = self._get_image2image_workflow(current_params, uploaded_name)
            prompt_id = await self.submit_prompt(workflow)
            result_path = await self.wait_for_completion(
                prompt_id,
                lambda p: progress_callback(int(p * (i + 1) / num_images)) if progress_callback else None,
                is_cancelled_callback
            )
            result_paths.append(result_path)

        return result_paths


# 全局客户端实例
comfyui_client = ComfyUIClient()