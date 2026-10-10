'use client';

import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Cpu, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  Info,
  ExternalLink,
  KeyRound,
  Sparkles
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { api } from '@/lib/api';
import { SystemHealth } from '@/lib/types';

export default function SettingsPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    loadHealth();
  }, []);

  const loadHealth = async () => {
    try {
      setIsLoading(true);
      const data = await api.getHealth();
      setHealth(data);
    } catch (err) {
      console.error('Failed to load system health:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto animate-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight flex items-center gap-2">
            <Cpu className="w-6 h-6 text-teal-500" /> Pipeline Settings & Engine Health
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Real-time operational status of media normalization, Deepgram Cloud STT, local Ollama LLM, and vector embeddings.
          </p>
        </div>

        <Button variant="outline" size="sm" onClick={loadHealth} isLoading={isLoading}>
          <RefreshCw className="w-3.5 h-3.5" /> Re-check Engine Health
        </Button>
      </div>

      {/* Deepgram STT Integration Banner */}
      <Card className="p-5 border-teal-500/20 bg-teal-500/5 dark:bg-teal-950/20 space-y-2">
        <div className="flex items-center gap-2 text-teal-700 dark:text-teal-400 font-semibold text-sm">
          <Sparkles className="w-5 h-5 shrink-0" />
          <span>Deepgram Nova-2 Integration Active</span>
        </div>
        <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
          Audio normalization and RAG embedding searches run locally. High-accuracy speech-to-text and native speaker diarization are powered by Deepgram Cloud API for instant processing.
        </p>
      </Card>

      {/* Engine Status Grid */}
      <div className="space-y-4">
        <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 uppercase tracking-wider text-slate-500">
          Core Engine Status
        </h2>

        {/* 1. FFmpeg */}
        <Card className="p-5 flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                FFmpeg Media Engine
              </span>
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${health?.ffmpeg?.available ? 'bg-teal-500/10 text-teal-500' : 'bg-rose-500/10 text-rose-500'}`}>
                {health?.ffmpeg?.available ? 'Operational' : 'Not Found'}
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Binary location: <code className="font-mono text-[11px]">{health?.ffmpeg?.path || 'Checking...'}</code>
            </p>
          </div>
        </Card>

        {/* 2. Deepgram Cloud STT & Diarization */}
        <Card className="p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                Deepgram Cloud STT & Native Diarization
              </span>
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${health?.deepgram?.configured ? 'bg-teal-500/10 text-teal-500' : 'bg-amber-500/10 text-amber-500'}`}>
                {health?.deepgram?.configured ? 'Configured & Ready' : 'API Key Unconfigured'}
              </span>
            </div>
            <span className="text-xs font-mono text-slate-500">
              Model: {health?.deepgram?.model || 'nova-2'}
            </span>
          </div>

          <p className="text-xs text-slate-600 dark:text-slate-400">
            {health?.deepgram?.status_message || 'Transcribes speech and identifies speakers natively.'}
          </p>

          {!health?.deepgram?.configured && (
            <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 space-y-2 text-xs">
              <div className="font-semibold text-amber-800 dark:text-amber-200 flex items-center gap-1.5">
                <KeyRound className="w-4 h-4 text-amber-500" /> How to configure your Deepgram API Key:
              </div>
              <ol className="list-decimal list-inside space-y-1 text-amber-700 dark:text-amber-300">
                <li>Create a free account at <a href="https://console.deepgram.com" target="_blank" rel="noreferrer" className="underline inline-flex items-center gap-0.5">console.deepgram.com <ExternalLink className="w-3 h-3" /></a></li>
                <li>Create an API key in your Deepgram console dashboard.</li>
                <li>Open <code className="px-1.5 py-0.5 rounded bg-amber-200/50 dark:bg-amber-900/50 font-mono text-[11px]">backend/.env</code> in your editor.</li>
                <li>Set <code className="px-1.5 py-0.5 rounded bg-amber-200/50 dark:bg-amber-900/50 font-mono text-[11px]">DEEPGRAM_API_KEY=your_key_here</code> and restart the backend server.</li>
              </ol>
            </div>
          )}
        </Card>

        {/* 3. Ollama LLM */}
        <Card className="p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                Ollama Local LLM
              </span>
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${health?.ollama?.connected ? 'bg-teal-500/10 text-teal-500' : 'bg-amber-500/10 text-amber-500'}`}>
                {health?.ollama?.connected ? 'Connected' : 'Ollama Offline'}
              </span>
            </div>
            <span className="text-xs font-mono text-slate-500">{health?.ollama?.base_url}</span>
          </div>

          <div className="space-y-2 text-xs bg-slate-50 dark:bg-slate-800/40 p-3 rounded-xl border border-slate-200/50 dark:border-slate-700/50">
            <div className="flex justify-between">
              <span className="text-slate-500">Target Model:</span>
              <span className="font-mono font-semibold text-teal-600 dark:text-teal-400">{health?.ollama?.target_model}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Active / Resolved Model:</span>
              <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">{health?.ollama?.active_model}</span>
            </div>
            {health?.ollama?.available_models && health.ollama.available_models.length > 0 && (
              <div className="pt-2 border-t border-slate-200/50 dark:border-slate-700/50">
                <span className="text-slate-500 block mb-1">Available Local Models in Ollama:</span>
                <div className="flex flex-wrap gap-1">
                  {health.ollama.available_models.map((m) => (
                    <span key={m} className="px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-mono text-[10px]">
                      {m}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>

        {/* 4. Local Embeddings & Vector Store */}
        <Card className="p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                Sentence Transformers & FAISS Vector Store
              </span>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-teal-500/10 text-teal-500">
                Operational
              </span>
            </div>
            <span className="text-xs font-mono text-slate-500">{health?.embeddings?.device}</span>
          </div>
          <p className="text-xs text-slate-500">
            Embedding Model: <code className="font-mono text-[11px] text-slate-800 dark:text-slate-200">{health?.embeddings?.model}</code>
          </p>
        </Card>
      </div>
    </div>
  );
}
