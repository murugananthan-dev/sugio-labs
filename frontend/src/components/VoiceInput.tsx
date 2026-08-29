import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff } from 'lucide-react';

interface VoiceInputProps {
  onResult: (text: string) => void;
  language: string;
  disabled?: boolean;
}

export const VoiceInput: React.FC<VoiceInputProps> = ({ onResult, language, disabled }) => {
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(true);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setIsSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;

    // Map internal language state to BCP 47
    if (language === 'ta') {
      recognition.lang = 'ta-IN';
    } else if (language === 'tanglish') {
      recognition.lang = 'en-IN'; // often best for mixed EN/TA
    } else {
      recognition.lang = 'en-US';
    }

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      onResult(transcript);
      setIsListening(false);
    };

    recognition.onerror = (event: any) => {
      console.warn('Speech recognition error:', event.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.abort();
    };
  }, [language, onResult]);

  const toggleListen = () => {
    if (!isSupported || disabled) return;

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      try {
        recognitionRef.current?.start();
        setIsListening(true);
      } catch (err) {
        console.warn('Failed to start speech recognition', err);
        setIsListening(false);
      }
    }
  };

  if (!isSupported) {
    return (
      <button
        type="button"
        disabled
        className="p-2 rounded-lg text-slate-500 bg-slate-900 border border-white/5 cursor-not-allowed"
        title="Voice input unavailable in this browser"
      >
        <MicOff className="w-4 h-4" />
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={toggleListen}
      disabled={disabled}
      className={`p-2 rounded-lg transition-colors border ${
        isListening
          ? 'bg-rose-500/20 text-rose-400 border-rose-500/50 animate-pulse'
          : 'bg-slate-900 border-white/10 text-slate-400 hover:text-white hover:border-indigo-500/40'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      title={isListening ? 'Stop listening' : 'Speak'}
    >
      <Mic className="w-4 h-4" />
    </button>
  );
};
