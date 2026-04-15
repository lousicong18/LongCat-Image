import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 文生图请求
export interface Text2ImageRequest {
  prompt: string;
  negative_prompt?: string;
  width?: number;
  height?: number;
  steps?: number;
  guidance_scale?: number;
  seed?: number;
  num_images?: number;
}

// 图生图请求
export interface Image2ImageRequest {
  prompt: string;
  negative_prompt?: string;
  steps?: number;
  guidance_scale?: number;
  seed?: number;
  num_images?: number;
  image: File;
}

// 任务响应
export interface TaskResponse {
  success: boolean;
  task_id: string;
  status: string;
  message: string;
}

// 任务状态
export interface TaskStatus {
  id: string;
  type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  result_url: string | null;
  result_urls?: string[];
  error_message: string | null;
  progress: number;
}

// 队列状态
export interface QueueStatus {
  max_size: number;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  available_slots: number;
}

// API 方法
export const apiClient = {
  // 文生图
  async createText2ImageTask(data: Text2ImageRequest): Promise<TaskResponse> {
    const response = await api.post('/text2image', data);
    return response.data;
  },

  // 图生图
  async createImage2ImageTask(data: Image2ImageRequest): Promise<TaskResponse> {
    const formData = new FormData();
    formData.append('prompt', data.prompt);
    if (data.negative_prompt) formData.append('negative_prompt', data.negative_prompt);
    if (data.steps) formData.append('steps', data.steps.toString());
    if (data.guidance_scale) formData.append('guidance_scale', data.guidance_scale.toString());
    if (data.seed !== undefined) formData.append('seed', data.seed.toString());
    if (data.num_images) formData.append('num_images', data.num_images.toString());
    formData.append('image', data.image);

    const response = await api.post('/image2image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  // 获取任务状态
  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await api.get(`/tasks/${taskId}`);
    return response.data;
  },

  // 获取队列状态
  async getQueueStatus(): Promise<QueueStatus> {
    const response = await api.get('/queue/status');
    return response.data;
  },

  // 获取最近任务列表
  async getRecentTasks(limit: number = 20): Promise<TaskStatus[]> {
    const response = await api.get('/tasks', { params: { limit } });
    return response.data;
  },

  // 取消任务
  async cancelTask(taskId: string): Promise<{ success: boolean; message: string }> {
    const response = await api.post(`/tasks/${taskId}/cancel`);
    return response.data;
  },

  // 获取图片 URL
  getImageUrl(taskId: string, index: number = 0): string {
    return `${API_BASE_URL}/api/images/${taskId}?index=${index}`;
  },

  // 创建 WebSocket 连接
  createWebSocket(): WebSocket {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = import.meta.env.VITE_WS_URL || `${wsProtocol}//${window.location.host}`;
    return new WebSocket(`${wsHost}/ws`);
  },
};

export default apiClient;
