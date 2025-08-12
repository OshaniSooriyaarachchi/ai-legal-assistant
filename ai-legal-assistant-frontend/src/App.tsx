import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from './app/store';
import { UserTypeProvider } from './contexts/UserTypeContext';
import AuthListener from './components/auth/AuthListener';
import ProtectedRoute from './components/auth/ProtectedRoute';
import Login from './components/auth/Login';
import SignUp from './components/auth/SignUp';
import Dashboard from './components/Dashboard';
import ForgotPassword from './components/auth/ForgotPassword';
import ResetPassword from './components/auth/ResetPassword';
import AuthCallback from './components/auth/AuthCallback';
import AdminDashboard from './components/admin/AdminDashboard';

function App() {
  return (
    <Provider store={store}>
      <UserTypeProvider>
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
              <Route path="/auth/callback" element={<AuthCallback />} />
              <Route path="/admin" element={<AdminDashboard />} />
            </Routes>
          </AuthListener>
        </BrowserRouter>
      </UserTypeProvider>
    </Provider>
  );
}

export default App;