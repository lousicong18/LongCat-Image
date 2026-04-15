#!/usr/bin/env python3
"""
AI Image Generator - OpenClaw Skill Script
用于调用 AI 图像生成服务的辅助脚本
"""

import argparse
import json
import sys
import time
import requests
from typing import Optional, Dict, Any

# 服务配置
BASE_URL = "http://192.168.20.202:10018"


def text2image(
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    steps: int = 20,
    guidance_scale: float = 4.5,
    seed: int = 0,
    num_images: int = 1,
    wait: bool = True
) -> Dict[str, Any]:
    """文生图"""
    url = f"{BASE_URL}/api/text2image"
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "guidance_scale": guidance_scale,
        "seed": seed,
        "num_images": num_images
    }

    response = requests.post(url, json=payload)
    result = response.json()

    if not result.get("success"):
        return {"status": "error", "message": result.get("message", "提交失败")}

    task_id = result["task_id"]

    if wait:
        return wait_for_completion(task_id)

    return {"status": "submitted", "task_id": task_id}


def image2image(
    prompt: str,
    image_path: str,
    negative_prompt: str = "",
    steps: int = 50,
    guidance_scale: float = 4.5,
    seed: int = 0,
    num_images: int = 1,
    wait: bool = True
) -> Dict[str, Any]:
    """图生图"""
    url = f"{BASE_URL}/api/image2image"

    with open(image_path, "rb") as f:
        files = {"image": f}
        data = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "seed": seed,
            "num_images": num_images
        }
        response = requests.post(url, files=files, data=data)

    result = response.json()

    if not result.get("success"):
        return {"status": "error", "message": result.get("message", "提交失败")}

    task_id = result["task_id"]

    if wait:
        return wait_for_completion(task_id)

    return {"status": "submitted", "task_id": task_id}


def get_task_status(task_id: str) -> Dict[str, Any]:
    """获取任务状态"""
    url = f"{BASE_URL}/api/tasks/{task_id}"
    response = requests.get(url)
    return response.json()


def cancel_task(task_id: str) -> Dict[str, Any]:
    """取消任务"""
    url = f"{BASE_URL}/api/tasks/{task_id}/cancel"
    response = requests.post(url)
    return response.json()


def get_queue_status() -> Dict[str, Any]:
    """获取队列状态"""
    url = f"{BASE_URL}/api/queue/status"
    response = requests.get(url)
    return response.json()


def wait_for_completion(task_id: str, timeout: int = 600) -> Dict[str, Any]:
    """等待任务完成"""
    start_time = time.time()

    while time.time() - start_time < timeout:
        status = get_task_status(task_id)

        if status["status"] == "completed":
            images = []
            if status.get("result_urls"):
                for i, _ in enumerate(status["result_urls"]):
                    images.append(f"{BASE_URL}/api/images/{task_id}?index={i}")
            else:
                images.append(f"{BASE_URL}/api/images/{task_id}")

            return {
                "status": "success",
                "message": "图片生成完成",
                "task_id": task_id,
                "images": images,
                "generation_time": f"{time.time() - start_time:.1f}s"
            }

        elif status["status"] == "failed":
            return {
                "status": "error",
                "message": status.get("error_message", "生成失败"),
                "task_id": task_id
            }

        elif status["status"] == "cancelled":
            return {
                "status": "cancelled",
                "message": "任务已取消",
                "task_id": task_id
            }

        time.sleep(2)

    return {
        "status": "timeout",
        "message": "生成超时，请稍后查看结果",
        "task_id": task_id
    }


def main():
    parser = argparse.ArgumentParser(description="AI Image Generator CLI")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # text2image 命令
    t2i_parser = subparsers.add_parser("text2image", help="文生图")
    t2i_parser.add_argument("prompt", help="正向提示词")
    t2i_parser.add_argument("--negative", "-n", default="", help="反向提示词")
    t2i_parser.add_argument("--width", "-W", type=int, default=1024, help="宽度")
    t2i_parser.add_argument("--height", "-H", type=int, default=1024, help="高度")
    t2i_parser.add_argument("--steps", "-s", type=int, default=20, help="迭代步数")
    t2i_parser.add_argument("--cfg", "-c", type=float, default=4.5, help="CFG Scale")
    t2i_parser.add_argument("--seed", type=int, default=0, help="随机种子")
    t2i_parser.add_argument("--num", type=int, default=1, help="生成数量")
    t2i_parser.add_argument("--no-wait", action="store_true", help="不等待完成")

    # image2image 命令
    i2i_parser = subparsers.add_parser("image2image", help="图生图")
    i2i_parser.add_argument("prompt", help="正向提示词")
    i2i_parser.add_argument("image", help="参考图片路径")
    i2i_parser.add_argument("--negative", "-n", default="", help="反向提示词")
    i2i_parser.add_argument("--steps", "-s", type=int, default=50, help="迭代步数")
    i2i_parser.add_argument("--cfg", "-c", type=float, default=4.5, help="CFG Scale")
    i2i_parser.add_argument("--seed", type=int, default=0, help="随机种子")
    i2i_parser.add_argument("--num", type=int, default=1, help="生成数量")
    i2i_parser.add_argument("--no-wait", action="store_true", help="不等待完成")

    # status 命令
    status_parser = subparsers.add_parser("status", help="查询任务状态")
    status_parser.add_argument("task_id", help="任务ID")

    # cancel 命令
    cancel_parser = subparsers.add_parser("cancel", help="取消任务")
    cancel_parser.add_argument("task_id", help="任务ID")

    # queue 命令
    subparsers.add_parser("queue", help="查询队列状态")

    args = parser.parse_args()

    if args.command == "text2image":
        result = text2image(
            prompt=args.prompt,
            negative_prompt=args.negative,
            width=args.width,
            height=args.height,
            steps=args.steps,
            guidance_scale=args.cfg,
            seed=args.seed,
            num_images=args.num,
            wait=not args.no_wait
        )
    elif args.command == "image2image":
        result = image2image(
            prompt=args.prompt,
            image_path=args.image,
            negative_prompt=args.negative,
            steps=args.steps,
            guidance_scale=args.cfg,
            seed=args.seed,
            num_images=args.num,
            wait=not args.no_wait
        )
    elif args.command == "status":
        result = get_task_status(args.task_id)
    elif args.command == "cancel":
        result = cancel_task(args.task_id)
    elif args.command == "queue":
        result = get_queue_status()
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
