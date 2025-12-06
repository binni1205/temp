import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import LegalSummary from './pages/LegalSummary';
import LegalConsultation from './pages/LegalConsultation';
import LegalSearch from './pages/LegalSearch';
import LegalResearch from './pages/LegalResearch';
import DeepResearch from './pages/DeepResearch';
import Profile from './pages/Profile';

const App: React.FC = () => {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Layout />}>
                    <Route index element={<LegalSummary />} />
                    <Route path="summary" element={<LegalSummary />} />
                    <Route path="consultation" element={<LegalConsultation />} />
                    <Route path="search" element={<LegalSearch />} />
                    <Route path="legal-research" element={<LegalResearch />} />
                    <Route path="research" element={<DeepResearch />} />
                    <Route path="profile" element={<Profile />} />
                </Route>
            </Routes>
        </BrowserRouter>
    );
};

export default App; 