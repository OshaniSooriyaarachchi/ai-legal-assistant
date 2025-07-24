import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../app/store';
import { loadSubscriptionData } from '../features/subscription/subscriptionSlice';

const UsageIndicator: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { currentSubscription, loading } = useSelector((state: RootState) => state.subscription);

  useEffect(() => {
    dispatch(loadSubscriptionData());
  }, [dispatch]);

  if (loading || !currentSubscription) {
    return (
      <div className="flex items-center space-x-2 text-sm text-gray-600">
        <div className="w-3 h-3 bg-gray-300 rounded-full animate-pulse"></div>
        <span>Loading...</span>
      </div>
    );
  }

  const usagePercentage = currentSubscription.daily_limit > 0 
    ? (currentSubscription.current_usage / currentSubscription.daily_limit) * 100 
    : 0;

  const getStatusColor = () => {
    if (usagePercentage >= 90) return 'text-red-600';
    if (usagePercentage >= 70) return 'text-yellow-600';
    return 'text-green-600';
  };

  const getIndicatorColor = () => {
    if (usagePercentage >= 90) return 'bg-red-500';
    if (usagePercentage >= 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className="flex items-center space-x-2 text-sm">
      <div className={`w-3 h-3 rounded-full ${getIndicatorColor()}`}></div>
      <span className={getStatusColor()}>
        {currentSubscription.daily_limit > 0 
          ? `${currentSubscription.current_usage}/${currentSubscription.daily_limit} queries`
          : `${currentSubscription.current_usage} queries (unlimited)`
        }
      </span>
    </div>
  );
};

export default UsageIndicator;
