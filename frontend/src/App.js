import React, { useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { usePrivy } from '@privy-io/react-auth';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import DashboardPreview from './pages/DashboardPreview';
import AgentConfigPage from './pages/AgentConfigPage';
import LinkAccountPage from './pages/LinkAccountPage';

function RequireAuth({ children }) {
  const { ready, authenticated } = usePrivy();
  const navigate = useNavigate();

  useEffect(() => {
    if (ready && !authenticated) {
      navigate('/', { replace: true });
    }
  }, [ready, authenticated, navigate]);

  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black text-white">
        <p className="text-sm">Initializing authentication...</p>
      </div>
    );
  }

  if (!authenticated) {
    return null;
  }

  return children;
}

function PublicRoute({ children }) {
  const { ready, authenticated } = usePrivy();
  const navigate = useNavigate();

  useEffect(() => {
    if (ready && authenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [ready, authenticated, navigate]);

  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black text-white">
        <p className="text-sm">Initializing authentication...</p>
      </div>
    );
  }

  return children;
}

function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <PublicRoute>
            <LandingPage />
          </PublicRoute>
        }
      />
      <Route
        path="/auth"
        element={
          <PublicRoute>
            <AuthPage />
          </PublicRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <DashboardPage />
          </RequireAuth>
        }
      />
      <Route path="/preview" element={<DashboardPreview />} />
      <Route
        path="/config"
        element={
          <RequireAuth>
            <AgentConfigPage />
          </RequireAuth>
        }
      />
      <Route path="/link" element={<LinkAccountPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
