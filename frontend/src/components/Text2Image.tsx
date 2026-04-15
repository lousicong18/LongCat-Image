import { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Form,
  Input,
  Slider,
  InputNumber,
  Button,
  Progress,
  Alert,
  Row,
  Col,
  Space,
  Typography,
  Image,
  message,
} from 'antd';
import { PictureOutlined, ReloadOutlined, RocketOutlined, StopOutlined } from '@ant-design/icons';
import { apiClient, type TaskStatus } from '../api/client';

const { TextArea } = Input;
const { Text, Title } = Typography;

interface Text2ImageProps {
  onTaskSubmitted?: (taskId: string) => void;
}

const Text2Image: React.FC<Text2ImageProps> = ({ onTaskSubmitted }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [progress, setProgress] = useState(0);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [resultUrls, setResultUrls] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);

  // 监听任务进度（轮询 + WebSocket 备用）
  useEffect(() => {
    if (!taskId) return;

    let ws: WebSocket | null = null;
    let pollInterval: ReturnType<typeof setInterval> | null = null;
    let isCompleted = false;
    let errorCount = 0;
    const MAX_ERRORS = 3;

    const connectWebSocket = () => {
      try {
        ws = apiClient.createWebSocket();

        ws.onopen = () => {
          // 订阅任务更新
          ws?.send(JSON.stringify({ type: 'subscribe', task_id: taskId }));
        };

        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);

          if (data.type === 'progress' && data.task_id === taskId) {
            setProgress(data.progress);
          }

          if (data.type === 'completed' && data.task_id === taskId) {
            isCompleted = true;
            setProgress(100);
            fetchTaskStatus();
            if (pollInterval) clearInterval(pollInterval);
          }

          if (data.type === 'failed' && data.task_id === taskId) {
            isCompleted = true;
            setError(data.error || '生成失败');
            setLoading(false);
            if (pollInterval) clearInterval(pollInterval);
          }
        };

        ws.onerror = () => {
          // WebSocket 失败时依赖轮询
        };

        ws.onclose = () => {
          // 如果任务未完成，尝试重新连接
          if (!isCompleted) {
            setTimeout(connectWebSocket, 3000);
          }
        };
      } catch (err) {
        // WebSocket 不支持时使用轮询
      }
    };

    const fetchTaskStatus = async () => {
      try {
        const status = await apiClient.getTaskStatus(taskId);
        setTaskStatus(status);
        setProgress(status.progress);

        if (status.status === 'completed') {
          isCompleted = true;
          // 处理多张图片结果
          if (status.result_urls && status.result_urls.length > 0) {
            const urls = status.result_urls.map((_, index) => apiClient.getImageUrl(taskId, index));
            setResultUrls(urls);
            setResultUrl(urls[0]);
          } else {
            setResultUrl(apiClient.getImageUrl(taskId));
            setResultUrls([]);
          }
          setLoading(false);
          if (pollInterval) clearInterval(pollInterval);
          if (ws) ws.close();
        } else if (status.status === 'failed') {
          isCompleted = true;
          setError(status.error_message || '生成失败');
          setLoading(false);
          if (pollInterval) clearInterval(pollInterval);
          if (ws) ws.close();
        }
        // 重置错误计数
        errorCount = 0;
      } catch (err) {
        console.error('获取任务状态失败:', err);
        errorCount++;
        // 连续错误达到阈值时停止轮询
        if (errorCount >= MAX_ERRORS) {
          isCompleted = true;
          setError('获取任务状态失败，已停止轮询');
          setLoading(false);
          if (pollInterval) clearInterval(pollInterval);
          if (ws) ws.close();
        }
      }
    };

    // 启动 WebSocket 和轮询
    connectWebSocket();
    pollInterval = setInterval(fetchTaskStatus, 2000);
    fetchTaskStatus();

    return () => {
      if (pollInterval) clearInterval(pollInterval);
      if (ws) ws.close();
    };
  }, [taskId]);

  const handleSubmit = useCallback(async (values: any) => {
    setLoading(true);
    setError(null);
    setResultUrl(null);
    setResultUrls([]);
    setProgress(0);
    setTaskStatus(null);

    try {
      const response = await apiClient.createText2ImageTask({
        prompt: values.prompt,
        negative_prompt: values.negative_prompt,
        width: values.width,
        height: values.height,
        steps: values.steps,
        guidance_scale: values.guidance_scale,
        seed: values.seed || 0,
        num_images: values.num_images || 1,
      });

      if (response.success) {
        setTaskId(response.task_id);
        onTaskSubmitted?.(response.task_id);
        message.success('任务已提交到队列');
      } else {
        setError(response.message || '提交失败');
        setLoading(false);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || '提交失败，请重试');
      setLoading(false);
    }
  }, [onTaskSubmitted]);

  const handleReset = () => {
    form.resetFields();
    setTaskId(null);
    setTaskStatus(null);
    setProgress(0);
    setResultUrl(null);
    setResultUrls([]);
    setError(null);
    setLoading(false);
    setIsCancelling(false);
  };

  const handleCancel = async () => {
    if (!taskId) return;

    setIsCancelling(true);
    try {
      await apiClient.cancelTask(taskId);
      message.success('任务已取消');
      setLoading(false);
      setProgress(0);
    } catch (err: any) {
      message.error(err.response?.data?.detail || '取消任务失败');
    } finally {
      setIsCancelling(false);
    }
  };

  // 判断是否显示终止按钮（任务正在等待或处理中）
  const canCancel = !!(taskId &&
    (taskStatus?.status === 'pending' || taskStatus?.status === 'processing'));

  return (
    <Card>
      <Title level={4}>
        <PictureOutlined /> 文生图
      </Title>
      <Text type="secondary">输入文字描述，AI 将为您生成图片</Text>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        style={{ marginTop: 24 }}
        initialValues={{
          width: 1024,
          height: 1024,
          steps: 20,
          guidance_scale: 4.5,
          seed: 0,
          num_images: 1,
        }}
      >
        <Form.Item
          name="prompt"
          label="正向提示词"
          rules={[{ required: true, message: '请输入正向提示词' }]}
        >
          <TextArea
            rows={4}
            placeholder="描述您想要生成的图片，例如：一只可爱的白色小猫，樱花树下，高清治愈"
            disabled={loading}
          />
        </Form.Item>

        <Form.Item name="negative_prompt" label="反向提示词">
          <TextArea
            rows={2}
            placeholder="描述您不想要的内容，例如：模糊,低分辨率,丑,变形"
            disabled={loading}
          />
        </Form.Item>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="width" label="宽度">
              <Slider min={512} max={2048} step={64} disabled={loading} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="height" label="高度">
              <Slider min={512} max={2048} step={64} disabled={loading} />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="迭代步数" name="steps">
              <InputNumber min={1} max={100} style={{ width: '100%' }} disabled={loading} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="CFG Scale" name="guidance_scale">
              <InputNumber
                min={1}
                max={20}
                step={0.1}
                style={{ width: '100%' }}
                disabled={loading}
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item label="随机种子" name="seed">
          <InputNumber
            min={0}
            max={4294967295}
            placeholder="留空或填 0 表示随机"
            style={{ width: '100%' }}
            disabled={loading}
          />
        </Form.Item>

        <Form.Item label="生成数量" name="num_images">
          <InputNumber
            min={1}
            max={4}
            placeholder="1-4 张"
            style={{ width: '100%' }}
            disabled={loading}
          />
        </Form.Item>

        {error && (
          <Alert
            message="错误"
            description={error}
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
            closable
            onClose={() => setError(null)}
          />
        )}

        {taskId && (
          <Card size="small" style={{ marginBottom: 16, background: '#f6ffed' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text strong>任务状态: {taskStatus?.status || 'pending'}</Text>
              <Progress percent={progress} status={progress === 100 ? 'success' : 'active'} />
              {taskId && <Text type="secondary" copyable>任务ID: {taskId}</Text>}
            </Space>
          </Card>
        )}

        {resultUrls.length > 0 && (
          <Card size="small" title={`生成结果 (${resultUrls.length} 张)`} style={{ marginBottom: 16 }}>
            <Image.PreviewGroup>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {resultUrls.map((url, index) => (
                  <Image
                    key={index}
                    src={url}
                    alt={`生成结果 ${index + 1}`}
                    style={{ maxWidth: '200px', maxHeight: '200px', borderRadius: 8, objectFit: 'cover' }}
                    preview
                  />
                ))}
              </div>
            </Image.PreviewGroup>
          </Card>
        )}

        {resultUrl && resultUrls.length === 0 && (
          <Card size="small" title="生成结果" style={{ marginBottom: 16 }}>
            <Image
              src={resultUrl}
              alt="生成结果"
              style={{ maxWidth: '100%', borderRadius: 8 }}
              preview
            />
          </Card>
        )}

        <Form.Item>
          <Space>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              icon={<RocketOutlined />}
              size="large"
              disabled={canCancel}
            >
              {loading ? '生成中...' : '开始生成'}
            </Button>
            {canCancel && (
              <Button
                danger
                onClick={handleCancel}
                loading={isCancelling}
                icon={<StopOutlined />}
                size="large"
              >
                终止任务
              </Button>
            )}
            <Button
              onClick={handleReset}
              icon={<ReloadOutlined />}
              disabled={loading && !canCancel}
            >
              重置
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default Text2Image;
