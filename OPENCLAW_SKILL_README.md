# AI Image Generator - OpenClaw Skill

## 概述

此 Skill 允许 OpenClaw 调用 AI 图像生成服务，支持文生图和图生图功能。

## 配置

在 OpenClaw 中导入 `openclaw-skill.json` 文件，或手动配置：

```json
{
  "name": "ai-image-generator",
  "base_url": "http://192.168.20.202:10018"
}
```

## 可用技能

### 1. text2image - 文生图

根据文字描述生成图片。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| prompt | string | ✅ | - | 正向提示词 |
| negative_prompt | string | | "" | 反向提示词 |
| width | integer | | 1024 | 图片宽度 (512-2048) |
| height | integer | | 1024 | 图片高度 (512-2048) |
| steps | integer | | 20 | 迭代步数 (1-100) |
| guidance_scale | number | | 4.5 | CFG Scale (1.0-20.0) |
| seed | integer | | 0 | 随机种子 (0=随机) |
| num_images | integer | | 1 | 生成数量 (1-4) |

**示例：**

```json
{
  "prompt": "一只可爱的白色小猫，樱花树下，高清治愈",
  "width": 1024,
  "height": 1024,
  "num_images": 2
}
```

**响应：**

```json
{
  "success": true,
  "task_id": "xxx-xxx-xxx",
  "status": "pending",
  "message": "任务已提交到队列"
}
```

---

### 2. image2image - 图生图

基于参考图片生成新图片。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| prompt | string | ✅ | - | 正向提示词 |
| image | file | ✅ | - | 参考图片 |
| negative_prompt | string | | "" | 反向提示词 |
| steps | integer | | 50 | 迭代步数 |
| guidance_scale | number | | 4.5 | CFG Scale |
| seed | integer | | 0 | 随机种子 |
| num_images | integer | | 1 | 生成数量 |

---

### 3. get_task_status - 获取任务状态

查询任务进度和结果。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | ✅ | 任务 ID |

**响应：**

```json
{
  "id": "xxx-xxx-xxx",
  "status": "completed",
  "progress": 100,
  "result_url": "/api/images/xxx-xxx-xxx",
  "result_urls": ["/api/images/xxx-xxx-xxx?index=0", "/api/images/xxx-xxx-xxx?index=1"]
}
```

---

### 4. cancel_task - 取消任务

取消等待中或处理中的任务。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | ✅ | 任务 ID |

---

### 5. get_queue_status - 获取队列状态

**响应：**

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

### 6. get_image - 获取图片

下载生成的图片。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| task_id | string | ✅ | - | 任务 ID |
| index | integer | | 0 | 图片索引 |

---

## 使用示例

### 示例 1：生成单张图片

```
用户：帮我生成一张可爱的小猫图片

OpenClaw 调用：
1. text2image({"prompt": "一只可爱的小猫"})
2. 获取 task_id: "abc-123"
3. 轮询 get_task_status({"task_id": "abc-123"})
4. 返回图片 URL
```

### 示例 2：生成多张图片

```
用户：帮我生成 4 张樱花风景图

OpenClaw 调用：
text2image({
  "prompt": "美丽的樱花风景",
  "num_images": 4
})
```

### 示例 3：图生图

```
用户：把这张图片变成油画风格

OpenClaw 调用：
image2image({
  "prompt": "oil painting style",
  "image": [用户上传的图片]
})
```

---

## WebSocket 实时进度

连接 `ws://192.168.20.202:10018/ws` 可获取实时进度推送。

**消息格式：**

```json
// 进度更新
{"type": "progress", "task_id": "xxx", "progress": 50}

// 任务完成
{"type": "completed", "task_id": "xxx", "result_url": "/api/images/xxx"}

// 任务失败
{"type": "failed", "task_id": "xxx", "error": "错误信息"}

// 任务取消
{"type": "cancelled", "task_id": "xxx"}
```

---

## 注意事项

1. **ComfyUI 必须运行**：确保 ComfyUI 服务运行在 `http://127.0.0.1:8188`
2. **队列限制**：最大 10 个任务排队，超出会返回 503 错误
3. **图片大小限制**：上传图片最大 10MB
4. **生成时间**：每张图片约需 10-60 秒，取决于参数设置

---

## API 文档

完整 API 文档请访问：http://192.168.20.202:10018/docs
