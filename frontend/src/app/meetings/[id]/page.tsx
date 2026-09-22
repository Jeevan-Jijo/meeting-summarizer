'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft, 
  Play, 
  Pause, 
  Volume2, 
  RefreshCw, 
  Trash2, 
  Bot, 
  FileText, 
  FileSpreadsheet, 
  Download, 
  Calendar, 
  Clock, 
  User, 
  CheckSquare, 
  Gavel, 
  Lightbulb, 
  HelpCircle, 
  BarChart3, 
  FileCheck2, 
  Sparkles,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { api } from '@/lib/api';
import { MeetingDetail, ProcessingJob, Speaker } from '@/lib/types';
import { formatSecondsToTime, getStatusBadgeColor } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { ProgressBar } from '@/components/ui/ProgressBar';

import { TranscriptView } from '@/components/meetings/TranscriptView';
import { ExtractionsList } from '@/components/meetings/ExtractionsList';
import { MinutesView } from '@/components/meetings/MinutesView';
import { AnalyticsCharts } from '@/components/meetings/AnalyticsCharts';
import { ChatPane } from '@/components/meetings/ChatPane';

const TABS = [
  { id: 'overview', label: 'Overview', icon: Sparkles },
  { id: 'transcript', label: 'Transcript', icon: FileText },
  { id: 'key_points', label: 'Key Points', icon: Lightbulb },
  { id: 'decisions', label: 'Decisions', icon: Gavel },
  { id: 'action_items', label: 'Action Items', icon: CheckSquare },
  { id: 'dates', label: 'Dates & Schedule', icon: Calendar },
  { id: 'takeaways', label: 'Takeaways', icon: Lightbulb },
  { id: 'questions', label: 'Questions', icon: HelpCircle },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'minutes', label: 'Minutes (MoM)', icon: FileCheck2 },
];

