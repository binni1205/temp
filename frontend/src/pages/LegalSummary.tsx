import React, { useState } from 'react';
import { Input, Button, Card, Typography, Space, List, message, Dropdown, Menu } from 'antd';
import { SendOutlined, SyncOutlined, DownOutlined } from '@ant-design/icons';

const { TextArea } = Input;
const { Title, Paragraph, Text } = Typography;

interface SummaryItem {
    id: string;
    document: string;
    summary: string;
    timestamp: string;
}

const LegalSummary: React.FC = () => {
    const [document, setDocument] = useState<string>('');
    const [loading, setLoading] = useState<boolean>(false);
    const [summaryResult, setSummaryResult] = useState<string>('');
    const [history, setHistory] = useState<SummaryItem[]>([]);
    const [selectedModel, setSelectedModel] = useState<string>('qwen2.5B');

    // 模拟示例案例
    const exampleCases = [
        { title: '民间借贷纠纷案例', id: 'case1' },
        { title: '知识产权侵权案例', id: 'case2' },
        { title: '劳动合同纠纷案例', id: 'case3' },
        { title: '交通事故责任案例', id: 'case4' }
    ];

    // 可选模型列表
    const models = [
        { key: 'chatglm-6B', label: 'ChatGLM-6B' },
        { key: 'qwen2.5B', label: 'Qwen-2.5B' },
        { key: 'deepseek', label: 'DeepSeek' }
    ];

    const handleModelSelect = (model: string) => {
        setSelectedModel(model);
        message.success(`已选择 ${models.find(m => m.key === model)?.label} 模型`);
    };

    const modelMenu = (
        <Menu
            selectedKeys={[selectedModel]}
            onClick={({ key }) => handleModelSelect(key)}
            items={models.map(model => ({
                key: model.key,
                label: model.label
            }))}
        />
    );

    const handleSubmit = () => {
        if (!document.trim()) {
            message.warning('请输入裁判文书内容');
            return;
        }

        setLoading(true);
        setSummaryResult('');

        // 模拟请求后端API
        setTimeout(() => {
            const summary = `
        【案件摘要】
        本案为一起典型的民间借贷纠纷案件。原告与被告于2021年3月签订借款合同，约定被告向原告借款50万元，期限为6个月，月利率为2%。借款到期后，被告未按约定还款。

        【法院认定】
        1. 双方借贷关系成立，有借款合同、转账记录等证据支持。
        2. 被告未按约定还款构成违约。
        3. 借款利率符合法律规定的民间借贷利率保护上限。

        【判决结果】
        1. 被告应于判决生效之日起10日内偿还原告借款本金50万元。
        2. 被告应支付逾期利息（按年利率15.4%计算）。
        3. 案件受理费由被告承担。
      `;

            setSummaryResult(summary);
            setLoading(false);

            // 添加到历史记录
            const newItem: SummaryItem = {
                id: Date.now().toString(),
                document: document.substring(0, 50) + '...',
                summary,
                timestamp: new Date().toLocaleString('zh-CN'),
            };

            setHistory([newItem, ...history]);
            setDocument('');
        }, 2000);
    };

    const refreshExamples = () => {
        message.info('已更新示例案例');
    };

    return (
        <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
            <div style={{ textAlign: 'center', margin: '20px 0 40px' }}>
                <Title level={2}>智法 - 司法摘要</Title>
                <Paragraph>
                    通过AI智能分析裁判文书，提取核心要点，为您生成清晰简洁的案件摘要
                </Paragraph>
            </div>

            <Card bordered={false} style={{ marginBottom: '20px' }}>
                <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    <div>
                        <TextArea
                            rows={8}
                            placeholder="请输入或粘贴裁判文书内容..."
                            value={document}
                            onChange={(e) => setDocument(e.target.value)}
                            style={{ resize: 'none' }}
                        />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Space>
                            <Dropdown overlay={modelMenu} trigger={['click']}>
                                <Button type="primary">
                                    {models.find(m => m.key === selectedModel)?.label} <DownOutlined />
                                </Button>
                            </Dropdown>
                            <Button icon={<SyncOutlined />} onClick={refreshExamples}>
                                换一批
                            </Button>
                        </Space>
                        <Button
                            type="primary"
                            size="large"
                            icon={<SendOutlined />}
                            onClick={handleSubmit}
                            loading={loading}
                        >
                            生成摘要
                        </Button>
                    </div>
                </Space>
            </Card>

            {summaryResult && (
                <Card
                    title="司法摘要结果"
                    bordered={false}
                    style={{ marginBottom: '20px', backgroundColor: '#f9f9f9' }}
                >
                    <div style={{ whiteSpace: 'pre-line' }}>
                        {summaryResult}
                    </div>
                </Card>
            )}

            <div style={{ display: 'flex', gap: '20px' }}>
                <Card title="示例案例" style={{ flex: 1 }} extra={<SyncOutlined onClick={refreshExamples} />}>
                    <List
                        itemLayout="horizontal"
                        dataSource={exampleCases}
                        renderItem={item => (
                            <List.Item>
                                <List.Item.Meta
                                    title={<span style={{ color: '#1890ff', cursor: 'pointer' }} onClick={() => message.info(`加载${item.title}`)}>{item.title}</span>}
                                    description="点击加载示例案例内容"
                                />
                            </List.Item>
                        )}
                    />
                </Card>

                <Card title="历史记录" style={{ flex: 1 }}>
                    {history.length > 0 ? (
                        <List
                            itemLayout="horizontal"
                            dataSource={history}
                            renderItem={item => (
                                <List.Item>
                                    <List.Item.Meta
                                        title={<span style={{ color: '#1890ff', cursor: 'pointer' }} onClick={() => message.info(`查看详情`)}>{item.document}</span>}
                                        description={`创建时间: ${item.timestamp}`}
                                    />
                                </List.Item>
                            )}
                        />
                    ) : (
                        <div style={{ textAlign: 'center', padding: '20px 0' }}>
                            <Text type="secondary">暂无历史记录</Text>
                        </div>
                    )}
                </Card>
            </div>
        </div>
    );
};

export default LegalSummary; 