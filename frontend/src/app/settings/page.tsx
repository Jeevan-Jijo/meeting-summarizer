'use client';

import React, { useEffect, useState } from 'react';
import { 
  Settings, 
  Cpu, 
  ShieldCheck, 
  ExternalLink, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  Activity, 
  Layers, 
  Info,
  Server
} from 'lucide-react';
import { api } from '@/lib/api';
import { SystemHealth } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';

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
    <div className="space-y-8 max-w-4xl mx-auto animate-fade-in pb-12">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight flex items-center gap-2">
            <Settings className="w-6 h-6 text-teal-500" /> System Settings & Health
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Real-time status of local hardware acceleration, speech engines, LLM inference, and speaker diarization.
          </p>
        </div>

        <Button variant="outline" size="sm" onClick={loadHealth} isLoading={isLoading}>
          <RefreshCw className="w-3.5 h-3.5" /> Re-check Engine Health
        </Button>
      </div>

      {/* Privacy Notice Card */}
      <Card className="p-5 border-emerald-500/20 bg-emerald-500/5 dark:bg-emerald-950/20 space-y-2">
        <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 font-semibold text-sm">
          <ShieldCheck className="w-5 h-5 shrink-0" />
          <span>Local-First Guarantee</span>
        </div>
        <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
          All audio normalization, NVIDIA Parakeet speech-to-text, PyAnnote diarization, and Ollama Qwen3 reasoning run strictly on your local PC. Zero external API calls or pay-per-use cloud dependencies.
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
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${health?.ffmpeg?.available ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'}`}>
                {health?.ffmpeg?.available ? 'Operational' : 'Not Found'}
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Binary location: <code className="font-mono text-[11px]">{health?.ffmpeg?.path || 'Checking...'}</code>
            </p>
          </div>
        </Card>

        {/* 2. NVIDIA Parakeet STT */}
        <Card className="p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                NVIDIA Parakeet (Speech-to-Text)
              </span>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500">
                Ready
              </span>
            </div>
            <span className="text-xs font-mono text-slate-500">
              {(health?.parakeet || health?.whisper)?.device?.toUpperCase()} ({(health?.parakeet || health?.whisper)?.compute_type})
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs bg-slate-50 dark:bg-slate-800/40 p-3 rounded-xl border border-slate-200/50 dark:border-slate-700/50">
            <div>
              <span className="text-slate-500 block">Primary Model:</span>
              <span className="font-mono font-medium text-slate-800 dark:text-slate-200">{(health?.parakeet || health?.whisper)?.primary_model}</span>
            </div>
            <div>
              <span className="text-slate-500 block">CUDA Acceleration:</span>
              <span className="font-medium text-slate-800 dark:text-slate-200">
                {(health?.parakeet || health?.whisper)?.cuda_available ? `Yes (${(health?.parakeet || health?.whisper)?.gpu_name || 'GPU'})` : 'CPU Mode'}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block">VRAM Available:</span>
              <span className="font-mono font-medium text-slate-800 dark:text-slate-200">{(health?.parakeet || health?.whisper)?.vram_gb || 0} GB</span>
            </div>
          </div>
        </Card>

        {/* 3. Ollama LLM */}
        <Card className="p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                Ollama Local LLM
              </span>
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${health?.ollama?.connected ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-500'}`}>
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

        {/* 4. Speaker Diarization & Hugging Face Token Guide */}
        <Card className="p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                Speaker Diarization (pyannote 3.1)
              </span>
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${health?.diarization?.is_ready ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-500'}`}>
                {health?.diarization?.is_ready ? 'Ready with Token' : 'Fallback Mode'}
              </span>
            </div>
          </div>

          <p className="text-xs text-slate-600 dark:text-slate-400">
            {health?.diarization?.status_message}
          </p>

          <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-700/60 bg-slate-50 dark:bg-slate-800/40 space-y-2 text-xs">
            <div className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
              <Info className="w-4 h-4 text-teal-500" /> How to enable pyannote diarization:
            </div>
            <ol className="list-decimal list-inside space-y-1 text-slate-600 dark:text-slate-300">
              <li>Create a free account at <a href="https://huggingface.co/join" target="_blank" rel="noreferrer" className="text-teal-500 underline inline-flex items-center gap-0.5">huggingface.co <ExternalLink className="w-3 h-3" /></a></li>
              <li>Accept terms at <a href="https://huggingface.co/pyannote/speaker-diarization-3.1" target="_blank" rel="noreferrer" className="text-teal-500 underline inline-flex items-center gap-0.5">pyannote/speaker-diarization-3.1 <ExternalLink className="w-3 h-3" /></a></li>
              <li>Generate a token at <a href="https://huggingface.co/settings/tokens" target="_blank" rel="noreferrer" className="text-teal-500 underline inline-flex items-center gap-0.5">huggingface.co/settings/tokens <ExternalLink className="w-3 h-3" /></a></li>
              <li>Set <code className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-700 font-mono text-[11px]">HF_TOKEN=hf_...</code> in <code className="font-mono text-[11px]">backend/.env</code> or your Windows environment variables.</li>
            </ol>
          </div>
        </Card>
      </div>
    </div>
  );
}
