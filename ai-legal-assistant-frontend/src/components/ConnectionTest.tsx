import React, { useState, useEffect } from 'react';
import { ApiService } from '../services/api';

const ConnectionTest: React.FC = () => {
  const [backendStatus, setBackendStatus] = useState<'checking' | 'connected' | 'failed'>('checking');

  useEffect(() => {
    const checkConnection = async () => {
      try {
        await ApiService.checkHealth();
        setBackendStatus('connected');
      } catch (error) {
        setBackendStatus('failed');
      }
    };

    checkConnection();
  }, []);

  return (
    <div className="p-4 border rounded">
      <h3 className="font-semibold mb-2">Backend Connection Status</h3>
      <div className="flex items-center">
        <div
          className={`w-3 h-3 rounded-full mr-2 ${
            backendStatus === 'connected'
              ? 'bg-green-500'
              : backendStatus === 'failed'
              ? 'bg-red-500'
              : 'bg-yellow-500'
          }`}
        />
        <span>
          {backendStatus === 'connected'
            ? 'Connected to backend'
            : backendStatus === 'failed'
            ? 'Failed to connect to backend'
            : 'Checking connection...'}
        </span>
      </div>
    </div>
  );
};

export default ConnectionTest;
