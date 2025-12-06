import React from 'react';
import { Layout as AntLayout } from 'antd';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

const { Content } = AntLayout;

const Layout: React.FC = () => {
    return (
        <AntLayout style={{ minHeight: '100vh' }}>
            <Sidebar />
            <AntLayout style={{ background: '#fff' }}>
                <Content style={{ padding: '24px 24px 24px 30px', minHeight: 280 }}>
                    <Outlet />
                </Content>
            </AntLayout>
        </AntLayout>
    );
};

export default Layout; 