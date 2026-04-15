import { useState, useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import { Card, Badge, Space, Typography, List, Tag, Button } from 'antd';
import { LoadingOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined, UnorderedListOutlined, ReloadOutlined } from '@ant-design/icons';
import { apiClient, type QueueStatus as QueueStatusType, type TaskStatus } from '../api/client';

const { Text, Title } = Typography;

export interface QueueStatusRef {
  startPolling: () => void;
}

const QueueStatus = forwardRef<QueueStatusRef>((_, ref) => {
  const [queueStatus, setQueueStatus] = useState<QueueStatusType | null>(null);
  const [recentTasks, setRecentTasks] = useState<TaskStatus[]>([]);
  const [loading, setLoading] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = async () => {
    setLoading(true);

    // 分别处理每个请求，避免一个失败影响另一个
    try {
      const status = await apiClient.getQueueStatus();
      setQueueStatus(status);

      // 如果没有活跃任务，停止轮询
      if (status.pending === 0 && status.processing === 0 && intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    } catch (e) {
      console.error('获取队列状态失败:', e);
    }

    try {
      const tasks = await apiClient.getRecentTasks(10);
      setRecentTasks(tasks);
    } catch (e) {
      console.error('获取任务列表失败:', e);
    }

    setLoading(false);
  };

  // 开始轮询
  const startPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    fetchData(); // 立即获取一次
    intervalRef.current = setInterval(fetchData, 5000);
  };

  // 暴露 startPolling 方法给父组件
  useImperativeHandle(ref, () => ({
    startPolling,
  }));

  useEffect(() => {
    // 初始加载一次
    fetchData();

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
      case 'processing':
        return <LoadingOutlined style={{ color: '#1890ff' }} />;
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'warning';
      case 'processing':
        return 'processing';
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending':
        return '等待中';
      case 'processing':
        return '处理中';
      case 'completed':
        return '已完成';
      case 'failed':
        return '失败';
      default:
        return status;
    }
  };

  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <UnorderedListOutlined /> 队列状态
        </Title>
        <Button
          icon={<ReloadOutlined />}
          loading={loading}
          onClick={startPolling}
          size="small"
        >
          刷新
        </Button>
      </div>

      {queueStatus && (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space wrap>
            <Badge count={queueStatus.pending} showZero color="#faad14">
              <Card size="small" style={{ width: 100, textAlign: 'center' }}>
                <Text type="secondary">等待中</Text>
              </Card>
            </Badge>
            <Badge count={queueStatus.processing} showZero color="#1890ff">
              <Card size="small" style={{ width: 100, textAlign: 'center' }}>
                <Text type="secondary">处理中</Text>
              </Card>
            </Badge>
            <Badge count={queueStatus.completed} showZero color="#52c41a">
              <Card size="small" style={{ width: 100, textAlign: 'center' }}>
                <Text type="secondary">已完成</Text>
              </Card>
            </Badge>
            <Badge count={queueStatus.failed} showZero color="#ff4d4f">
              <Card size="small" style={{ width: 100, textAlign: 'center' }}>
                <Text type="secondary">失败</Text>
              </Card>
            </Badge>
          </Space>

          <Card size="small" style={{ background: '#f6ffed' }}>
            <Space>
              <Text strong>可用槽位:</Text>
              <Text type="success">{queueStatus.available_slots} / {queueStatus.max_size}</Text>
            </Space>
          </Card>

          <Title level={5} style={{ marginTop: 16 }}>最近任务</Title>
          <List
            size="small"
            dataSource={recentTasks}
            locale={{ emptyText: '暂无任务' }}
            renderItem={(task) => (
              <List.Item
                actions={[
                  <Tag color={getStatusColor(task.status)}>
                    {getStatusIcon(task.status)} {getStatusText(task.status)}
                  </Tag>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong>{task.type === 'text2image' ? '文生图' : '图生图'}</Text>
                      <Text type="secondary" copyable style={{ fontSize: 12 }}>
                        {task.id.slice(0, 8)}...
                      </Text>
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size={0}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        创建时间: {new Date(task.created_at).toLocaleString()}
                      </Text>
                      {task.progress > 0 && task.progress < 100 && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          进度: {task.progress}%
                        </Text>
                      )}
                      {task.error_message && (
                        <Text type="danger" style={{ fontSize: 12 }}>
                          错误: {task.error_message}
                        </Text>
                      )}
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Space>
      )}
    </Card>
  );
});

export default QueueStatus;
