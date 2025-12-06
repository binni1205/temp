import React, { useState } from 'react';
import {
    Input, Button, Card, Typography, Space, List, message,
    Steps, Spin, Result, Modal
} from 'antd';
import {
    SearchOutlined, CheckCircleOutlined, EditOutlined,
    FileTextOutlined, ReloadOutlined, DownloadOutlined
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';

const { TextArea } = Input;
const { Title, Paragraph, Text } = Typography;

// API基础地址
const API_BASE = 'http://118.195.205.71:45855/api/research';

interface Section {
    name: string;
    description: string;
    research: boolean;
    content: string;
}

interface ResearchSession {
    sessionId: string;
    status: 'idle' | 'planning' | 'reviewing' | 'generating' | 'completed';
    sections: Section[];
    finalReport: string;
}

const DeepResearch: React.FC = () => {
    const [topic, setTopic] = useState<string>('');
    const [loading, setLoading] = useState<boolean>(false);
    const [session, setSession] = useState<ResearchSession>({
        sessionId: '',
        status: 'idle',
        sections: [],
        finalReport: ''
    });
    const [feedback, setFeedback] = useState<string>('');
    const [feedbackModalVisible, setFeedbackModalVisible] = useState<boolean>(false);

    // 获取当前步骤
    const getCurrentStep = () => {
        switch (session.status) {
            case 'idle': return 0;
            case 'planning': return 1;
            case 'reviewing': return 1;
            case 'generating': return 2;
            case 'completed': return 3;
            default: return 0;
        }
    };

    // 返回到输入主题步骤
    const goToInputStep = () => {
        if (session.sessionId) {
            fetch(`${API_BASE}/session/${session.sessionId}`, { method: 'DELETE' }).catch(() => { });
        }
        setSession({
            sessionId: '',
            status: 'idle',
            sections: [],
            finalReport: ''
        });
    };

    // 返回到审核计划步骤
    const goToReviewStep = () => {
        if (session.sections.length > 0) {
            setSession(prev => ({
                ...prev,
                status: 'reviewing',
                finalReport: ''
            }));
        }
    };

    // 点击步骤条
    const handleStepClick = (step: number) => {
        if (loading) return;

        const currentStep = getCurrentStep();
        if (step >= currentStep) return;

        switch (step) {
            case 0:
                goToInputStep();
                break;
            case 1:
                if (session.sections.length > 0) {
                    goToReviewStep();
                }
                break;
            default:
                break;
        }
    };

    // 开始研究
    const handleStartResearch = async () => {
        if (!topic.trim()) {
            message.warning('请输入研究主题');
            return;
        }

        setLoading(true);
        setSession(prev => ({ ...prev, status: 'planning' }));

        try {
            const response = await fetch(`${API_BASE}/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic })
            });

            if (!response.ok) throw new Error('请求失败');

            const data = await response.json();
            setSession({
                sessionId: data.session_id,
                status: 'reviewing',
                sections: data.sections,
                finalReport: ''
            });
            message.success('报告计划已生成，请审核');
        } catch (error) {
            message.error('生成报告计划失败，请重试');
            setSession(prev => ({ ...prev, status: 'idle' }));
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    // 批准计划
    const handleApprove = async () => {
        setLoading(true);
        setSession(prev => ({ ...prev, status: 'generating' }));

        try {
            const response = await fetch(`${API_BASE}/feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: session.sessionId,
                    feedback: 'true'
                })
            });

            if (!response.ok) throw new Error('请求失败');

            const data = await response.json();

            if (data.status === 'completed') {
                const reportResponse = await fetch(`${API_BASE}/report/${session.sessionId}`);
                const reportData = await reportResponse.json();

                setSession(prev => ({
                    ...prev,
                    status: 'completed',
                    finalReport: reportData.final_report
                }));
                message.success('研究报告生成完成！');
            }
        } catch (error) {
            message.error('生成报告失败，请重试');
            setSession(prev => ({ ...prev, status: 'reviewing' }));
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    // 提交修改反馈
    const handleSubmitFeedback = async () => {
        if (!feedback.trim()) {
            message.warning('请输入修改建议');
            return;
        }

        setLoading(true);
        setFeedbackModalVisible(false);

        try {
            const response = await fetch(`${API_BASE}/feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: session.sessionId,
                    feedback: feedback
                })
            });

            if (!response.ok) throw new Error('请求失败');

            const data = await response.json();
            setSession(prev => ({
                ...prev,
                sections: data.sections,
                status: 'reviewing'
            }));
            setFeedback('');
            message.success('报告计划已更新');
        } catch (error) {
            message.error('提交反馈失败，请重试');
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    // 重新开始
    const handleReset = () => {
        if (session.sessionId) {
            fetch(`${API_BASE}/session/${session.sessionId}`, { method: 'DELETE' }).catch(() => { });
        }
        setSession({
            sessionId: '',
            status: 'idle',
            sections: [],
            finalReport: ''
        });
        setTopic('');
        setFeedback('');
    };

    // 下载报告
    const handleDownload = () => {
        const blob = new Blob([session.finalReport], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `research_report_${new Date().toISOString().slice(0, 10)}.md`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const currentStep = getCurrentStep();

    return (
        <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
            {/* 标题 */}
            <div style={{ textAlign: 'center', marginBottom: '30px' }}>
                <Title level={2}>🔬 深度研究</Title>
                <Paragraph>
                    AI驱动的法律主题深度研究，自动搜索网络并生成专业研究报告
                </Paragraph>
            </div>

            {/* 进度条 - 点击可返回 */}
            <Steps
                current={currentStep}
                style={{ marginBottom: '30px' }}
                onChange={handleStepClick}
                items={[
                    {
                        title: '输入主题',
                        icon: <SearchOutlined />,
                        style: { cursor: currentStep > 0 && !loading ? 'pointer' : 'default' }
                    },
                    {
                        title: '审核计划',
                        icon: <EditOutlined />,
                        style: { cursor: currentStep > 1 && !loading ? 'pointer' : 'default' }
                    },
                    {
                        title: '生成报告',
                        icon: <FileTextOutlined />
                    },
                    {
                        title: '完成',
                        icon: <CheckCircleOutlined />
                    }
                ]}
            />

            {/* 提示文字 */}
            {currentStep > 0 && !loading && (
                <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                    <Text type="secondary">点击上方步骤条可返回之前的步骤</Text>
                </div>
            )}

            {/* 主题输入 */}
            {session.status === 'idle' && (
                <Card bordered={false}>
                    <Space direction="vertical" size="large" style={{ width: '100%' }}>
                        <Input
                            size="large"
                            placeholder="请输入法律研究主题，例如：网络隐私权保护的法律问题"
                            value={topic}
                            onChange={(e) => setTopic(e.target.value)}
                            onPressEnter={handleStartResearch}
                            prefix={<SearchOutlined />}
                        />
                        <Button
                            type="primary"
                            size="large"
                            block
                            onClick={handleStartResearch}
                            loading={loading}
                        >
                            开始研究
                        </Button>
                    </Space>
                </Card>
            )}

            {/* 生成计划中 */}
            {session.status === 'planning' && (
                <Card bordered={false}>
                    <Result
                        icon={<Spin size="large" />}
                        title="正在生成报告计划..."
                        subTitle="AI正在分析主题并规划报告结构，请稍候"
                    />
                </Card>
            )}

            {/* 报告计划审核 */}
            {session.status === 'reviewing' && (
                <Card
                    title="📋 报告计划"
                    bordered={false}
                    extra={
                        <Space>
                            <Button
                                icon={<EditOutlined />}
                                onClick={() => setFeedbackModalVisible(true)}
                            >
                                修改计划
                            </Button>
                            <Button
                                type="primary"
                                icon={<CheckCircleOutlined />}
                                onClick={handleApprove}
                                loading={loading}
                            >
                                批准并生成
                            </Button>
                        </Space>
                    }
                >
                    <List
                        itemLayout="vertical"
                        dataSource={session.sections}
                        renderItem={(section, index) => (
                            <List.Item>
                                <List.Item.Meta
                                    title={
                                        <span>
                                            <Text strong>{index + 1}. {section.name}</Text>
                                            {section.research && (
                                                <Text type="secondary" style={{ marginLeft: 10 }}>
                                                    (需要网络研究)
                                                </Text>
                                            )}
                                        </span>
                                    }
                                    description={section.description}
                                />
                            </List.Item>
                        )}
                    />
                </Card>
            )}

            {/* 生成中 */}
            {session.status === 'generating' && (
                <Card bordered={false}>
                    <Result
                        icon={<Spin size="large" />}
                        title="正在生成研究报告..."
                        subTitle="AI正在搜索网络并撰写各章节内容，请稍候"
                    />
                </Card>
            )}

            {/* 完成 - 显示报告 */}
            {session.status === 'completed' && (
                <Card
                    title="📄 研究报告"
                    bordered={false}
                    extra={
                        <Space>
                            <Button
                                icon={<DownloadOutlined />}
                                onClick={handleDownload}
                            >
                                下载报告
                            </Button>
                            <Button
                                type="primary"
                                icon={<ReloadOutlined />}
                                onClick={handleReset}
                            >
                                新研究
                            </Button>
                        </Space>
                    }
                >
                    <div style={{
                        background: '#fafafa',
                        padding: '20px',
                        borderRadius: '8px',
                        maxHeight: '600px',
                        overflow: 'auto'
                    }}>
                        <ReactMarkdown>{session.finalReport}</ReactMarkdown>
                    </div>
                </Card>
            )}

            {/* 修改反馈弹窗 */}
            <Modal
                title="修改报告计划"
                open={feedbackModalVisible}
                onOk={handleSubmitFeedback}
                onCancel={() => setFeedbackModalVisible(false)}
                okText="提交修改"
                cancelText="取消"
            >
                <TextArea
                    rows={4}
                    placeholder="请描述您希望如何修改报告计划，例如：增加更多关于案例分析的内容..."
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                />
            </Modal>
        </div>
    );
};

export default DeepResearch;
