import React from 'react';
import { UsageInfo } from '../services/api';

interface RateLimitModalProps {
  isOpen: boolean;
  onClose: () => void;
  usageInfo: UsageInfo;
  onUpgrade: (planName: string) => void;
}

const RateLimitModal: React.FC<RateLimitModalProps> = ({
  isOpen,
  onClose,
  usageInfo,
  onUpgrade
}) => {
  if (!isOpen) return null;

  const usagePercentage = (usageInfo.daily_usage / usageInfo.daily_limit) * 100;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
        <div className="text-center">
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
            <svg
              className="h-6 w-6 text-red-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
          </div>
          
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Daily Query Limit Reached
          </h3>
          
          <div className="mb-4">
            <p className="text-sm text-gray-600 mb-3">
            You've used all {usageInfo?.daily_limit || 'your'} of your daily queries on the{' '}
            <span className="font-semibold">
                {usageInfo?.subscription?.plan_display_name || 'current'}
            </span> plan.
            </p>
            
            <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
              <div
                className="bg-red-500 h-2 rounded-full"
                style={{ width: `${Math.min(usagePercentage, 100)}%` }}
              ></div>
            </div>
            
            <p className="text-xs text-gray-500">
              {usageInfo.daily_usage} / {usageInfo.daily_limit} queries used today
            </p>
          </div>
          
          <div className="space-y-3">
            <p className="text-sm text-gray-600">
              Upgrade your plan to continue asking questions and get more features:
            </p>
            
            <div className="space-y-2">
              <button
                onClick={() => onUpgrade('premium')}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors"
              >
                Upgrade to Premium
                <span className="block text-xs opacity-90">50 queries/day</span>
              </button>
              
              <button
                onClick={() => onUpgrade('professional')}
                className="w-full bg-purple-600 text-white py-2 px-4 rounded-md hover:bg-purple-700 transition-colors"
              >
                Upgrade to Professional
                <span className="block text-xs opacity-90">200 queries/day</span>
              </button>
            </div>
            
            <div className="pt-3 border-t">
              <button
                onClick={onClose}
                className="w-full bg-gray-200 text-gray-800 py-2 px-4 rounded-md hover:bg-gray-300 transition-colors"
              >
                Continue Tomorrow
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RateLimitModal;
