import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from './app/store';
import AuthListener from './components/auth/AuthListener';
import ProtectedRoute from './components/auth/ProtectedRoute';
import Login from './components/auth/Login';
import SignUp from './components/auth/SignUp';
import Dashboard from './components/Dashboard';
import ForgotPassword from './components/auth/ForgotPassword';
import ResetPassword from './components/auth/ResetPassword';

function App() {
  return (
    <Provider store={store}>
      <BrowserRouter>
        <AuthListener>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<SignUp />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<Dashboard />} />
            </Route>
            <Route path="/" element={<Navigate to="/login" />} />
            {/* Auth callback handler */}
            <Route path="/auth/callback" element={<AuthCallbackHandler />} />
          </Routes>
        </AuthListener>
      </BrowserRouter>
    </Provider>
  );
}

// Auth callback handler component
const AuthCallbackHandler = () => {
  const navigate = useNavigate();
  
  React.useEffect(() => {
    // Short delay to ensure auth state is updated
    const timer = setTimeout(() => {
      navigate('/dashboard');
    }, 500);
    
    return () => clearTimeout(timer);
  }, [navigate]);
  
  return <div className="flex justify-center items-center h-screen">Completing login...</div>;
};

export default App;