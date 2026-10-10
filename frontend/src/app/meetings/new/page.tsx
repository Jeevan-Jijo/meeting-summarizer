'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Mic, UploadCloud, ArrowLeft, Activity, CheckCircle2, AlertCircle } from 'lucide-react';
import Link from 'next/link';
import { FileUploader } from '@/components/meetings/FileUploader';
import { AudioRecorder } from '@/components/meetings/AudioRecorder';
import { api } from '@/lib/api';
import { ProgressBar } from '@/components/ui/ProgressBar';

export default function NewMeetingPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'upload' | 'record'>('upload');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [currentJob, setCurrentJob] = useState<{ id: number; meeting_id: number; progress: number; step: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUploadSubmit = async (file: File, title: string, description?: string) => {
    setIsSubmitting(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', title);
      if (description) formData.append('description', description);

      const res = await api.uploadMeeting(formData);
      setCurrentJob({
        id: res.job_id,
        meeting_id: res.meeting_id,
        progress: 10,
        step: 'Initializing pipeline...',
      });

      // Poll job progress or redirect to meeting view immediately
      pollJobAndRedirect(res.job_id, res.meeting_id);
    } catch (err: any) {
      setError(err.message || 'Upload failed');
      setIsSubmitting(false);
    }
  };

  const pollJobAndRedirect = (jobId: number, meetingId: number) => {
    const interval = setInterval(async () => {
      try {
        const job = await api.getJob(jobId);
        setCurrentJob({
          id: jobId,
          meeting_id: meetingId,
          progress: job.progress_percent,
          step: job.current_step,
        });

        if (job.status === 'COMPLETED' || job.progress_percent >= 100) {
          clearInterval(interval);
          router.push(`/meetings/${meetingId}`);
        } else if (job.status === 'FAILED') {
          clearInterval(interval);
          setError(job.error_message || 'Processing failed');
          setIsSubmitting(false);
        }
      } catch (err) {
        // If error, redirect directly to meeting page where user can see status
        clearInterval(interval);
        router.push(`/meetings/${meetingId}`);
      }
    }, 1500);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      {/* Top Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <Link href="/meetings" className="hover:text-teal-500 transition flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Meetings
        </Link>
      </div>

      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
          Create New Meeting
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Upload an audio/video recording or record directly through your browser microphone.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 text-xs text-rose-600 dark:text-rose-400 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Mode Tabs */}
      {!isSubmitting && (
        <div className="flex rounded-xl p-1 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
          <button
            onClick={() => setActiveTab('upload')}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'upload'
                ? 'bg-white dark:bg-slate-800 text-teal-600 dark:text-teal-400 shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
          >
            <UploadCloud className="w-4 h-4" /> Upload Recording
          </button>
          <button
            onClick={() => setActiveTab('record')}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'record'
                ? 'bg-white dark:bg-slate-800 text-teal-600 dark:text-teal-400 shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
          >
            <Mic className="w-4 h-4" /> Record Browser Mic
          </button>
        </div>
      )}

      {/* Processing Live Overlay */}
      {isSubmitting && currentJob && (
        <div className="p-8 rounded-2xl border border-teal-500/30 bg-white dark:bg-slate-900 text-center space-y-6 animate-fade-in shadow-xl">
          <div className="w-16 h-16 mx-auto rounded-full bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-500 animate-spin">
            <Activity className="w-8 h-8" />
          </div>

          <div className="space-y-1">
            <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
              Processing Meeting on Local AI Pipeline
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Executing NVIDIA Parakeet STT, PyAnnote diarization, and Ollama Qwen3 extraction.
            </p>
          </div>

          <div className="max-w-md mx-auto space-y-2">
            <ProgressBar
              progress={currentJob.progress}
              label={currentJob.step}
              sublabel={`${currentJob.progress}%`}
            />
          </div>

          <p className="text-[11px] text-slate-400 italic">
            All AI computation is running securely on your local GPU/CPU. No cloud data transfer.
          </p>
        </div>
      )}

      {/* Main Tab Content */}
      {!isSubmitting && (
        <div className="pt-2">
          {activeTab === 'upload' ? (
            <FileUploader onUploadSubmit={handleUploadSubmit} isSubmitting={isSubmitting} />
          ) : (
            <AudioRecorder
              onRecordingComplete={(file, title) => handleUploadSubmit(file, title)}
              isSubmitting={isSubmitting}
            />
          )}
        </div>
      )}
    </div>
  );
}
