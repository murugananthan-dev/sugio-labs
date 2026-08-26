import React from 'react';
import { Shield, Cpu, Sparkles, Volume2, VolumeX, Globe } from 'lucide-react';
import { HealthStatus, HardwareProfile } from '../types';

interface HeaderProps {
  health: HealthStatus | null;
  hardware: HardwareProfile | null;
  language: string;
  setLanguage: (lang: string) => void;
  voiceEnabled: boolean;
  setVoiceEnabled: (enabled: boolean) => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  hardware,
  language,
  setLanguage,
  voiceEnabled,
  setVoiceEnabled,
  activeTab,
  setActiveTab,
}) => {
  return (
    <header className="w-full border-b border-white/10 bg-slate-950/80 backdrop-blur-xl sticky top-0 z-40 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Brand & Tagline */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white">Sugio Labs</h1>
              <span className="pill pill-indigo">v0.1 Local Agent</span>
            </div>
            <p className="text-xs text-slate-400">
              Cross-Layer Contract Consistency • Human-in-the-Loop Governance
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 bg-slate-900/90 p-1 rounded-xl border border-white/5 overflow-x-auto max-w-full">
          {[
            { id: 'interview', label: 'Requirement Wizard' },
            { id: 'blueprint', label: 'Architecture Blueprint' },
            { id: 'graph', label: 'Contract Graph' },
            { id: 'impact', label: 'Impact Analyzer' },
            { id: 'checkpoints', label: 'Git Safety & Checkpoints' },
            { id: 'chat', label: 'AI Assistant' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                activeTab === tab.id
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {/* System Badges & Controls */}
        <div className="flex items-center gap-3">
          {/* Hardware Profile Pill */}
          {hardware && (
            <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-white/5 text-xs text-slate-300">
              <Cpu className="w-3.5 h-3.5 text-indigo-400" />
              <span>{hardware.ram_gb} GB RAM</span>
              <span className="text-slate-500">•</span>
              <span className="text-cyan-400 font-mono">{hardware.recommended_model.split(' ')[0]}</span>
            </div>
          )}

          {/* Ollama Status */}
          <div
            className={`pill ${
              health?.ollama_online ? 'pill-emerald' : 'pill-amber'
            } text-xs`}
            title={
              health?.ollama_online
                ? 'Local Ollama Engine Connected'
                : 'Local Heuristic Engine Active'
            }
          >
            <span
              className={`w-2 h-2 rounded-full ${
                health?.ollama_online ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
              }`}
            />
            <span>{health?.ollama_online ? 'Ollama Online' : 'Local Offline Engine'}</span>
          </div>

          {/* Multilingual Selector */}
          <div className="flex items-center gap-1 bg-slate-900 border border-white/10 rounded-lg px-2 py-1">
            <Globe className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="bg-transparent text-xs text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="en" className="bg-slate-900 text-white">English</option>
              <option value="tanglish" className="bg-slate-900 text-white">Tanglish</option>
              <option value="ta" className="bg-slate-900 text-white">தமிழ் (Tamil)</option>
            </select>
          </div>

          {/* Voice Notification Toggle */}
          <button
            onClick={() => setVoiceEnabled(!voiceEnabled)}
            className={`p-2 rounded-lg border transition-all ${
              voiceEnabled
                ? 'bg-indigo-600/20 border-indigo-500/40 text-indigo-300'
                : 'bg-slate-900 border-white/10 text-slate-500 hover:text-slate-300'
            }`}
            title={voiceEnabled ? 'Voice Updates: Enabled' : 'Voice Updates: Disabled'}
          >
            {voiceEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </header>
  );
};
