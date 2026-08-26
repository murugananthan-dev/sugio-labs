import React, { createContext, useContext, useState, ReactNode, useCallback } from 'react';
import {
  HealthStatus,
  HardwareProfile,
  PermissionRequest,
  AgentActivityLog,
} from '../types';

interface GlobalState {
  health: HealthStatus | null;
  setHealth: (h: HealthStatus | null) => void;
  hardware: HardwareProfile | null;
  setHardware: (hw: HardwareProfile | null) => void;
  pendingPermission: PermissionRequest | null;
  setPendingPermission: (p: PermissionRequest | null) => void;
  activityLogs: AgentActivityLog[];
  appendActivityLog: (log: AgentActivityLog) => void;
  voiceEnabled: boolean;
  setVoiceEnabled: (v: boolean) => void;
  speakAnnouncement: (text: string) => void;
}

const GlobalContext = createContext<GlobalState | undefined>(undefined);

export const GlobalProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [hardware, setHardware] = useState<HardwareProfile | null>(null);
  const [pendingPermission, setPendingPermission] = useState<PermissionRequest | null>(null);
  const [activityLogs, setActivityLogs] = useState<AgentActivityLog[]>([]);
  const [voiceEnabled, setVoiceEnabled] = useState<boolean>(true);

  const appendActivityLog = useCallback((log: AgentActivityLog) => {
    setActivityLogs((prev) => [...prev, log]);
  }, []);

  const speakAnnouncement = useCallback(
    (text: string) => {
      if (!voiceEnabled || !('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      window.speechSynthesis.speak(utterance);
    },
    [voiceEnabled]
  );

  return (
    <GlobalContext.Provider
      value={{
        health,
        setHealth,
        hardware,
        setHardware,
        pendingPermission,
        setPendingPermission,
        activityLogs,
        appendActivityLog,
        voiceEnabled,
        setVoiceEnabled,
        speakAnnouncement,
      }}
    >
      {children}
    </GlobalContext.Provider>
  );
};

export function useGlobalState() {
  const context = useContext(GlobalContext);
  if (context === undefined) {
    throw new Error('useGlobalState must be used within a GlobalProvider');
  }
  return context;
}