export default function MeetingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const meetingId = Number(params?.id);

  const [meeting, setMeeting] = useState<MeetingDetail | null>(null);
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [showChat, setShowChat] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeJob, setActiveJob] = useState<ProcessingJob | null>(null);

  // Audio Player State
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);

  useEffect(() => {
    if (meetingId) {
      loadMeeting();
    }
  }, [meetingId]);

  // Poll job if not completed
  useEffect(() => {
    if (meeting && meeting.status !== 'COMPLETED' && meeting.status !== 'FAILED') {
      const interval = setInterval(async () => {
        try {
          const job = await api.getLatestJobForMeeting(meetingId);
          setActiveJob(job);
          if (job?.status === 'COMPLETED') {
            loadMeeting();
          }
        } catch (err) {
          // ignore
        }
      }, 2500);
      return () => clearInterval(interval);
    }
  }, [meeting?.status, meetingId]);

  const loadMeeting = async () => {
    try {
      setIsLoading(true);
      const data = await api.getMeeting(meetingId);
      setMeeting(data);
      setDuration(data.duration_seconds || 0);

      const latestJob = await api.getLatestJobForMeeting(meetingId);
      setActiveJob(latestJob);
    } catch (err: any) {
      console.error('Failed to load meeting:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSeek = (seconds: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = seconds;
      setCurrentTime(seconds);
      if (!isPlaying) {
        audioRef.current.play().catch(() => {});
        setIsPlaying(true);
      }
    }
  };

  const togglePlayPause = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
  };

  const handleSpeakerRenamed = (updatedSpeaker: Speaker) => {
    if (!meeting) return;
    const updatedSpeakers = meeting.speakers.map((s) =>
      s.id === updatedSpeaker.id ? updatedSpeaker : s
    );
    const updatedSegments = meeting.transcript_segments.map((seg) =>
      seg.speaker_id === updatedSpeaker.id
        ? { ...seg, speaker_label: updatedSpeaker.display_name }
        : seg
    );
    setMeeting({
      ...meeting,
      speakers: updatedSpeakers,
      transcript_segments: updatedSegments,
    });
  };

  const handleDeleteMeeting = async () => {
    if (!confirm('Are you sure you want to delete this meeting?')) return;
    try {
      await api.deleteMeeting(meetingId);
      router.push('/meetings');
    } catch (err: any) {
      alert(`Delete error: ${err.message}`);
    }
  };

  const handleReprocess = async () => {
    try {
      await api.reprocessMeeting(meetingId);
      loadMeeting();
    } catch (err: any) {
      alert(`Reprocess error: ${err.message}`);
    }
  };

  if (isLoading && !meeting) {
    return (
      <div className="py-24 text-center flex flex-col items-center justify-center gap-3 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-teal-500" />
        <span className="text-sm">Loading meeting details...</span>
      </div>
    );
  }

  if (!meeting) {
    return (
      <div className="text-center py-20 space-y-4">
        <p className="text-sm text-slate-500">Meeting not found or deleted.</p>
        <Link href="/meetings">
          <Button variant="outline">Return to Meetings</Button>
        </Link>
      </div>
    );
  }

  const badge = getStatusBadgeColor(meeting.status);
  const audioUrl = api.getAudioUrl(meeting.id);

  return (
    <div className="space-y-6 max-w-7xl mx-auto animate-fade-in pb-12">
      {/* Hidden HTML5 Audio Element for synchronization */}
      <audio
        ref={audioRef}
        src={audioUrl}
        onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
        onLoadedMetadata={(e) => setDuration(e.currentTarget.duration || meeting.duration_seconds)}
        onEnded={() => setIsPlaying(false)}
        preload="metadata"
      />

      {/* Breadcrumb & Quick Actions */}
      <div className="flex items-center justify-between gap-4">
        <Link href="/meetings" className="text-xs text-slate-500 hover:text-teal-500 transition flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Meetings
        </Link>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleReprocess} title="Reprocess Pipeline">
            <RefreshCw className="w-3.5 h-3.5" /> Reprocess
          </Button>
          <Button variant="danger" size="sm" onClick={handleDeleteMeeting} title="Delete Meeting">
            <Trash2 className="w-3.5 h-3.5" /> Delete
          </Button>
        </div>
      </div>

      {/* Meeting Header Card */}
      <div className="p-6 rounded-2xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/50 backdrop-blur-md shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
                {meeting.title}
              </h1>
              <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badge.bg} ${badge.text}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`} />
                {meeting.status}
              </span>
            </div>
            {meeting.description && (
              <p className="text-xs text-slate-500 dark:text-slate-400">{meeting.description}</p>
            )}
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
            <span className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              {new Date(meeting.meeting_date).toLocaleDateString()}
            </span>
            <span>•</span>
            <span className="flex items-center gap-1 font-mono">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              {formatSecondsToTime(meeting.duration_seconds)}
            </span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <User className="w-3.5 h-3.5 text-slate-400" />
              {meeting.speakers.length} Speaker{meeting.speakers.length === 1 ? '' : 's'}
            </span>
          </div>
        </div>

        {/* Audio Player Bar */}
        <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/50 dark:border-slate-700/50 flex items-center gap-4">
          <button
            onClick={togglePlayPause}
            className="w-10 h-10 rounded-full bg-teal-500 hover:bg-teal-600 text-white flex items-center justify-center shadow-md transition shrink-0"
          >
            {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current pl-0.5" />}
          </button>

          <div className="flex-1 space-y-1">
            <input
              type="range"
              min="0"
              max={duration || 100}
              step="0.1"
              value={currentTime}
              onChange={(e) => handleSeek(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-teal-500"
            />
            <div className="flex justify-between text-[11px] font-mono text-slate-500 dark:text-slate-400">
              <span>{formatSecondsToTime(currentTime)}</span>
              <span>{formatSecondsToTime(duration)}</span>
            </div>
          </div>
        </div>

        {/* Live Processing Indicator if still running */}
        {meeting.status !== 'COMPLETED' && meeting.status !== 'FAILED' && activeJob && (
          <div className="p-3.5 rounded-xl border border-teal-500/30 bg-teal-500/10 space-y-2 animate-pulse-fast">
            <div className="flex justify-between text-xs font-semibold text-teal-800 dark:text-teal-200">
              <span>Running Stage: {activeJob.current_step}</span>
              <span>{activeJob.progress_percent}%</span>
            </div>
            <ProgressBar progress={activeJob.progress_percent} />
          </div>
        )}

        {/* Failure Banner with Retry Action */}
        {meeting.status === 'FAILED' && (
          <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-semibold text-rose-800 dark:text-rose-200">Processing Failed</h4>
                <p className="text-xs text-rose-600 dark:text-rose-400 mt-0.5">
                  {activeJob?.error_message || "An error occurred during audio processing."}
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleReprocess}
              className="border-rose-300 dark:border-rose-800 hover:bg-rose-500/20 text-rose-700 dark:text-rose-300 shrink-0"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1" /> Retry Processing
            </Button>
          </div>
        )}
      </div>

      {/* 10 Navigation Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-slate-200 dark:border-slate-800">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-500/30 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Main Grid: Tabs Content + Chat Pane Side Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left / Center: Tab Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* TAB 1: OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Executive Summary */}
              <Card className="space-y-3">
                <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-teal-500" /> Executive Summary
                </h2>
                <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                  {meeting.summary?.executive_summary || 'Analysis in progress or not available.'}
                </p>
              </Card>

              {/* Quick Highlights Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Key Decisions */}
                <Card className="space-y-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                    <Gavel className="w-3.5 h-3.5 text-indigo-500" /> Top Decisions ({meeting.decisions.length})
                  </h3>
                  {meeting.decisions.slice(0, 3).map((dec) => (
                    <div key={dec.id} className="text-xs p-2 rounded-lg bg-slate-50 dark:bg-slate-800/40">
                      <p className="font-semibold text-slate-800 dark:text-slate-200">• {dec.decision}</p>
                    </div>
                  ))}
                  {meeting.decisions.length === 0 && (
                    <p className="text-xs text-slate-400">No decisions recorded.</p>
                  )}
                </Card>

                {/* Urgent Action Items */}
                <Card className="space-y-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                    <CheckSquare className="w-3.5 h-3.5 text-teal-500" /> Pending Actions ({meeting.action_items.filter(a => !a.is_completed).length})
                  </h3>
                  {meeting.action_items.slice(0, 3).map((item) => (
                    <div key={item.id} className="text-xs p-2 rounded-lg bg-slate-50 dark:bg-slate-800/40 space-y-1">
                      <p className="font-medium text-slate-800 dark:text-slate-200 truncate">{item.description}</p>
                      <span className="text-[11px] text-slate-400">Assignee: {item.assignee} ({item.priority})</span>
                    </div>
                  ))}
                  {meeting.action_items.length === 0 && (
                    <p className="text-xs text-slate-400">No action items recorded.</p>
                  )}
                </Card>
              </div>
            </div>
          )}

          {/* TAB 2: TRANSCRIPT */}
          {activeTab === 'transcript' && (
            <TranscriptView
              meetingId={meeting.id}
              segments={meeting.transcript_segments}
              speakers={meeting.speakers}
              currentTime={currentTime}
              onSeek={handleSeek}
              onSpeakerRenamed={handleSpeakerRenamed}
            />
          )}

          {/* TAB 3: KEY POINTS */}
          {activeTab === 'key_points' && (
            <ExtractionsList
              meetingId={meeting.id}
              type="key_points"
              keyPoints={meeting.key_points}
              onSeek={handleSeek}
              onRefresh={loadMeeting}
            />
          )}

          {/* TAB 4: DECISIONS */}
          {activeTab === 'decisions' && (
            <ExtractionsList
              meetingId={meeting.id}
              type="decisions"
              decisions={meeting.decisions}
              onSeek={handleSeek}
              onRefresh={loadMeeting}
            />
          )}

          {/* TAB 5: ACTION ITEMS */}
          {activeTab === 'action_items' && (
            <ExtractionsList
              meetingId={meeting.id}
              type="action_items"
              actionItems={meeting.action_items}
              onSeek={handleSeek}
              onRefresh={loadMeeting}
            />
          )}

          {/* TAB 6: DATES & SCHEDULE */}
          {activeTab === 'dates' && (
            <ExtractionsList
              meetingId={meeting.id}
              type="dates"
              importantDates={meeting.important_dates}
              scheduledEvents={meeting.scheduled_events}
              onSeek={handleSeek}
              onRefresh={loadMeeting}
            />
          )}

          {/* TAB 7: TAKEAWAYS */}
          {activeTab === 'takeaways' && (
            <ExtractionsList
              meetingId={meeting.id}
              type="takeaways"
              takeaways={meeting.takeaways}
              onSeek={handleSeek}
              onRefresh={loadMeeting}
            />
          )}

          {/* TAB 8: QUESTIONS */}
          {activeTab === 'questions' && (
            <ExtractionsList
              meetingId={meeting.id}
              type="questions"
              questions={meeting.unresolved_questions}
              onSeek={handleSeek}
              onRefresh={loadMeeting}
            />
          )}

          {/* TAB 9: ANALYTICS */}
          {activeTab === 'analytics' && (
            <AnalyticsCharts
              speakers={meeting.speakers}
              durationSeconds={meeting.duration_seconds}
              summary={meeting.summary}
            />
          )}

          {/* TAB 10: MINUTES */}
          {activeTab === 'minutes' && <MinutesView meeting={meeting} />}
        </div>

        {/* Right: RAG Chat Assistant */}
        <div className="lg:col-span-1 space-y-4 sticky top-20">
          <ChatPane
            meetingId={meeting.id}
            meetingTitle={meeting.title}
            onSeek={handleSeek}
          />
        </div>
      </div>
    </div>
  );
}
