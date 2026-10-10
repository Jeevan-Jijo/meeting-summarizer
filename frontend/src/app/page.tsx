'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { 
  FolderKanban, 
  CheckSquare, 
  Calendar, 
  Gavel, 
  Plus, 
  ArrowRight, 
  Activity, 
  Play, 
  Clock, 
  ShieldCheck,
  Cpu,
  Layers,
  Sparkles
} from 'lucide-react';
import { api } from '@/lib/api';
import { MeetingListItem, ProcessingJob, SystemHealth } from '@/lib/types';
import { formatSecondsToTime, getStatusBadgeColor } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ProgressBar } from '@/components/ui/ProgressBar';

export default function DashboardPage() {
  const [meetings, setMeetings] = useState<MeetingListItem[]>([]);
  const [jobs, setJobs] = useState<ProcessingJob[]>([]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 5000); // Polling for job updates
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      const [meetingsData, jobsData, healthData] = await Promise.allSettled([
        api.listMeetings(),
        api.listJobs(),
        api.getHealth(),
      ]);

      if (meetingsData.status === 'fulfilled') setMeetings(meetingsData.value);
      if (jobsData.status === 'fulfilled') setJobs(jobsData.value);
      if (healthData.status === 'fulfilled') setHealth(healthData.value);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const activeJobs = jobs.filter((j) => !['COMPLETED', 'FAILED'].includes(j.status));
  const recentMeetings = meetings.slice(0, 5);

  return (
    <div className="space-y-8 max-w-7xl mx-auto animate-fade-in">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-teal-900/30 via-slate-900/40 to-slate-900/60 border border-teal-500/20 backdrop-blur-md shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-teal-600 dark:text-teal-400 text-xs font-semibold tracking-wide uppercase">
            <Sparkles className="w-4 h-4" /> Local Intelligence Dashboard
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
            Meeting Intelligence System
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Secure, GPU-accelerated local transcription, diarization, extraction, and RAG.
          </p>
        </div>

        <Link href="/meetings/new">
          <Button variant="primary" size="md">
            <Plus className="w-4 h-4" /> New Meeting
          </Button>
        </Link>
      </div>

      {/* Active Processing Banner if any */}
      {activeJobs.length > 0 && (
        <div className="p-5 rounded-2xl border border-teal-500/30 bg-teal-500/10 space-y-3 animate-pulse-fast">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-teal-800 dark:text-teal-200">
              <Activity className="w-4 h-4 text-teal-500 animate-spin" />
              Active Local Processing Pipeline ({activeJobs.length} Job{activeJobs.length > 1 ? 's' : ''})
            </div>
            <span className="text-xs text-teal-600 dark:text-teal-400 font-medium">Auto-refreshing</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {activeJobs.map((job) => (
              <div key={job.id} className="p-3 rounded-xl bg-white/80 dark:bg-slate-900/80 border border-teal-500/20 space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-800 dark:text-slate-200 truncate max-w-[200px]">
                    {job.meeting_title || `Meeting #${job.meeting_id}`}
                  </span>
                  <span className="font-mono text-teal-600 dark:text-teal-400 font-bold">
                    {job.progress_percent}%
                  </span>
                </div>
                <ProgressBar progress={job.progress_percent} />
                <p className="text-[11px] text-slate-500 truncate">
                  Stage: <strong>{job.current_step}</strong>
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Metric Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-600 dark:text-teal-400 shrink-0">
            <FolderKanban className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Total Meetings</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{meetings.length}</p>
          </div>
        </Card>

        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shrink-0">
            <CheckSquare className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Action Items Tracked</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              {meetings.reduce((acc, m) => acc + (m.action_item_count || 0), 0)}
            </p>
          </div>
        </Card>

        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-600 dark:text-amber-400 shrink-0">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Total Processed Audio</p>
            <p className="text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
              {formatSecondsToTime(meetings.reduce((acc, m) => acc + (m.duration_seconds || 0), 0))}
            </p>
          </div>
        </Card>

        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-600 dark:text-teal-400 shrink-0">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">STT Engine</p>
            <p className="text-sm font-semibold text-teal-600 dark:text-teal-400 truncate">
              {health?.deepgram?.configured ? 'Deepgram Nova-2' : 'API Key Needed'}
            </p>
          </div>
        </Card>
      </div>

      {/* Main Content Split: Recent Meetings & Quick Jump */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Meetings Table/List */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <FolderKanban className="w-4 h-4 text-teal-500" /> Recent Meetings
            </h2>
            <Link href="/meetings" className="text-xs text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-1 font-medium">
              View All ({meetings.length}) <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-3">
            {recentMeetings.length === 0 ? (
              <Card className="text-center py-12 space-y-3">
                <FolderKanban className="w-10 h-10 mx-auto text-slate-400" />
                <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
                  No meetings recorded yet.
                </p>
                <Link href="/meetings/new">
                  <Button variant="primary" size="sm">
                    <Plus className="w-4 h-4" /> Record or Upload First Meeting
                  </Button>
                </Link>
              </Card>
            ) : (
              recentMeetings.map((m) => {
                const badge = getStatusBadgeColor(m.status);
                return (
                  <Link key={m.id} href={`/meetings/${m.id}`}>
                    <Card hover className="flex items-center justify-between gap-4 p-4">
                      <div className="space-y-1 flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">
                            {m.title}
                          </h3>
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border ${badge.bg} ${badge.text}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`} />
                            {m.status}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                          <span>{new Date(m.meeting_date).toLocaleDateString()}</span>
                          <span>•</span>
                          <span className="font-mono">{formatSecondsToTime(m.duration_seconds)}</span>
                          <span>•</span>
                          <span>{m.speaker_count} speaker{m.speaker_count === 1 ? '' : 's'}</span>
                          <span>•</span>
                          <span>{m.action_item_count} action item{m.action_item_count === 1 ? '' : 's'}</span>
                        </div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-slate-400 shrink-0" />
                    </Card>
                  </Link>
                );
              })
            )}
          </div>
        </div>

        {/* Right Info Column: Local System Health */}
        <div className="space-y-4">
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-teal-500" /> Pipeline Engine Health
          </h2>

          <Card className="space-y-4 p-5">
            <div className="space-y-3 text-xs">
              <div className="flex justify-between items-center pb-2 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">FFmpeg Normalizer:</span>
                <span className={`font-semibold ${health?.ffmpeg?.available ? 'text-teal-500' : 'text-rose-500'}`}>
                  {health?.ffmpeg?.available ? 'Available' : 'Missing'}
                </span>
              </div>

              <div className="flex justify-between items-center pb-2 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Deepgram Cloud STT:</span>
                <span className={`font-semibold ${health?.deepgram?.configured ? 'text-teal-500' : 'text-amber-500'}`}>
                  {health?.deepgram?.configured ? 'Nova-2 Active' : 'Key Unconfigured'}
                </span>
              </div>

              <div className="flex justify-between items-center pb-2 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Speaker Diarization:</span>
                <span className={`font-semibold ${health?.diarization?.is_ready ? 'text-teal-500' : 'text-amber-500'}`}>
                  {health?.diarization?.is_ready ? 'Deepgram Native' : 'Requires API Key'}
                </span>
              </div>

              <div className="flex justify-between items-center pb-2 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Ollama LLM:</span>
                <span className="font-semibold text-slate-700 dark:text-slate-300 truncate max-w-[120px]">
                  {health?.ollama?.active_model || 'Connecting...'}
                </span>
              </div>
            </div>

            <Link href="/settings" className="block pt-2">
              <Button variant="outline" size="sm" className="w-full">
                View Detailed Settings & HF Token
              </Button>
            </Link>
          </Card>
        </div>
      </div>
    </div>
  );
}
