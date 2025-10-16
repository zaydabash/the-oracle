import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import TopicDetail from './pages/TopicDetail';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="topics/:topicId" element={<TopicDetail />} />
      </Route>
    </Routes>
  );
}

export default App;
