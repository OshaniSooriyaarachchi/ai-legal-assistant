import React, { createContext, useContext, ReactNode } from 'react';
import { useUserType } from '../hooks/useUserType';

interface UserTypeContextType {
  userType: string;
  setUserType: (type: string) => void;
}

const UserTypeContext = createContext<UserTypeContextType | undefined>(undefined);

interface UserTypeProviderProps {
  children: ReactNode;
}

export const UserTypeProvider: React.FC<UserTypeProviderProps> = ({ children }) => {
  const { userType, setUserType } = useUserType();

  return (
    <UserTypeContext.Provider value={{ userType, setUserType }}>
      {children}
    </UserTypeContext.Provider>
  );
};

export const useUserTypeContext = () => {
  const context = useContext(UserTypeContext);
  if (context === undefined) {
    throw new Error('useUserTypeContext must be used within a UserTypeProvider');
  }
  return context;
};

export default UserTypeProvider;
