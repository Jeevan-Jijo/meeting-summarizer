'use client';

import React, { useState } from 'react';
import { Search, Play, Edit2, User, Copy, Check } from 'lucide-react';
import { TranscriptSegment, Speaker } from '@/lib/types';
import { formatSecondsToTime, cn } from '@/lib/utils';
import { SpeakerRenameModal } from './SpeakerRenameModal';

interface TranscriptViewProps {
  meetingId: number;
  segments: TranscriptSegment[];
  speakers: Speaker[];
  currentTime: number;
  onSeek: (seconds: number) => void;
  onSpeakerRenamed: (speaker: Speaker) => void;
}

const SPEAKER_COLORS = [
  'bg-teal-500/10 text-teal-400 border-teal-500/20',
  'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
  'bg-amber-500/10 text-amber-400 border-amber-500/20',
  'bg-purple-500/10 text-purple-400 border-purple-500/20',
  'bg-rose-500/10 text-rose-400 border-rose-500/20',
];

export const TranscriptView: React.FC<TranscriptViewProps> = ({
  meetingId,
  segments,
  speakers,
  currentTime,
  onSeek,
  onSpeakerRenamed,
}) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [editingSpeaker, setEditingSpeaker] = useState<Speaker | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const filteredSegments = segments.filter((seg) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      seg.cleaned_text.toLowerCase().includes(q) ||
      seg.speaker_label.toLowerCase().includes(q)
    );
  });

  const getSpeakerColor = (label: string) => {
    let hash = 0;
    for (let i = 0; i < label.length; i++) {
      hash = label.charCodeAt(i) + ((hash << 5) - hash);
    }
    const idx = Math.abs(hash) % SPEAKER_COLORS.length;
    return SPEAKER_COLORS[idx];
  };

  const handleCopyText = (id: number, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="space-y-4">
      {/* Search & Filter Bar */}
      <div className="flex items-center justify-between gap-4 p-3 rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search transcript segments or speakers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 rounded-lg text-sm bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
        </div>
        <div className="text-xs text-slate-500 dark:text-slate-400">
          Showing {filteredSegments.length} of {segments.length} segments
        </div>
      </div>

      {/* Segments List */}
      <div className="space-y-3">
        {filteredSegments.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            No matching transcript segments found.
          </div>
        ) : (
          filteredSegments.map((seg) => {
            const isActive = currentTime >= seg.start_time && currentTime <= seg.end_time;
            const speakerObj = speakers.find((s) => s.id === seg.speaker_id) || null;

            return (
              <div
                key={seg.id}
                id={`seg-${seg.id}`}
                className={cn(
                  'p-4 rounded-xl border transition-all text-sm group',
                  isActive
                    ? 'border-teal-500/60 bg-teal-500/5 dark:bg-teal-950/20 shadow-sm'
                    : 'border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/40 hover:border-slate-300 dark:hover:border-slate-700'
                )}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {/* Timestamp button (click to seek) */}
                    <button
                      onClick={() => onSeek(seg.start_time)}
                      className="inline-flex items-center gap-1 font-mono text-xs px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-teal-500 hover:text-white dark:hover:bg-teal-500 text-slate-600 dark:text-slate-300 transition"
                      title="Click to jump to this timestamp in recording"
                    >
                      <Play className="w-3 h-3 fill-current" />
                      {formatSecondsToTime(seg.start_time)}
                    </button>

                    {/* Speaker Badge */}
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border',
                        getSpeakerColor(seg.speaker_label)
                      )}
                    >
                      <User className="w-3 h-3" />
                      {seg.speaker_label}
                    </span>

                    {/* Edit speaker name quick button */}
                    {speakerObj && (
                      <button
                        onClick={() => setEditingSpeaker(speakerObj)}
                        className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-teal-400 p-1 rounded transition"
                        title={`Rename ${seg.speaker_label}`}
                      >
                        <Edit2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-slate-400 font-mono">
                      {formatSecondsToTime(seg.end_time)}
                    </span>
                    <button
                      onClick={() => handleCopyText(seg.id, seg.cleaned_text)}
                      className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-slate-200 p-1 rounded transition"
                      title="Copy segment text"
                    >
                      {copiedId === seg.id ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                <p className="text-slate-800 dark:text-slate-200 leading-relaxed pl-1">
                  {seg.cleaned_text}
                </p>
              </div>
            );
          })
        )}
      </div>

      {/* Speaker Rename Modal */}
      <SpeakerRenameModal
        isOpen={!!editingSpeaker}
        onClose={() => setEditingSpeaker(null)}
        meetingId={meetingId}
        speaker={editingSpeaker}
        onSpeakerUpdated={onSpeakerRenamed}
      />
    </div>
  );
};
