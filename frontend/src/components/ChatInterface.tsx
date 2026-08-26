import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, HelpCircle, Check, Sparkles, MessageSquare } from 'lucide-react';
import { RequirementQuestion } from '../types';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface ChatInterfaceProps {
  messages: Message[];
  onSendMessage: (msg: string) => void;
  currentQuestion: RequirementQuestion | null;
  onAnswerQuestion: (questionId: string, answer: string) => void;
  isLoading: boolean;
  voiceEnabled: boolean;
  language: string;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  messages,
  onSendMessage,
  currentQuestion,
  onAnswerQuestion,
  isLoading,
  voiceEnabled,
  language,
}) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentQuestion]);

  // Voice synthesis effect
  useEffect(() => {
    if (!voiceEnabled) return;
    const lastMsg = messages[messages.length - 1];
    if (lastMsg && lastMsg.role === 'assistant' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      let textToSpeak = lastMsg.content.replace(/[*#`_-]/g, '');
      
      // Tamil / Tanglish adaptation if set
      if (language === 'ta') {
        // Simple Tamil announcement prompt
        textToSpeak = `ப்ராஜெக்ட் செயல்முறை தொடர்கிறது: ${textToSpeak.slice(0, 100)}`;
      }

      const utterance = new SpeechSynthesisUtterance(textToSpeak.slice(0, 200));
      utterance.rate = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  }, [messages, voiceEnabled, language]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;
    
    if (currentQuestion) {
      onAnswerQuestion(currentQuestion.id, inputText.trim());
    } else {
      onSendMessage(inputText.trim());
    }
    setInputText('');
  };

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Panel Header */}
      <div style={{
        padding: '14px 18px',
        borderBottom: '1px solid var(--border-card)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <MessageSquare size={18} color="#22d3ee" />
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Development Agent</h2>
        </div>
        <span className="badge badge-primary" style={{ fontSize: '0.65rem' }}>
          Supervisor Online
        </span>
      </div>

      {/* Messages Feed */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {messages.map((m) => (
          <div
            key={m.id}
            style={{
              display: 'flex',
              gap: '10px',
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '88%',
            }}
          >
            {m.role === 'assistant' && (
              <div style={{
                width: '30px',
                height: '30px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #06b6d4, #8b5cf6)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}>
                <Bot size={18} color="#ffffff" />
              </div>
            )}

            <div style={{
              background: m.role === 'user' ? 'rgba(6, 182, 212, 0.2)' : 'rgba(255, 255, 255, 0.04)',
              border: `1px solid ${m.role === 'user' ? 'rgba(6, 182, 212, 0.4)' : 'var(--border-card)'}`,
              borderRadius: '12px',
              padding: '12px 16px',
              fontSize: '0.85rem',
              lineHeight: 1.5,
            }}>
              <div style={{ whiteSpace: 'pre-wrap' }}>{m.content}</div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-subtle)', marginTop: '4px', textAlign: 'right' }}>
                {new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>

            {m.role === 'user' && (
              <div style={{
                width: '30px',
                height: '30px',
                borderRadius: '8px',
                background: 'rgba(255, 255, 255, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}>
                <User size={18} color="#f3f4f6" />
              </div>
            )}
          </div>
        ))}

        {/* Active Requirement Interview Question Card */}
        {currentQuestion && (
          <div className="glass-panel glow-primary" style={{
            padding: '16px',
            border: '1px solid rgba(6, 182, 212, 0.5)',
            background: 'rgba(6, 182, 212, 0.05)',
            borderRadius: '12px',
            marginTop: '8px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <HelpCircle size={16} color="#22d3ee" />
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#22d3ee', textTransform: 'uppercase' }}>
                Requirement Interview ({currentQuestion.id})
              </span>
            </div>

            <p style={{ fontSize: '0.9rem', fontWeight: 600, color: '#ffffff', marginBottom: '12px' }}>
              {currentQuestion.question}
            </p>

            {/* Recommended Choice Box */}
            {currentQuestion.recommended_option && (
              <div style={{
                background: 'rgba(139, 92, 246, 0.1)',
                border: '1px solid rgba(139, 92, 246, 0.3)',
                borderRadius: '8px',
                padding: '10px 12px',
                marginBottom: '12px',
                fontSize: '0.75rem',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#a78bfa', fontWeight: 600, marginBottom: '2px' }}>
                  <Sparkles size={14} />
                  <span>AI Recommendation: {currentQuestion.recommended_option}</span>
                </div>
                <p style={{ color: 'var(--text-muted)' }}>{currentQuestion.recommendation_reason}</p>
              </div>
            )}

            {/* Quick Option Buttons */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {currentQuestion.options.map((opt, i) => {
                const isRec = opt === currentQuestion.recommended_option;
                return (
                  <button
                    key={i}
                    onClick={() => onAnswerQuestion(currentQuestion.id, opt)}
                    className={isRec ? 'btn-primary' : 'btn-secondary'}
                    style={{ fontSize: '0.75rem', padding: '6px 12px' }}
                  >
                    {isRec && <Check size={13} />}
                    <span>{opt}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <form onSubmit={handleSend} style={{
        padding: '12px 16px',
        borderTop: '1px solid var(--border-card)',
        display: 'flex',
        gap: '10px',
        background: 'rgba(0, 0, 0, 0.2)',
      }}>
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={currentQuestion ? 'Type your answer or select an option above...' : 'Type requirements or change requests (e.g. "Add phone to Student")...'}
          disabled={isLoading}
          style={{
            flex: 1,
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid var(--border-card)',
            borderRadius: '10px',
            padding: '10px 14px',
            color: '#ffffff',
            fontSize: '0.85rem',
            outline: 'none',
          }}
        />
        <button type="submit" className="btn-primary" disabled={isLoading || !inputText.trim()} style={{ padding: '0 16px' }}>
          <Send size={16} />
        </button>
      </form>
    </div>
  );
};
