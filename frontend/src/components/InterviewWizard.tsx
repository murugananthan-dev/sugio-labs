import React, { useState } from 'react';
import { Sparkles, ArrowRight, CheckCircle2, HelpCircle, RefreshCw } from 'lucide-react';
import { RequirementQuestion } from '../types';

interface InterviewWizardProps {
  question: RequirementQuestion | null;
  questionNumber: number;
  totalQuestions: number;
  loading: boolean;
  onAnswer: (questionId: string, answer: string) => void;
  onRestart: () => void;
}

export const InterviewWizard: React.FC<InterviewWizardProps> = ({
  question,
  questionNumber,
  totalQuestions,
  loading,
  onAnswer,
  onRestart,
}) => {
  const [selectedOption, setSelectedOption] = useState<string>('');
  const [customAnswer, setCustomAnswer] = useState<string>('');
  const [isCustom, setIsCustom] = useState<boolean>(false);

  // Set default selection to recommended option whenever question changes
  React.useEffect(() => {
    if (question?.recommended_option) {
      setSelectedOption(question.recommended_option);
      setIsCustom(false);
      setCustomAnswer('');
    }
  }, [question]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question) return;
    const answer = isCustom ? customAnswer : selectedOption;
    if (!answer.trim()) return;
    onAnswer(question.id, answer);
  };

  if (!question) {
    return (
      <div className="glass-panel p-8 text-center flex flex-col items-center justify-center max-w-xl mx-auto my-8">
        <Sparkles className="w-12 h-12 text-indigo-400 mb-4 animate-pulse" />
        <h3 className="text-xl font-bold text-white mb-2">Ready to Start Requirement Gathering?</h3>
        <p className="text-slate-400 text-sm mb-6">
          Sugio Labs will guide your team step-by-step with tailored recommendations for architecture, stack, and data models.
        </p>
        <button onClick={onRestart} className="btn-primary">
          <span>Start Requirement Wizard</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    );
  }

  const progressPercent = Math.round((questionNumber / totalQuestions) * 100);

  return (
    <div className="max-w-3xl mx-auto my-6">
      {/* Progress Card */}
      <div className="mb-4 flex items-center justify-between text-xs text-slate-400 px-1">
        <span>Step {questionNumber} of {totalQuestions}</span>
        <span className="font-mono text-indigo-400">{progressPercent}% Completed</span>
      </div>
      <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-white/5 mb-6">
        <div
          className="h-full bg-gradient-to-r from-indigo-500 via-indigo-400 to-cyan-400 transition-all duration-500"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Main Question Card */}
      <div className="glass-panel p-6 md:p-8 relative overflow-hidden">
        <div className="flex items-center justify-between gap-2 mb-4">
          <span className="pill pill-indigo text-xs uppercase tracking-wider font-mono">
            {question.category}
          </span>
          <button
            onClick={onRestart}
            className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Restart</span>
          </button>
        </div>

        <h2 className="text-xl md:text-2xl font-bold text-white mb-4 leading-snug">
          {question.question}
        </h2>

        {/* AI Intelligent Recommendation Box */}
        {question.recommended_option && (
          <div className="mb-6 p-4 rounded-xl bg-indigo-950/40 border border-indigo-500/30 backdrop-blur-md">
            <div className="flex items-center gap-2 text-indigo-300 font-semibold text-xs mb-1">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span>AI Recommendation</span>
            </div>
            <p className="text-sm text-slate-200 font-medium mb-1">
              {question.recommended_option}
            </p>
            {question.recommendation_reason && (
              <p className="text-xs text-slate-400 leading-relaxed">
                💡 <strong className="text-slate-300">Why this fits:</strong> {question.recommendation_reason}
              </p>
            )}
          </div>
        )}

        {/* Options List */}
        <form onSubmit={handleSubmit} className="space-y-3">
          {question.options.map((option, idx) => {
            const isRecommended = option === question.recommended_option;
            const isSelected = !isCustom && selectedOption === option;

            return (
              <div
                key={idx}
                onClick={() => {
                  setSelectedOption(option);
                  setIsCustom(false);
                }}
                className={`p-4 rounded-xl border cursor-pointer transition-all flex items-start gap-3 ${
                  isSelected
                    ? 'bg-indigo-600/20 border-indigo-500 shadow-md shadow-indigo-500/20'
                    : 'bg-slate-900/60 border-white/5 hover:border-white/20 hover:bg-slate-900'
                }`}
              >
                <div className={`mt-0.5 w-4 h-4 rounded-full border flex items-center justify-center ${
                  isSelected ? 'border-indigo-400 bg-indigo-600' : 'border-slate-600'
                }`}>
                  {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                </div>

                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-100">{option}</span>
                    {isRecommended && (
                      <span className="pill pill-emerald text-[10px]">Recommended</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {/* Custom Write-In Option */}
          <div
            onClick={() => setIsCustom(true)}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              isCustom
                ? 'bg-indigo-600/20 border-indigo-500 shadow-md shadow-indigo-500/20'
                : 'bg-slate-900/60 border-white/5 hover:border-white/20 hover:bg-slate-900'
            }`}
          >
            <div className="flex items-center gap-3 mb-2">
              <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                isCustom ? 'border-indigo-400 bg-indigo-600' : 'border-slate-600'
              }`}>
                {isCustom && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
              </div>
              <span className="text-sm font-medium text-slate-300">Custom Answer / Specific Requirement</span>
            </div>

            {isCustom && (
              <textarea
                value={customAnswer}
                onChange={(e) => setCustomAnswer(e.target.value)}
                placeholder="Type your specific requirement or custom stack configuration..."
                rows={2}
                className="w-full mt-2 p-2.5 rounded-lg bg-slate-950 border border-white/10 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                autoFocus
              />
            )}
          </div>

          {/* Submit Button */}
          <div className="pt-4 flex justify-end">
            <button
              type="submit"
              disabled={loading || (!isCustom && !selectedOption) || (isCustom && !customAnswer.trim())}
              className="btn-primary"
            >
              <span>{questionNumber === totalQuestions ? 'Generate Project Blueprint' : 'Next Step'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
