import React, { useState } from 'react';
import {
    Input, Button, Card, Typography, Space, List, message,
    Empty, Spin, Tag, Drawer, Divider, Tooltip, Row, Col
} from 'antd';
import {
    SearchOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
    FileTextOutlined, CopyOutlined
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';

const { TextArea } = Input;
const { Title, Paragraph, Text } = Typography;

// API基础地址
const API_BASE = 'http://118.195.205.71:45855/api/legal-research';

interface LegalResult {
    content: string;
    law_name: string;
    simple_law_name: string;
    article: string;
    article_num: number | null;
    score: number;
    metadata: Record<string, any>;
}

interface SearchResponse {
    query: string;
    search_type: 'exact' | 'fuzzy' | 'none';
    results: LegalResult[];
    message: string;
}

const LegalResearch: React.FC = () => {
    const [query, setQuery] = useState<string>('');
    const [topK, setTopK] = useState<number>(3);
    const [loading, setLoading] = useState<boolean>(false);
    const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
    const [selectedResult, setSelectedResult] = useState<LegalResult | null>(null);
    const [drawerVisible, setDrawerVisible] = useState<boolean>(false);

    // 执行搜索
    const handleSearch = async () => {
        if (!query.trim()) {
            message.warning('请输入查询内容');
            return;
        }

        setLoading(true);
        try {
            const response = await fetch(`${API_BASE}/search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: query.trim(),
                    top_k: topK
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '检索失败');
            }

            const data: SearchResponse = await response.json();
            setSearchResult(data);

            if (data.results.length === 0) {
                message.info('未找到匹配的法律条文');
            } else {
                message.success(`找到 ${data.results.length} 条结果`);
            }
        } catch (error) {
            message.error(`检索出错: ${error instanceof Error ? error.message : '未知错误'}`);
        } finally {
            setLoading(false);
        }
    };

    // 显示详情抽屉
    const showDetail = (result: LegalResult) => {
        setSelectedResult(result);
        setDrawerVisible(true);
    };

    // 复制内容到剪贴板
    const copyToClipboard = async (text: string) => {
        try {
            await navigator.clipboard.writeText(text);
            message.success('已复制到剪贴板');
        } catch {
            message.error('复制失败');
        }
    };

    // 渲染搜索类型标签
    const renderSearchTypeTag = (type: string) => {
        if (type === 'exact') {
            return (
                <Tag icon={<CheckCircleOutlined />} color="success">
                    精确匹配
                </Tag>
            );
        } else if (type === 'fuzzy') {
            return (
                <Tag icon={<ExclamationCircleOutlined />} color="orange">
                    向量相似度
                </Tag>
            );
        } else {
            return (
                <Tag color="error">
                    无结果
                </Tag>
            );
        }
    };

    // 格式化相似度得分
    const formatScore = (score: number) => {
        return (score * 100).toFixed(1);
    };

    return (
        <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
            <Card>
                <Title level={2}>
                    <FileTextOutlined /> 法律检索
                </Title>
                <Paragraph>
                    基于向量数据库的两层法律检索系统。
                    <br />
                    <Text type="secondary">
                        • 精确检索：法律名称 + 法条号完全匹配
                        <br />
                        • 模糊检索：向量相似度搜索（当精确匹配失败时）
                    </Text>
                </Paragraph>

                <Divider />

                {/* 搜索表单 */}
                <Space direction="vertical" style={{ width: '100%' }} size="large">
                    {/* 查询输入框 */}
                    <div>
                        <Text strong>查询内容</Text>
                        <Tooltip title='示例: "《合同法》第六十条" 或 "合同责任如何承担"'>
                            <TextArea
                                rows={3}
                                placeholder='输入查询内容，例如："《合同法》第六十条" 或 "合同相关条款"'
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                onPressEnter={(e) => {
                                    if (e.ctrlKey || e.metaKey) {
                                        handleSearch();
                                    }
                                }}
                                status={!query.trim() && searchResult ? 'error' : ''}
                            />
                        </Tooltip>
                    </div>

                    {/* 参数设置 */}
                    <Row gutter={16}>
                        <Col span={12}>
                            <Text strong>返回结果数 (Top-K)</Text>
                            <Input
                                type="number"
                                min={1}
                                max={10}
                                value={topK}
                                onChange={(e) => setTopK(parseInt(e.target.value) || 3)}
                                style={{ marginTop: '8px' }}
                            />
                        </Col>
                        <Col span={12} style={{ display: 'flex', alignItems: 'flex-end' }}>
                            <Button
                                type="primary"
                                size="large"
                                icon={<SearchOutlined />}
                                onClick={handleSearch}
                                loading={loading}
                                style={{ width: '100%' }}
                            >
                                {loading ? '检索中...' : '执行检索'}
                            </Button>
                        </Col>
                    </Row>
                </Space>

                <Divider />

                {/* 结果展示 */}
                {searchResult && (
                    <Space direction="vertical" style={{ width: '100%' }} size="large">
                        {/* 结果摘要 */}
                        <Card type="inner" style={{ background: '#f5f5f5' }}>
                            <Row gutter={16}>
                                <Col xs={24} sm={12}>
                                    <Text>
                                        <strong>搜索类型：</strong> {renderSearchTypeTag(searchResult.search_type)}
                                    </Text>
                                </Col>
                                <Col xs={24} sm={12}>
                                    <Text>
                                        <strong>匹配数：</strong> {searchResult.results.length} 条
                                    </Text>
                                </Col>
                            </Row>
                            <Paragraph style={{ margin: '12px 0 0 0', color: '#666' }}>
                                {searchResult.message}
                            </Paragraph>
                        </Card>

                        {/* 结果列表 */}
                        {searchResult.results.length > 0 ? (
                            <List
                                dataSource={searchResult.results}
                                renderItem={(result, index) => (
                                    <List.Item
                                        key={index}
                                        style={{
                                            padding: '16px',
                                            border: '1px solid #e8e8e8',
                                            borderRadius: '4px',
                                            marginBottom: '12px',
                                            cursor: 'pointer',
                                            transition: 'all 0.3s',
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                                            e.currentTarget.style.background = '#fafafa';
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.boxShadow = 'none';
                                            e.currentTarget.style.background = 'white';
                                        }}
                                        onClick={() => showDetail(result)}
                                    >
                                        <List.Item.Meta
                                            title={
                                                <Space>
                                                    <Text strong>{result.simple_law_name}</Text>
                                                    <Tag color="blue">{result.article}</Tag>
                                                    {searchResult.search_type === 'fuzzy' && (
                                                        <Tag color="orange">
                                                            相似度: {formatScore(result.score)}%
                                                        </Tag>
                                                    )}
                                                </Space>
                                            }
                                            description={
                                                <Paragraph
                                                    ellipsis={{ rows: 2 }}
                                                    style={{ marginTop: '8px', color: '#666' }}
                                                >
                                                    {result.content.substring(0, 150)}...
                                                </Paragraph>
                                            }
                                        />
                                    </List.Item>
                                )}
                            />
                        ) : (
                            <Empty
                                description="未找到匹配的法律条文"
                                style={{ marginTop: '24px' }}
                            />
                        )}
                    </Space>
                )}

                {/* 初始状态提示 */}
                {!searchResult && (
                    <Empty
                        description="输入查询内容开始检索"
                        style={{ marginTop: '48px' }}
                    />
                )}
            </Card>

            {/* 详情抽屉 */}
            {selectedResult && (
                <Drawer
                    title="法律条文详情"
                    placement="right"
                    onClose={() => setDrawerVisible(false)}
                    open={drawerVisible}
                    width={500}
                >
                    <Space direction="vertical" style={{ width: '100%' }} size="large">
                        {/* 基本信息 */}
                        <div>
                            <Paragraph>
                                <Text strong>法律名称：</Text>
                                <br />
                                <Text>{selectedResult.law_name}</Text>
                            </Paragraph>
                            <Paragraph>
                                <Text strong>法条号：</Text>
                                <br />
                                <Text>{selectedResult.article}</Text>
                            </Paragraph>
                            {selectedResult.score < 1 && (
                                <Paragraph>
                                    <Text strong>相似度：</Text>
                                    <br />
                                    <Text>{formatScore(selectedResult.score)}%</Text>
                                </Paragraph>
                            )}
                        </div>

                        <Divider />

                        {/* 条文内容 */}
                        <div>
                            <Text strong style={{ display: 'block', marginBottom: '8px' }}>
                                条文内容
                            </Text>
                            <Card type="inner">
                                <ReactMarkdown>{selectedResult.content}</ReactMarkdown>
                            </Card>
                        </div>

                        {/* 操作按钮 */}
                        <Space style={{ width: '100%' }}>
                            <Button
                                type="primary"
                                icon={<CopyOutlined />}
                                onClick={() => copyToClipboard(selectedResult.content)}
                            >
                                复制
                            </Button>
                        </Space>
                    </Space>
                </Drawer>
            )}
        </div>
    );
};

export default LegalResearch;
