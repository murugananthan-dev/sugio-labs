import React, { useState } from 'react';
import { Send, Sparkles, Bot, User, Globe, MessageSquare, PlayCircle, RefreshCw } from 'lucide-react';
import { VoiceInput } from './VoiceInput';
import { sendChatMessage } from '../services/api';

interface ChatAssistantProps {
  language: string;
  setLanguage: (lang: string) => void;
  voiceEnabled: boolean;
}

interface Message {
  sender: 'user' | 'agent';
  text: string;
  timestamp: string;
}

export const ChatAssistant: React.FC<ChatAssistantProps> = ({
  language,
  setLanguage,
  voiceEnabled,
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'agent',
      text: 'Vanakkam & Welcome! I am Sugio Labs AI Assistant. You can ask me questions in English, Tamil, or Tanglish regarding your architecture, Contract Graph, or code verification.',
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [input, setInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  const speak = (text: string) => {
    if (!voiceEnabled || !('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
  };

  const handleSend = async (textToSend?: string) => {
    const text = textToSend || input;
    if (!text.trim() || loading) return;

    const userMsg: Message = {
      sender: 'user',
      text: text.trim(),
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await sendChatMessage(text.trim(), language);
      const agentMsg: Message = {
        sender: 'agent',
        text: res.reply,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, agentMsg]);
      speak(res.reply);
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'agent',
          text: 'Error connecting to local engine. Please make sure FastAPI backend is active.',
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const samplePrompts = [
    {
      label: 'Contract Graph Purpose (EN)',
      text: 'How does the Contract Graph prevent frontend/backend schema drift?',
    },
    {
      label: 'Student System Architecture (Tanglish)',
      text: 'Student Management System-oda architecture and database schema pathi explain pannu.',
    },
    {
      label: 'Zero-Trust Permissions (EN)',
      text: 'Explain how Zero-Trust Human-in-the-Loop permission gating protects the project.',
    },
  ];

  return (
    <div className="max-w-4xl mx-auto my-6 space-y-4">
      {/* Chat Container */}
      <div className="glass-panel flex flex-col h-[560px]">
        {/* Chat Header */}
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Sugio Labs Interactive Assistant</h3>
              <p className="text-[11px] text-slate-400">Local-First Multilingual Engineering Mentor</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-mono">Language:</span>
            <div className="flex bg-slate-900 rounded-lg p-1 border border-white/5 text-xs">
              {['en', 'tanglish', 'ta'].map((lang) => (
                <button
                  key={lang}
                  onClick={() => setLanguage(lang)}
                  className={`px-2 py-0.5 rounded ${
                    language === lang ? 'bg-indigo-600 text-white font-semibold' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {lang.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Message Stream */}
        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex gap-3 ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {m.sender === 'agent' && (
                <div className="w-7 h-7 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-400 shrink-0 mt-1">
                  <Bot className="w-3.5 h-3.5" />
                </div>
              )}

              <div
                className={`max-w-xl p-3.5 rounded-2xl text-xs leading-relaxed ${
                  m.sender === 'user'
                    ? 'bg-gradient-to-br from-indigo-600 to-indigo-700 text-white rounded-tr-sm shadow-md shadow-indigo-600/30'
                    : 'bg-slate-900/90 border border-white/10 text-slate-200 rounded-tl-sm'
                }`}
              >
                <p className="whitespace-pre-line">{m.text}</p>
                <span className="text-[9px] text-slate-400/80 block mt-1.5 text-right font-mono">
                  {m.timestamp}
                </span>
              </div>

              {m.sender === 'user' && (
                <div className="w-7 h-7 rounded-lg bg-cyan-600/30 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shrink-0 mt-1">
                  <User className="w-3.5 h-3.5" />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-3 justify-start">
              <div className="w-7 h-7 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-400 shrink-0">
                <Bot className="w-3.5 h-3.5" />
              </div>
              <div className="p-3 rounded-2xl bg-slate-900 border border-white/10 text-xs text-slate-400 flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
                <span>Thinking locally with Sugio Engine...</span>
              </div>
            </div>
          )}
        </div>

        {/* Suggested Quick Prompts */}
        <div className="px-4 py-2 bg-slate-950/60 border-t border-white/5 flex flex-wrap gap-1.5">
          {samplePrompts.map((p, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(p.text)}
              className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-900 border border-white/5 text-slate-300 hover:border-indigo-500/40 hover:bg-slate-800 transition-all truncate max-w-xs"
              title={p.text}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="p-3 border-t border-white/10 bg-slate-900/50 flex items-center gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={`Ask Sugio Labs in ${language === 'ta' ? 'Tamil' : language === 'tanglish' ? 'Tanglish' : 'English'}...`}
            className="flex-1 p-2.5 rounded-xl bg-slate-950 border border-white/10 text-xs text-white focus:outline-none focus:border-indigo-500"
          />
          <VoiceInput onResult={(text) => handleSend(text)} language={language} />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="btn-primary text-xs p-2.5"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
};
