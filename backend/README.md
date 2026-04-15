# AI 图像生成器项目

## 📋 项目概述

这是一个基于 **ComfyUI + LongCat 模型**的AI图像生成应用，采用前后端分离架构：

- **后端**: FastAPI (Python)
- **前端**: React + TypeScript + Vite
- **AI引擎**: ComfyUI (需要单独运行)

---

## 🚀 启动方式

### 1️⃣ 启动后端服务

```bash
# 进入后端目录
cd backend

# 激活虚拟环境（如果使用.venv）
.venv\Scripts\activate

# 安装依赖（首次运行）
pip install -r requirements.txt

# 配置环境变量（可选，复制.env.example为.env）
copy .env.example .env

# 启动后端服务
python main.py
```

**后端端口**: `10018` (默认，可在 config.py 中修改)

### 2️⃣ 启动前端服务

```bash
# 进入前端目录
cd frontend

# 安装依赖（首次运行）
npm install

# 启动开发服务器
npm run dev
```

**前端端口**: `5173` (Vite默认端口)

### 3️⃣ 启动 ComfyUI (必需)

```bash
# 需要单独启动ComfyUI服务
# 默认地址: http://127.0.0.1:8188
```

**ComfyUI端口**: `8188`

---

## ✨ 主要功能

### 🎨 文生图 (Text2Image)
- **API**: `POST /api/text2image`
- **功能**: 根据文本提示生成图片
- **参数**:
  - `prompt`: 正向提示词
  - `negative_prompt`: 反向提示词
  - `width/height`: 图片尺寸 (512-2048)
  - `steps`: 迭代步数 (1-100)
  - `guidance_scale`: CFG Scale (1.0-20.0)
  - `seed`: 随机种子 (0表示随机)
  - `num_images`: 一次生成1-4张图片

### 🖼️ 图生图 (Image2Image)
- **API**: `POST /api/image2image`
- **功能**: 根据上传的图片和提示词生成新图片
- **参数**: 类似文生图，支持上传参考图片

### 📊 队列管理
- **查看队列状态**: `GET /api/queue/status`
- **查看任务详情**: `GET /api/tasks/{task_id}`
- **查看最近任务**: `GET /api/tasks?limit=20`
- **取消任务**: `POST /api/tasks/{task_id}/cancel`
- **获取生成的图片**: `GET /api/images/{task_id}`

### 🔌 WebSocket 实时通信
- **端点**: `/ws`
- **功能**: 实时接收任务进度更新
- **事件类型**: `progress`, `completed`, `failed`, `cancelled`

---

## 📁 项目结构

```
ai-image-generator/
├── backend/                    # 后端服务
│   ├── main.py                # FastAPI主程序
│   ├── config.py              # 配置管理
│   ├── comfyui_client.py      # ComfyUI客户端
│   ├── queue_manager.py       # 队列管理器
│   ├── requirements.txt       # Python依赖
│   ├── .env.example          # 环境变量示例
│   └── outputs/               # 生成的图片存储
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── components/        # React组件
│   │   │   ├── Text2Image.tsx
│   │   │   ├── Image2Image.tsx
│   │   │   └── QueueStatus.tsx
│   │   ├── api/               # API客户端
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
```

---

## 🔧 环境配置

在 `backend/.env` 中配置：

```env
COMFYUI_URL=http://127.0.0.1:8188  # ComfyUI服务地址
HOST=0.0.0.0                        # 后端监听地址
PORT=10018                           # 后端端口
MAX_QUEUE_SIZE=10                   # 最大队列大小
OUTPUT_DIR=./outputs                # 输出目录
```

---

## 📝 使用流程

1. 启动 ComfyUI 服务 (端口8188)
2. 启动后端服务 (端口10018)
3. 启动前端服务 (端口5173)
4. 在浏览器访问 `http://localhost:5173`
5. 选择"文生图"或"图生图"功能
6. 输入提示词和参数，提交任务
7. 通过WebSocket实时查看生成进度
8. 下载生成的图片

---

## 🎯 技术特点

- ✅ 异步队列处理，支持并发任务
- ✅ WebSocket实时进度推送
- ✅ 支持批量生成多张图片
- ✅ 任务取消功能
- ✅ CORS跨域支持
- ✅ 图片大小限制 (10MB)
- ✅ 健康检查端点 `/health`

---

## 📅 更新日志

- **2026-04-15**: 项目初始化
- **功能**: 文生图、图生图、队列管理、WebSocket实时通信
