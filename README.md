# AI Image Generator

基于 LongCat 模型的 AI 图像生成服务，支持文生图和图生图功能。

## 功能特性

- ✅ 文生图 (Text to Image)
- ✅ 图生图 (Image to Image)
- ✅ 批量生成 (1-4张)
- ✅ 任务队列管理
- ✅ WebSocket 实时进度
- ✅ 任务取消功能
- ✅ React + Ant Design 前端界面

## 技术栈

**后端:**
- Python 3.10+
- FastAPI
- WebSocket
- aiohttp

**前端:**
- React 18
- TypeScript
- Ant Design 5
- Vite

## 快速开始

### 1. 启动 ComfyUI

确保 ComfyUI 运行在 `http://127.0.0.1:8188`

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 10018 --reload
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 4. 访问页面

- 前端: http://localhost:5173
- 后端 API: http://localhost:10018
- API 文档: http://localhost:10018/docs

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/text2image | 文生图 |
| POST | /api/image2image | 图生图 |
| GET | /api/tasks/{task_id} | 获取任务状态 |
| POST | /api/tasks/{task_id}/cancel | 取消任务 |
| GET | /api/queue/status | 获取队列状态 |
| GET | /api/tasks | 获取最近任务列表 |
| GET | /api/images/{task_id} | 获取生成的图片 |
| WS | /ws | WebSocket 实时进度 |

## 项目结构

```
ai-image-generator/
├── backend/                 # FastAPI 后端
│   ├── main.py             # 主应用
│   ├── config.py           # 配置管理
│   ├── queue_manager.py    # 任务队列
│   ├── comfyui_client.py   # ComfyUI 客户端
│   └── requirements.txt    # Python 依赖
│
├── frontend/               # React 前端
│   ├── src/
│   │   ├── App.tsx        # 主应用
│   │   ├── api/client.ts  # API 客户端
│   │   └── components/    # 组件
│   ├── package.json
│   └── vite.config.ts
│
└── openclaw-skill/         # OpenClaw Skill 配置
    └── ai-image-generator/
        └── SKILL.md
```

## 配置说明

修改 `backend/.env` 文件:

```env
COMFYUI_URL=http://127.0.0.1:8188
HOST=0.0.0.0
PORT=10018
MAX_QUEUE_SIZE=10
OUTPUT_DIR=./outputs
```

## 许可证

MIT License
