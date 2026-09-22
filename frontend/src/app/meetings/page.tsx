'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { 
  Search, 
  Filter, 
  Plus, 
  FolderKanban, 
  Calendar, 
  Clock, 
  User, 
  CheckSquare, 
  Trash2, 
  RefreshCw, 
  ArrowRight,
  Loader2
} from 'lucide-react';
import { api } from '@/lib/api';
import { MeetingListItem, ProcessingState } from '@/lib/types';
import { formatSecondsToTime, getStatusBadgeColor } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';

const STATUS_FILTERS = [
  'ALL',
  'COMPLETED',
  'TRANSCRIBING',
  'DIARIZING',
  'ANALYZING',
  'QUEUED',
  'FAILED',
];

export default function MeetingsListPage() {
  const [meetings, setMeetings] = useState<MeetingListItem[]>([]);
  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    loadMeetings();
  }, [search, statusFilter]);

  const loadMeetings = async () => {
    try {
      setIsLoading(true);
      const data = await api.listMeetings(search || undefined, statusFilter);
      setMeetings(data);
    } catch (err) {
      console.error('Failed to load meetings:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteMeeting = async (id: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this meeting and its local audio/data?')) return;
    try {
      await api.deleteMeeting(id);
      loadMeetings();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleReprocessMeeting = async (id: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await api.reprocessMeeting(id);
      alert('Reprocessing initiated in background.');
      loadMeetings();
    } catch (err: any) {
      alert(`Reprocess failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
            Meetings Library
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Browse, search, and manage all your processed meeting recordings.
          </p>
        </div>

        <Link href="/meetings/new">
          <Button variant="primary">
            <Plus className="w-4 h-4" /> New Meeting
          </Button>
        </Link>
      </div>

      {/* Filter / Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between p-4 rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/50">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search meetings by title or description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 rounded-lg text-sm bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
        </div>

        {/* Status Pills */}
        <div className="flex flex-wrap gap-1.5 items-center">
          {STATUS_FILTERS.map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`text-xs px-2.5 py-1 rounded-lg font-medium transition ${
                statusFilter === st
                  ? 'bg-teal-600 text-white'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Meeting Cards List */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="py-20 text-center flex flex-col items-center justify-center gap-2 text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin text-teal-500" />
            <span className="text-xs">Loading meetings...</span>
          </div>
        ) : meetings.length === 0 ? (
          <Card className="text-center py-16 space-y-3">
            <FolderKanban className="w-12 h-12 mx-auto text-slate-400" />
            <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200">
              No meetings found
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {search || statusFilter !== 'ALL'
                ? 'Try adjusting your search terms or filters.'
                : 'Upload or record a meeting to get started with local transcription and analysis.'}
            </p>
            <Link href="/meetings/new" className="inline-block pt-2">
              <Button variant="primary" size="sm">
                <Plus className="w-4 h-4" /> Create New Meeting
              </Button>
            </Link>
          </Card>
        ) : (
          meetings.map((m) => {
            const badge = getStatusBadgeColor(m.status);
            return (
              <Link key={m.id} href={`/meetings/${m.id}`}>
                <Card hover className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 group">
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition">
                        {m.title}
                      </h3>
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${badge.bg} ${badge.text}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`} />
                        {m.status}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        {new Date(m.meeting_date).toLocaleDateString()}
                      </span>
                      <span className="flex items-center gap-1 font-mono">
                        <Clock className="w-3.5 h-3.5 text-slate-400" />
                        {formatSecondsToTime(m.duration_seconds)}
                      </span>
                      <span className="flex items-center gap-1">
                        <User className="w-3.5 h-3.5 text-slate-400" />
                        {m.speaker_count} Speaker{m.speaker_count === 1 ? '' : 's'}
                      </span>
                      <span className="flex items-center gap-1">
                        <CheckSquare className="w-3.5 h-3.5 text-slate-400" />
                        {m.action_item_count} Action Item{m.action_item_count === 1 ? '' : 's'}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={(e) => handleReprocessMeeting(m.id, e)}
                      className="p-2 text-slate-400 hover:text-teal-500 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                      title="Reprocess Pipeline"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => handleDeleteMeeting(m.id, e)}
                      className="p-2 text-slate-400 hover:text-rose-500 rounded-lg hover:bg-rose-500/10 transition"
                      title="Delete Meeting"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    <div className="p-2 text-slate-400 group-hover:text-teal-500 group-hover:translate-x-0.5 transition">
                      <ArrowRight className="w-4 h-4" />
                    </div>
                  </div>
                </Card>
              </Link>
            );
          })
        )}
      </div>
    </div>
  );
}
