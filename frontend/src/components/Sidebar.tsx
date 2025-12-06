import React from 'react';
import { Layout, Menu } from 'antd';
import {
    FileTextOutlined,
    MessageOutlined,
    SearchOutlined,
    ExperimentOutlined,
    UserOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Sider } = Layout;

const Sidebar: React.FC = () => {
    const navigate = useNavigate();

    const menuItems = [
        {
            key: 'summary',
            icon: <FileTextOutlined style={{ fontSize: '18px' }} />,
            label: '司法摘要',
            onClick: () => navigate('/summary')
        },
        {
            key: 'consultation',
            icon: <MessageOutlined style={{ fontSize: '18px' }} />,
            label: '法律咨询',
            onClick: () => navigate('/consultation')
        },
        {
            key: 'search',
            icon: <SearchOutlined style={{ fontSize: '18px' }} />,
            label: '法律检索',
            onClick: () => navigate('/search')
        },
        {
            key: 'research',
            icon: <ExperimentOutlined style={{ fontSize: '18px' }} />,
            label: '深度研究',
            onClick: () => navigate('/research')
        },
        {
            key: 'profile',
            icon: <UserOutlined style={{ fontSize: '18px' }} />,
            label: '个人主页',
            onClick: () => navigate('/profile')
        }
    ];

    return (
        <Sider
            width={240}
            theme="light"
            style={{
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
                zIndex: 10,
                marginRight: '1px'
            }}
        >
            <div style={{ height: '80px', padding: '20px', textAlign: 'center' }}>
                <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 'bold' }}>智法</h1>
            </div>
            <Menu
                mode="inline"
                defaultSelectedKeys={['summary']}
                style={{ height: '100%', borderRight: 0, fontSize: '16px', padding: '0 5px' }}
                items={menuItems}
            />
        </Sider>
    );
};

export default Sidebar; 