'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Play, Sparkles, Trash2, Quote, Loader2 } from 'lucide-react';
import { ChatMessage, Citation } from '@/lib/types';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { formatSecondsToTime, cn } from '@/lib/utils';

interface ChatPaneProps {
  meetingId: number;
  meetingTitle: string;
  onSeek: (seconds: number) => void;
}

export const ChatPane: React.FC<ChatPaneProps> = ({
  meetingId,
  meetingTitle,
  onSeek,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    loadHistory();
  }, [meetingId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const loadHistory = async () => {
    try {
      const history = await api.getChatHistory(meetingId);
      setMessages(history);
    } catch (err) {
      console.error('Failed to load chat history:', err);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const query = inputQuery.trim();
    if (!query || isLoading) return;

    setInputQuery('');
    const tempUserMsg: ChatMessage = {
      meeting_id: meetingId,
      role: 'user',
      content: query,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setIsLoading(true);

    try {
      const res = await api.sendChatMessage(meetingId, query);
      const assistantMsg: ChatMessage = {
        meeting_id: meetingId,
        role: 'assistant',
        content: res.answer,
        citations: res.citations,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        meeting_id: meetingId,
        role: 'assistant',
        content: `Error generating answer: ${err.message || 'Local AI service unavailable.'}`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = async () => {
    if (!confirm('Clear chat conversation history for this meeting?')) return;
    try {
      await api.clearChatHistory(meetingId);
      setMessages([]);
    } catch (err) {
      console.error('Failed to clear history:', err);
    }
  };

  return (
    <div className="flex flex-col h-[650px] rounded-2xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/40 backdrop-blur-sm overflow-hidden shadow-sm">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-slate-200/80 dark:border-slate-800/80 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/60">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-600 dark:text-teal-400 flex items-center justify-center">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Meeting Assistant
            </h3>
            <p className="text-[11px] text-slate-400">
              Local RAG with FAISS transcript citations
            </p>
          </div>
        </div>

        {messages.length > 0 && (
          <button
            onClick={handleClearHistory}
            className="text-slate-400 hover:text-rose-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            title="Clear Chat History"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {messages.length === 0 && !isLoading && (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400 space-y-3">
            <Sparkles className="w-8 h-8 text-teal-500/60 animate-pulse" />
            <div className="max-w-xs space-y-1">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Ask anything about "{meetingTitle}"
              </p>
              <p className="text-xs text-slate-400">
                Answers cite exact transcript timestamps from this meeting.
              </p>
            </div>
            <div className="flex flex-wrap gap-2 justify-center pt-2">
              {[
                'What were the key decisions?',
                'Who was assigned which tasks?',
                'What are the upcoming deadlines?',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setInputQuery(suggestion)}
                  className="text-[11px] px-2.5 py-1 rounded-full border border-slate-200 dark:border-slate-800 hover:border-teal-500 hover:text-teal-500 transition text-slate-500 dark:text-slate-400 bg-white dark:bg-slate-800"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={cn(
              'flex gap-3 text-sm animate-fade-in',
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            )}
          >
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-lg bg-teal-500/10 text-teal-600 dark:text-teal-400 flex items-center justify-center shrink-0 mt-0.5">
                <Bot className="w-4 h-4" />
              </div>
            )}

            <div
              className={cn(
                'max-w-[85%] rounded-2xl p-3.5 space-y-2',
                msg.role === 'user'
                  ? 'bg-teal-600 text-white rounded-tr-xs'
                  : 'bg-slate-100 dark:bg-slate-800/80 text-slate-800 dark:text-slate-200 rounded-tl-xs border border-slate-200/50 dark:border-slate-700/50'
              )}
            >
              <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>

              {/* Citations Pill Bar */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="pt-2 border-t border-slate-200/50 dark:border-slate-700/50 space-y-1.5">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block">
                    Source Citations
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {msg.citations.map((c, cIdx) => (
                      <button
                        key={cIdx}
                        onClick={() => onSeek(c.start_time)}
                        className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-teal-500/10 hover:bg-teal-500 hover:text-white text-teal-600 dark:text-teal-400 border border-teal-500/20 transition"
                        title={`Jump to [${c.timestamp_str}]: ${c.text}`}
                      >
                        <Play className="w-2.5 h-2.5 fill-current" />
                        {c.timestamp_str}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-lg bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 flex items-center justify-center shrink-0 mt-0.5">
                <User className="w-4 h-4" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3 text-sm animate-fade-in">
            <div className="w-7 h-7 rounded-lg bg-teal-500/10 text-teal-600 dark:text-teal-400 flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-3.5 rounded-2xl bg-slate-100 dark:bg-slate-800/80 rounded-tl-xs border border-slate-200/50 dark:border-slate-700/50 flex items-center gap-2 text-slate-500 text-xs">
              <Loader2 className="w-4 h-4 animate-spin text-teal-500" />
              Searching transcript & generating evidence-backed answer...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <form onSubmit={handleSendMessage} className="p-3 border-t border-slate-200/80 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-900/60 flex gap-2">
        <input
          type="text"
          placeholder="Ask a question about this meeting..."
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          disabled={isLoading}
          className="flex-1 px-3.5 py-2 rounded-xl text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
        />
        <Button type="submit" variant="primary" size="md" disabled={!inputQuery.trim() || isLoading}>
          <Send className="w-4 h-4" />
        </Button>
      </form>
    </div>
  );
};
