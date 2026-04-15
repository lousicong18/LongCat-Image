import { useState, useRef } from 'react';
import { Layout, Tabs, Typography, Space, Alert } from 'antd';
import {
  PictureOutlined,
  EditOutlined,
  DesktopOutlined,
} from '@ant-design/icons';
import Text2Image from './components/Text2Image';
import Image2Image from './components/Image2Image';
import QueueStatus from './components/QueueStatus';

const { Header, Content, Sider } = Layout;
const { Title, Text } = Typography;

function App() {
  const [activeTab, setActiveTab] = useState('text2image');
  const [lastTaskId, setLastTaskId] = useState<string | null>(null);
  const queueStatusRef = useRef<{ startPolling: () => void } | null>(null);

  const handleTaskSubmitted = (taskId: string) => {
    setLastTaskId(taskId);
    // 提交新任务时开始轮询
    queueStatusRef.current?.startPolling();
  };

  const items = [
    {
      key: 'text2image',
      label: (
        <Space>
          <PictureOutlined />
          文生图
        </Space>
      ),
      children: <Text2Image onTaskSubmitted={handleTaskSubmitted} />,
    },
    {
      key: 'image2image',
      label: (
        <Space>
          <EditOutlined />
          图生图
        </Space>
      ),
      children: <Image2Image onTaskSubmitted={handleTaskSubmitted} />,
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
        <Space align="center" style={{ height: '100%' }}>
          <DesktopOutlined style={{ fontSize: 24, color: '#1890ff' }} />
          <Title level={3} style={{ margin: 0, color: '#1890ff' }}>
            AI 图像生成器
          </Title>
          <Text type="secondary">基于 LongCat 模型</Text>
        </Space>
      </Header>

      <Layout>
        <Content style={{ padding: 24, background: '#f5f5f5' }}>
          <Alert
            message="使用说明"
            description="请确保 ComfyUI 服务已启动并运行在 http://127.0.0.1:8188。队列最大容量为 10 个任务，超出后新任务将被拒绝。"
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
          />

          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={items}
            type="card"
            size="large"
          />

          {lastTaskId && (
            <Alert
              message="任务已提交"
              description={`任务 ID: ${lastTaskId}，您可以在右侧队列状态中查看进度`}
              type="success"
              showIcon
              closable
              style={{ marginTop: 24 }}
              onClose={() => setLastTaskId(null)}
            />
          )}
        </Content>

        <Sider
          width={350}
          style={{
            background: '#fff',
            padding: 24,
            boxShadow: '-2px 0 8px rgba(0,0,0,0.05)',
          }}
        >
          <QueueStatus ref={queueStatusRef} />
        </Sider>
      </Layout>
    </Layout>
  );
}

export default App;
