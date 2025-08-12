import React from 'react';
import { useUserTypeContext } from '../contexts/UserTypeContext';

interface UserTypeSelectorProps {
  userType?: string;
  onUserTypeChange?: (type: string) => void;
  className?: string;
}

export const UserTypeSelector: React.FC<UserTypeSelectorProps> = ({ 
  userType: propUserType, 
  onUserTypeChange: propOnUserTypeChange,
  className = ""
}) => {
  const context = useUserTypeContext();
  
  // Use context if no props are provided
  const userType = propUserType ?? context.userType;
  const onUserTypeChange = propOnUserTypeChange ?? context.setUserType;

  return (
    <div className={`flex items-center space-x-4 ${className}`}>
      <label className="text-sm font-medium text-white">
        Response Style:
      </label>
      <div className="flex space-x-2">
        <button
          className={`px-3 py-1 text-sm rounded-md transition-colors ${
            userType === 'normal' 
              ? 'bg-white text-blue-600 shadow-sm font-medium' 
              : 'bg-blue-500 text-white hover:bg-blue-400 border border-blue-400'
          }`}
          onClick={() => onUserTypeChange('normal')}
          title="Get responses in simple, easy-to-understand language with practical examples"
        >
          General User
        </button>
        <button
          className={`px-3 py-1 text-sm rounded-md transition-colors ${
            userType === 'lawyer' 
              ? 'bg-white text-blue-600 shadow-sm font-medium' 
              : 'bg-blue-500 text-white hover:bg-blue-400 border border-blue-400'
          }`}
          onClick={() => onUserTypeChange('lawyer')}
          title="Get responses with technical legal terminology and detailed analysis"
        >
          Legal Professional
        </button>
      </div>
    </div>
  );
};

export default UserTypeSelector;
