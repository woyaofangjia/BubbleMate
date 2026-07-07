'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type RoleType = 'customer' | 'admin' | 'agent';

interface RoleContextType {
  role: RoleType;
  setRole: (role: RoleType) => void;
  adminVerified: boolean;
  agentVerified: boolean;
  setAdminVerified: (verified: boolean) => void;
  setAgentVerified: (verified: boolean) => void;
}

const RoleContext = createContext<RoleContextType | undefined>(undefined);

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<RoleType>('customer');
  const [adminVerified, setAdminVerifiedState] = useState(false);
  const [agentVerified, setAgentVerifiedState] = useState(false);

  useEffect(() => {
    const savedRole = localStorage.getItem('bubblemate_role') as RoleType;
    if (savedRole) {
      setRoleState(savedRole);
    }
    const savedAdmin = localStorage.getItem('bubblemate_admin_verified');
    if (savedAdmin === 'true') {
      setAdminVerifiedState(true);
    }
    const savedAgent = localStorage.getItem('bubblemate_agent_verified');
    if (savedAgent === 'true') {
      setAgentVerifiedState(true);
    }
  }, []);

  const setRole = (newRole: RoleType) => {
    setRoleState(newRole);
    localStorage.setItem('bubblemate_role', newRole);
  };

  const setAdminVerified = (verified: boolean) => {
    setAdminVerifiedState(verified);
    localStorage.setItem('bubblemate_admin_verified', String(verified));
  };

  const setAgentVerified = (verified: boolean) => {
    setAgentVerifiedState(verified);
    localStorage.setItem('bubblemate_agent_verified', String(verified));
  };

  return (
    <RoleContext.Provider
      value={{
        role,
        setRole,
        adminVerified,
        agentVerified,
        setAdminVerified,
        setAgentVerified,
      }}
    >
      {children}
    </RoleContext.Provider>
  );
}

export function useRole() {
  const context = useContext(RoleContext);
  if (!context) {
    throw new Error('useRole must be used within a RoleProvider');
  }
  return context;
}