---
name: ai-image-generator
description: |
  AI图像生成服务，支持文生图和图生图功能。
  
  触发场景：
  - 用户要求生成图片、画图、创作图像
  - 用户要求基于参考图片进行编辑或风格转换
  - 用户询问图片生成相关功能
  
  示例触发：
  - "帮我生成一张小猫的图片"
  - "画一张樱花风景图"
  - "把这张图片变成油画风格"
  - "生成2张不同风格的风景图"

version: 1.0.0
author: AI Image Generator Team
user-invocable: true
triggers:
  - 生成图片
  - 画图
  - 创建图像
  - 文生图
  - 图生图
  - AI绘图
  
metadata:
  openclaw:
    requires:
      bins: [curl]
    config:
      base_url: "http://192.168.20.202:10018"
      api_docs: "http://192.168.20.202:10018/docs"
---

# AI Image Generator - OpenClaw Skill

基于 LongCat 模型的 AI 图像生成服务，支持文生图和图生图。

## 功能说明

| 功能 | 触发词 | 说明 |
|------|--------|------|
| 文生图 | 生成图片、画图、创建图像 | 根据文字描述生成图片 |
| 图生图 | 基于图片编辑、图片风格转换 | 基于参考图片生成新图片 |
| 查询任务 | 查询生成进度 | 查看任务状态 |
| 取消任务 | 取消生成 | 取消正在进行的任务 |

## 服务配置

- **后端地址**: `http://192.168.20.202:10018`
- **API文档**: `http://192.168.20.202:10018/docs`
- **前端页面**: `http://192.168.20.202:5173`

**注意**: 调用前请确保 ComfyUI 服务运行在 `http://127.0.0.1:8188`

---

## 执行步骤

### 1. 文生图 (text2image)

当用户要求生成图片时：

**API 调用**:
```bash
POST {base_url}/api/text2image
Content-Type: application/json

{
  "prompt": "<用户描述的内容>",
  "negative_prompt": "<不想要的内容，可选>",
  "width": 1024,
  "height": 1024,
  "steps": 20,
  "guidance_scale": 4.5,
  "seed": 0,
  "num_images": 1
}
```

**参数说明**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| prompt | string | ✅ | - | 正向提示词，描述想要生成的图片 |
| negative_prompt | string | | "" | 反向提示词，描述不想要的内容 |
| width | integer | | 1024 | 图片宽度 (512-2048) |
| height | integer | | 1024 | 图片高度 (512-2048) |
| steps | integer | | 20 | 迭代步数 (1-100)，越高越精细 |
| guidance_scale | number | | 4.5 | CFG Scale (1.0-20.0) |
| seed | integer | | 0 | 随机种子，0表示随机 |
| num_images | integer | | 1 | 生成数量 (1-4张) |

**响应示例**:
```json
{
  "success": true,
  "task_id": "abc-123-def",
  "status": "pending",
  "message": "任务已提交到队列"
}
```

---

### 2. 图生图 (image2image)

当用户上传图片并要求编辑时：

**API 调用**:
```bash
POST {base_url}/api/image2image
Content-Type: multipart/form-data

参数:
- prompt: string (必填) - 描述想要的效果
- image: file (必填) - 参考图片文件
- negative_prompt: string - 反向提示词
- steps: integer (默认50) - 迭代步数
- guidance_scale: number (默认4.5)
- seed: integer (默认0)
- num_images: integer (默认1)
```

---

### 3. 查询任务状态

提交任务后，轮询查询状态：

**API 调用**:
```bash
GET {base_url}/api/tasks/{task_id}
```

**响应**:
```json
{
  "id": "abc-123-def",
  "type": "text2image",
  "status": "completed",
  "progress": 100,
  "result_url": "/api/images/abc-123-def",
  "result_urls": ["/api/images/abc-123-def?index=0", "/api/images/abc-123-def?index=1"],
  "error_message": null
}
```

**状态说明**:
- `pending`: 等待中
- `processing`: 处理中
- `completed`: 已完成
- `failed`: 失败
- `cancelled`: 已取消

---

### 4. 获取生成的图片

任务完成后获取图片：

```bash
GET {base_url}/api/images/{task_id}?index=0
```

- `index`: 图片索引，生成多张时使用（从0开始）

---

### 5. 取消任务

```bash
POST {base_url}/api/tasks/{task_id}/cancel
```

---

### 6. 查询队列状态

```bash
GET {base_url}/api/queue/status
```

**响应**:
```json
{
  "max_size": 10,
  "pending": 1,
  "processing": 1,
  "completed": 5,
  "failed": 0,
  "available_slots": 8
}
```

---

## 完整工作流

### 文生图工作流

1. **提交任务**: 调用 `POST /api/text2image` 获取 `task_id`
2. **轮询状态**: 每2秒调用 `GET /api/tasks/{task_id}` 直到 `status` 为 `completed` 或 `failed`
3. **获取图片**: 调用 `GET /api/images/{task_id}` 返回图片 URL
4. **返回结果**: 告诉用户图片已生成，提供图片链接

### 图生图工作流

1. **上传图片**: 用户上传参考图片
2. **提交任务**: 调用 `POST /api/image2image` (multipart/form-data)
3. **轮询状态**: 同上
4. **返回结果**: 同上

---

## 使用示例

**示例 1: 简单文生图**
```
用户: 帮我生成一张可爱的小猫图片

步骤:
1. POST /api/text2image {"prompt": "一只可爱的小猫"}
2. 轮询任务状态
3. 返回: 图片已生成，链接: http://192.168.20.202:10018/api/images/xxx
```

**示例 2: 指定参数**
```
用户: 帮我生成2张 1024x768 的樱花风景图

步骤:
POST /api/text2image {
  "prompt": "美丽的樱花风景",
  "width": 1024,
  "height": 768,
  "num_images": 2
}
```

**示例 3: 图生图**
```
用户: [上传图片] 把这张图片变成油画风格

步骤:
POST /api/image2image {
  "prompt": "oil painting style",
  "image": <上传的图片>
}
```

---

## 输入参数

由 AI 从用户对话中提取：

- **prompt**: 从用户描述中提取想要生成的内容
- **width/height**: 用户指定尺寸，或根据描述推断（风景用宽屏，人像用方形等）
- **num_images**: 用户指定数量，默认1张
- **negative_prompt**: 用户提到"不要xxx"时提取
- **image**: 用户上传的图片（图生图时）

---

## 输出格式

```json
{
  "status": "success",
  "message": "图片已生成完成",
  "task_id": "abc-123-def",
  "images": [
    {
      "url": "http://192.168.20.202:10018/api/images/abc-123-def?index=0",
      "index": 0
    }
  ],
  "generation_time": "15.3s"
}
```

---

## 错误处理

| 错误 | 原因 | 处理方式 |
|------|------|---------|
| 503 队列已满 | 任务排队超过10个 | 告诉用户稍后重试 |
| 400 参数错误 | 参数格式不对 | 检查并修正参数 |
| 500 服务错误 | ComfyUI 未启动 | 提示管理员检查服务 |
| 超时 | 生成超过10分钟 | 建议用户减少 steps 或图片尺寸 |

---

## 注意事项

1. **ComfyUI 必须运行**: 确保服务在 `http://127.0.0.1:8188`
2. **生成时间**: 每张图片约10-60秒，取决于参数
3. **队列限制**: 最多10个任务排队
4. **图片限制**: 上传图片最大10MB
5. **格式支持**: 支持 JPG、PNG 格式
