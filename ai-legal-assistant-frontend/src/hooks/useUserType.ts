import { useState, useEffect } from 'react';

/**
 * Custom hook for managing user type preference
 * Stores the preference in localStorage for persistence across sessions
 */
export const useUserType = () => {
  const [userType, setUserType] = useState<string>(() => {
    // Initialize from localStorage or default to 'normal'
    const saved = localStorage.getItem('userType');
    return saved || 'normal';
  });

  // Update localStorage whenever userType changes
  useEffect(() => {
    localStorage.setItem('userType', userType);
  }, [userType]);

  const handleUserTypeChange = (newType: string) => {
    if (newType === 'normal' || newType === 'lawyer') {
      setUserType(newType);
    }
  };

  return {
    userType,
    setUserType: handleUserTypeChange,
  };
};

export default useUserType;
