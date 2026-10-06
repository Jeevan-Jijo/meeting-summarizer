'use client';

import React, { useState } from 'react';
import { 
  CheckSquare, 
  Square, 
  Calendar, 
  HelpCircle, 
  Lightbulb, 
  Gavel, 
  Trash2, 
  Play, 
  AlertTriangle,
  Clock,
  User,
  Quote,
  CheckCircle2,
  CalendarCheck2
} from 'lucide-react';
import { 
  ActionItem, Decision, KeyPoint, ImportantDate, 
  ScheduledEvent, Takeaway, UnresolvedQuestion 
} from '@/lib/types';
import { formatSecondsToTime, getPriorityColor, cn } from '@/lib/utils';
import { api } from '@/lib/api';

interface ExtractionsListProps {
  meetingId: number;
  type: 'action_items' | 'decisions' | 'key_points' | 'dates' | 'questions' | 'takeaways';
  actionItems?: ActionItem[];
  decisions?: Decision[];
  keyPoints?: KeyPoint[];
  importantDates?: ImportantDate[];
  scheduledEvents?: ScheduledEvent[];
  questions?: UnresolvedQuestion[];
  takeaways?: Takeaway[];
  onSeek: (seconds: number) => void;
  onRefresh: () => void;
}

export const ExtractionsList: React.FC<ExtractionsListProps> = ({
  meetingId,
  type,
  actionItems = [],
  decisions = [],
  keyPoints = [],
  importantDates = [],
  scheduledEvents = [],
  questions = [],
  takeaways = [],
  onSeek,
  onRefresh,
}) => {
  const [editingId, setEditingId] = useState<number | null>(null);

  // Toggle Action Item completion
  const handleToggleActionItem = async (item: ActionItem) => {
    try {
      await api.updateActionItem(meetingId, item.id, { is_completed: !item.is_completed });
      onRefresh();
    } catch (err: any) {
      alert(`Failed to update action item: ${err.message}`);
    }
  };

  const handleDeleteItem = async (id: number) => {
    if (!confirm('Are you sure you want to delete this item?')) return;
    try {
      if (type === 'action_items') await api.deleteActionItem(meetingId, id);
      else if (type === 'decisions') await api.deleteDecision(meetingId, id);
      else if (type === 'key_points') await api.deleteKeyPoint(meetingId, id);
      else if (type === 'dates') await api.deleteImportantDate(meetingId, id);
      else if (type === 'questions') await api.deleteQuestion(meetingId, id);
      else if (type === 'takeaways') await api.deleteTakeaway(meetingId, id);
      onRefresh();
    } catch (err: any) {
      alert(`Delete error: ${err.message}`);
    }
  };

  // --- ACTION ITEMS RENDER ---
  if (type === 'action_items') {
    return (
      <div className="space-y-3">
        {actionItems.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">No actionable tasks were identified.</div>
        ) : (
          actionItems.map((item) => (
            <div
              key={item.id}
              className={cn(
                'p-4 rounded-xl border transition-all',
                item.is_completed
                  ? 'bg-slate-50/50 dark:bg-slate-900/20 border-slate-200 dark:border-slate-800 opacity-70'
                  : 'bg-white dark:bg-slate-900/50 border-slate-200/80 dark:border-slate-800/80 hover:border-teal-500/30 shadow-xs'
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1">
                  <button
                    onClick={() => handleToggleActionItem(item)}
                    className="mt-0.5 text-slate-400 hover:text-teal-500 transition"
                  >
                    {item.is_completed ? (
                      <CheckSquare className="w-5 h-5 text-teal-500" />
                    ) : (
                      <Square className="w-5 h-5" />
                    )}
                  </button>

                  <div className="space-y-1.5 flex-1">
                    <p className={cn('text-sm font-medium text-slate-900 dark:text-slate-100', item.is_completed && 'line-through text-slate-400')}>
                      {item.description}
                    </p>

                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      {/* Assignee */}
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium">
                        <User className="w-3 h-3 text-slate-400" /> {item.assignee || 'Unassigned'}
                      </span>

                      {/* Domain */}
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-teal-500/10 text-teal-400 border border-teal-500/20 font-medium text-[11px]">
                        {item.domain || 'Other'}
                      </span>

                      {/* Deadline */}
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        <Clock className="w-3 h-3 text-slate-400" /> {item.deadline || 'Not specified'}
                      </span>

                      {/* Priority */}
                      <span className={cn('px-2 py-0.5 rounded border text-[11px] font-semibold', getPriorityColor(item.priority))}>
                        {item.priority} Priority
                      </span>

                      {/* Status */}
                      <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[11px] font-semibold">
                        {item.status || (item.is_completed ? 'Completed' : 'Pending')}
                      </span>

                      {/* Timestamp link */}
                      {item.start_time !== undefined && item.start_time !== null && (
                        <button
                          onClick={() => onSeek(item.start_time || 0)}
                          className="inline-flex items-center gap-1 font-mono text-[11px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 hover:bg-teal-500 hover:text-white text-slate-500 dark:text-slate-400 transition"
                        >
                          <Play className="w-2.5 h-2.5 fill-current" />
                          {formatSecondsToTime(item.start_time)}
                        </button>
                      )}
                    </div>

                    {/* Source Evidence */}
                    {item.source_text && (
                      <div className="mt-2 p-2 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200/50 dark:border-slate-700/50 text-xs text-slate-600 dark:text-slate-300 flex items-start gap-1.5">
                        <Quote className="w-3.5 h-3.5 text-teal-500 shrink-0 mt-0.5" />
                        <span className="italic">"{item.source_text}"</span>
                      </div>
                    )}
                  </div>
                </div>

                <button
                  onClick={() => handleDeleteItem(item.id)}
                  className="text-slate-400 hover:text-rose-500 p-1 rounded transition"
                  title="Delete action item"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    );
  }

  // --- DECISIONS RENDER ---
  if (type === 'decisions') {
    return (
      <div className="space-y-4">
        {decisions.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">No explicit decisions were identified.</div>
        ) : (
          decisions.map((dec) => (
            <div
              key={dec.id}
              className="p-5 rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/50 shadow-xs space-y-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1">
                  <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-500 flex items-center justify-center shrink-0">
                    <Gavel className="w-4 h-4" />
                  </div>
                  <div className="space-y-1 flex-1">
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{dec.decision}</h4>
                    {dec.made_by && (
                      <p className="text-xs text-slate-500"><span className="font-medium text-slate-700 dark:text-slate-300">Made By:</span> {dec.made_by}</p>
                    )}
                    {dec.context && (
                      <p className="text-xs text-slate-600 dark:text-slate-300"><span className="font-medium text-slate-700 dark:text-slate-200">Context:</span> {dec.context}</p>
                    )}
                    {dec.impact && (
                      <p className="text-xs text-slate-600 dark:text-slate-300"><span className="font-medium text-slate-700 dark:text-slate-200">Impact:</span> {dec.impact}</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {dec.start_time !== undefined && dec.start_time !== null && (
                    <button
                      onClick={() => onSeek(dec.start_time || 0)}
                      className="inline-flex items-center gap-1 font-mono text-xs px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-teal-500 hover:text-white text-slate-600 dark:text-slate-300 transition"
                    >
                      <Play className="w-3 h-3 fill-current" />
                      {formatSecondsToTime(dec.start_time)}
                    </button>
                  )}
                  <button
                    onClick={() => handleDeleteItem(dec.id)}
                    className="text-slate-400 hover:text-rose-500 p-1 rounded transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {dec.source_text && (
                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200/50 dark:border-slate-700/50 text-xs text-slate-600 dark:text-slate-300 flex items-start gap-1.5">
                  <Quote className="w-3.5 h-3.5 text-indigo-500 shrink-0 mt-0.5" />
                  <span className="italic">"{dec.source_text}"</span>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    );
  }

  // --- DATES & SCHEDULES RENDER ---
  if (type === 'dates') {
    return (
      <div className="space-y-6">
        {/* Important Dates */}
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2">
            <Calendar className="w-4 h-4 text-teal-500" /> Stated Dates & Deadlines
          </h3>
          {importantDates.length === 0 ? (
            <div className="p-6 text-center text-slate-400 text-xs border border-dashed rounded-xl border-slate-200 dark:border-slate-800">
              No specific date milestones extracted.
            </div>
          ) : (
            importantDates.map((dt) => (
              <div
                key={dt.id}
                className="p-4 rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/50 flex items-start justify-between gap-3"
              >
                <div className="space-y-1 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-slate-900 dark:text-slate-100 font-mono">
                      {dt.raw_phrase}
                    </span>
                    {dt.normalized_date && (
                      <span className="text-xs px-2 py-0.5 rounded bg-teal-500/10 text-teal-400 border border-teal-500/20 font-mono">
                        {dt.normalized_date}
                      </span>
                    )}
                    {dt.needs_confirmation && (
                      <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20 font-medium">
                        <AlertTriangle className="w-3 h-3" /> Needs Confirmation
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-300">{dt.description}</p>
                </div>

                <div className="flex items-center gap-2">
                  {dt.start_time !== undefined && dt.start_time !== null && (
                    <button
                      onClick={() => onSeek(dt.start_time || 0)}
                      className="inline-flex items-center gap-1 font-mono text-xs px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-teal-500 hover:text-white text-slate-600 dark:text-slate-300 transition"
                    >
                      <Play className="w-3 h-3 fill-current" />
                      {formatSecondsToTime(dt.start_time)}
                    </button>
                  )}
                  <button onClick={() => handleDeleteItem(dt.id)} className="text-slate-400 hover:text-rose-500 p-1">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Scheduled Events */}
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2">
            <CalendarCheck2 className="w-4 h-4 text-indigo-500" /> Scheduled Follow-up Events
          </h3>
          {scheduledEvents.length === 0 ? (
            <div className="p-6 text-center text-slate-400 text-xs border border-dashed rounded-xl border-slate-200 dark:border-slate-800">
              No follow-up meetings or events scheduled.
            </div>
          ) : (
            scheduledEvents.map((ev) => (
              <div
                key={ev.id}
                className="p-4 rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/50 flex items-start justify-between gap-3"
              >
                <div className="space-y-1">
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{ev.event_title}</h4>
                  <p className="text-xs text-slate-500 font-mono">Date / Time: {ev.date_phrase}</p>
                  {ev.participants && ev.participants.length > 0 && (
                    <p className="text-xs text-slate-600 dark:text-slate-300">
                      Participants: {ev.participants.join(', ')}
                    </p>
                  )}
                </div>
                {ev.start_time !== undefined && ev.start_time !== null && (
                  <button
                    onClick={() => onSeek(ev.start_time || 0)}
                    className="inline-flex items-center gap-1 font-mono text-xs px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-teal-500 hover:text-white text-slate-600 dark:text-slate-300 transition"
                  >
                    <Play className="w-3 h-3 fill-current" />
                    {formatSecondsToTime(ev.start_time)}
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    );
  }

  // --- KEY POINTS RENDER ---
  if (type === 'key_points') {
    return (
      <div className="space-y-3">
        {keyPoints.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">No key points recorded.</div>
        ) : (
          keyPoints.map((kp) => (
            <div
              key={kp.id}
              className="p-4 rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/50 flex items-start justify-between gap-3"
            >
              <div className="space-y-1 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-semibold uppercase px-2 py-0.5 rounded bg-teal-500/10 text-teal-400 border border-teal-500/20">
                    {kp.category || 'General'}
                  </span>
                </div>
                <p className="text-sm text-slate-900 dark:text-slate-100">{kp.point}</p>
              </div>

              <div className="flex items-center gap-2">
                {kp.start_time !== undefined && kp.start_time !== null && (
                  <button
                    onClick={() => onSeek(kp.start_time || 0)}
                    className="inline-flex items-center gap-1 font-mono text-xs px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-teal-500 hover:text-white text-slate-600 dark:text-slate-300 transition"
                  >
                    <Play className="w-3 h-3 fill-current" />
                    {formatSecondsToTime(kp.start_time)}
                  </button>
                )}
                <button onClick={() => handleDeleteItem(kp.id)} className="text-slate-400 hover:text-rose-500 p-1">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    );
  }

  // --- UNRESOLVED QUESTIONS RENDER ---
  if (type === 'questions') {
    return (
      <div className="space-y-3">
        {questions.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">No unanswered questions were identified.</div>
        ) : (
          questions.map((q) => (
            <div
              key={q.id}
              className="p-4 rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/50 space-y-2.5"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2.5 flex-1">
                  <HelpCircle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                  <div className="space-y-1.5 flex-1">
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{q.question}</h4>
                    
                    {/* Answer section */}
                    <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60 text-xs text-slate-700 dark:text-slate-300">
                      <span className="font-semibold text-teal-600 dark:text-teal-400 block mb-0.5">Answer:</span>
                      {q.answer || 'No answer was identified in the meeting.'}
                    </div>

                    <div className="flex items-center gap-2 text-xs pt-0.5">
                      <span className="text-slate-500">Raised by: <strong className="text-slate-700 dark:text-slate-300">{q.raised_by || 'Speaker 00'}</strong></span>
                      <span className={cn(
                        'px-2 py-0.5 rounded border text-[11px] font-semibold',
                        q.status === 'Answered' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                      )}>
                        {q.status || 'Unanswered'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {q.start_time !== undefined && q.start_time !== null && (
                    <button
                      onClick={() => onSeek(q.start_time || 0)}
                      className="inline-flex items-center gap-1 font-mono text-xs px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-teal-500 hover:text-white text-slate-600 dark:text-slate-300 transition"
                    >
                      <Play className="w-3 h-3 fill-current" />
                      {formatSecondsToTime(q.start_time)}
                    </button>
                  )}
                  <button onClick={() => handleDeleteItem(q.id)} className="text-slate-400 hover:text-rose-500 p-1">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    );
  }

  // --- TAKEAWAYS RENDER ---
  if (type === 'takeaways') {
    return (
      <div className="space-y-3">
        {takeaways.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">No takeaways recorded.</div>
        ) : (
          takeaways.map((t) => (
            <div
              key={t.id}
              className="p-4 rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/50 flex items-start justify-between gap-3"
            >
              <div className="flex items-start gap-3 flex-1">
                <Lightbulb className="w-5 h-5 text-teal-500 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <span className="text-[11px] font-semibold uppercase px-2 py-0.5 rounded bg-teal-500/10 text-teal-400 border border-teal-500/20">
                    {t.category || 'Strategic'}
                  </span>
                  <p className="text-sm text-slate-900 dark:text-slate-100">{t.takeaway}</p>
                </div>
              </div>

              <button onClick={() => handleDeleteItem(t.id)} className="text-slate-400 hover:text-rose-500 p-1">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))
        )}
      </div>
    );
  }

  return null;
};
