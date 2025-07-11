import React, { useState } from 'react';
import { ApiService } from '../services/api';

const DebugPanel: React.FC = () => {
  const [testResults, setTestResults] = useState<any>({});
  const [loading, setLoading] = useState(false);

  const runTests = async () => {
    setLoading(true);
    const results: any = {};

    // Test 1: Health check
    try {
      const health = await ApiService.checkHealth();
      results.health = { status: 'success', data: health };
    } catch (error) {
      results.health = { status: 'error', error: (error as Error).message };
    }

    // Test 2: Direct fetch to backend
    try {
      const directResponse = await fetch('http://localhost:8000/health');
      const directData = await directResponse.json();
      results.direct = { status: 'success', data: directData };
    } catch (error) {
      results.direct = { status: 'error', error: (error as Error).message };
    }

    // Test 3: Proxy test
    try {
      const proxyResponse = await fetch('/health');
      const proxyData = await proxyResponse.json();
      results.proxy = { status: 'success', data: proxyData };
    } catch (error) {
      results.proxy = { status: 'error', error: (error as Error).message };
    }

    // Test 4: API endpoint test
    try {
      const apiResponse = await fetch('/api/documents');
      const apiData = await apiResponse.json();
      results.api = { status: 'success', data: apiData };
    } catch (error) {
      results.api = { status: 'error', error: (error as Error).message };
    }

    setTestResults(results);
    setLoading(false);
  };

  return (
    <div className="p-6 bg-white border rounded-lg shadow-sm">
      <h3 className="text-lg font-semibold mb-4">Connection Debug Panel</h3>
      
      <button
        onClick={runTests}
        disabled={loading}
        className="mb-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Testing...' : 'Run Connection Tests'}
      </button>

      {Object.keys(testResults).length > 0 && (
        <div className="space-y-4">
          {Object.entries(testResults).map(([test, result]: [string, any]) => (
            <div key={test} className="border rounded p-3">
              <h4 className="font-medium capitalize">{test} Test</h4>
              <div className={`text-sm ${result.status === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                Status: {result.status}
              </div>
              <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-auto">
                {JSON.stringify(result.data || result.error, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default DebugPanel;
