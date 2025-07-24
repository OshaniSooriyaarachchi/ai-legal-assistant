import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../app/store';
import { loadSubscriptionData, upgradeSubscription, clearError } from '../features/subscription/subscriptionSlice';

const UsageDashboard: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const {
    currentSubscription,
    subscriptionPlans,
    loading,
    upgrading,
    error
  } = useSelector((state: RootState) => state.subscription);

  useEffect(() => {
    dispatch(loadSubscriptionData());
  }, [dispatch]);

  const handleUpgrade = async (planId: string) => {
    try {
      await dispatch(upgradeSubscription(planId)).unwrap();
      alert('Subscription upgraded successfully!');
    } catch (error) {
      console.error('Failed to upgrade subscription:', error);
    }
  };

  if (loading) {
    return (
      <div className="p-6 bg-white rounded-lg shadow-md">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded mb-4"></div>
          <div className="h-4 bg-gray-200 rounded mb-2"></div>
          <div className="h-4 bg-gray-200 rounded mb-2"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
              <button
                onClick={() => dispatch(clearError())}
                className="mt-2 text-sm text-red-600 hover:text-red-500"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Current Usage */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Usage Overview</h2>
        
        {currentSubscription && (
          <>
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-700">Daily Queries</span>
                <span className="text-sm text-gray-500">
                  {currentSubscription.current_usage} / {currentSubscription.daily_limit || 'Unlimited'}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{
                    width: currentSubscription.daily_limit 
                      ? `${Math.min((currentSubscription.current_usage / currentSubscription.daily_limit) * 100, 100)}%`
                      : '0%'
                  } as React.CSSProperties}
                ></div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-sm font-medium text-gray-700">Current Plan</h3>
                <p className="text-lg font-semibold text-gray-900">{currentSubscription.subscription.plan_display_name}</p>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-sm font-medium text-gray-700">Status</h3>
                <p className="text-lg font-semibold text-gray-900">{currentSubscription.subscription.status}</p>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-sm font-medium text-gray-700">Queries Today</h3>
                <p className="text-lg font-semibold text-gray-900">{currentSubscription.current_usage}</p>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Subscription Plans */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Subscription Plans</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {subscriptionPlans.map((plan) => (
            <div 
              key={plan.id} 
              className={`border rounded-lg p-6 ${
                currentSubscription?.subscription.plan_name === plan.name 
                  ? 'border-blue-500 bg-blue-50' 
                  : 'border-gray-200'
              }`}
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{plan.display_name}</h3>
              <p className="text-2xl font-bold text-gray-900 mb-2">
                ${plan.price_monthly}
                <span className="text-sm font-normal text-gray-500">/month</span>
              </p>
              <p className="text-sm text-gray-600 mb-4">
                {plan.daily_query_limit === 0 ? 'Unlimited queries' : `${plan.daily_query_limit} queries per day`}
              </p>
              
              <ul className="space-y-2 mb-6">
                <li className="flex items-center">
                  <svg className="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm text-gray-600">
                    {plan.daily_query_limit === 0 ? 'Unlimited queries' : `${plan.daily_query_limit} queries/day`}
                  </span>
                </li>
                <li className="flex items-center">
                  <svg className="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm text-gray-600">Document upload</span>
                </li>
                <li className="flex items-center">
                  <svg className="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm text-gray-600">24/7 support</span>
                </li>
              </ul>
              
              {currentSubscription?.subscription.plan_name === plan.name ? (
                <button
                  disabled
                  className="w-full py-2 px-4 bg-gray-300 text-gray-500 rounded-md cursor-not-allowed"
                >
                  Current Plan
                </button>
              ) : (
                <button
                  onClick={() => handleUpgrade(plan.id)}
                  disabled={upgrading}
                  className="w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {upgrading ? 'Upgrading...' : 'Upgrade'}
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default UsageDashboard;
