'use client';

import React from 'react';
import { Download, FileText, FileCode, FileSpreadsheet, Printer, Copy, Check } from 'lucide-react';
import { MeetingDetail } from '@/lib/types';
import { formatSecondsToTime } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';

interface MinutesViewProps {
  meeting: MeetingDetail;
}

export const MinutesView: React.FC<MinutesViewProps> = ({ meeting }) => {
  const [copied, setCopied] = React.useState<boolean>(false);

  const handleDownload = (format: 'markdown' | 'json' | 'pdf') => {
    let url = '';
    if (format === 'markdown') url = api.getExportMarkdownUrl(meeting.id);
    else if (format === 'json') url = api.getExportJsonUrl(meeting.id);
    else if (format === 'pdf') url = api.getExportPdfUrl(meeting.id);

    window.open(url, '_blank');
  };

  const participants = meeting.speakers.map((s) => s.display_name).join(', ') || 'Participants';

  return (
    <div className="space-y-6">
      {/* Top Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/50">
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Export Official Minutes of Meeting (MoM)
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Download polished minutes formatted for documentation or team sharing.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => handleDownload('markdown')}>
            <FileText className="w-4 h-4 text-teal-500" /> Export Markdown
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleDownload('json')}>
            <FileCode className="w-4 h-4 text-indigo-500" /> Export JSON
          </Button>
          <Button variant="primary" size="sm" onClick={() => handleDownload('pdf')}>
            <Download className="w-4 h-4" /> Download PDF
          </Button>
        </div>
      </div>

      {/* Styled Document Preview */}
      <div className="p-8 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm max-w-4xl mx-auto space-y-6 text-slate-800 dark:text-slate-200">
        {/* Document Header */}
        <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
          <div className="text-xs font-mono text-teal-600 dark:text-teal-400 font-semibold uppercase tracking-wider">
            MINUTES OF MEETING
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {meeting.title}
          </h1>
          <div className="flex flex-wrap gap-4 text-xs text-slate-500 dark:text-slate-400 pt-2">
            <span>
              <strong>Date:</strong> {new Date(meeting.meeting_date).toLocaleDateString()}
            </span>
            <span>•</span>
            <span>
              <strong>Duration:</strong> {formatSecondsToTime(meeting.duration_seconds)}
            </span>
            <span>•</span>
            <span>
              <strong>Participants:</strong> {participants}
            </span>
          </div>
        </div>

        {/* 1. Executive Summary */}
        <section className="space-y-2">
          <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 border-b border-slate-100 dark:border-slate-800/60 pb-1">
            1. Executive Summary
          </h2>
          <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
            {meeting.summary?.executive_summary || 'No executive summary available.'}
          </p>
        </section>

        {/* 2. Agenda Topics */}
        {meeting.summary?.agenda_topics && meeting.summary.agenda_topics.length > 0 && (
          <section className="space-y-2">
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 border-b border-slate-100 dark:border-slate-800/60 pb-1">
              2. Agenda & Discussion Topics
            </h2>
            <ul className="list-disc list-inside text-sm space-y-1 text-slate-700 dark:text-slate-300">
              {meeting.summary.agenda_topics.map((t, idx) => (
                <li key={idx}>{t}</li>
              ))}
            </ul>
          </section>
        )}

        {/* 3. Decisions */}
        {meeting.decisions && meeting.decisions.length > 0 && (
          <section className="space-y-3">
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 border-b border-slate-100 dark:border-slate-800/60 pb-1">
              3. Key Decisions
            </h2>
            <div className="space-y-2">
              {meeting.decisions.map((dec, idx) => (
                <div key={dec.id} className="text-sm">
                  <span className="font-semibold text-slate-900 dark:text-slate-100">
                    3.{idx + 1} {dec.decision}
                  </span>
                  {dec.context && (
                    <p className="text-xs text-slate-500 pl-4 mt-0.5">Rationale: {dec.context}</p>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 4. Action Items Table */}
        {meeting.action_items && meeting.action_items.length > 0 && (
          <section className="space-y-3">
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 border-b border-slate-100 dark:border-slate-800/60 pb-1">
              4. Action Items & Commitments
            </h2>
            <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-700 dark:text-slate-300 uppercase font-semibold">
                  <tr>
                    <th className="px-4 py-2.5">Action Item</th>
                    <th className="px-4 py-2.5">Assignee</th>
                    <th className="px-4 py-2.5">Deadline</th>
                    <th className="px-4 py-2.5">Priority</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-600 dark:text-slate-300">
                  {meeting.action_items.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                      <td className="px-4 py-2.5 font-medium text-slate-900 dark:text-slate-100">
                        {item.description}
                      </td>
                      <td className="px-4 py-2.5">{item.assignee || 'Unassigned'}</td>
                      <td className="px-4 py-2.5">{item.deadline || 'TBD'}</td>
                      <td className="px-4 py-2.5">{item.priority}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* 5. Deadlines & Dates */}
        {meeting.important_dates && meeting.important_dates.length > 0 && (
          <section className="space-y-2">
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 border-b border-slate-100 dark:border-slate-800/60 pb-1">
              5. Important Dates & Milestones
            </h2>
            <ul className="list-disc list-inside text-sm space-y-1 text-slate-700 dark:text-slate-300">
              {meeting.important_dates.map((dt) => (
                <li key={dt.id}>
                  <strong>{dt.raw_phrase}</strong>
                  {dt.normalized_date ? ` (${dt.normalized_date})` : ''}: {dt.description}
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* 6. Unresolved Questions */}
        {meeting.unresolved_questions && meeting.unresolved_questions.length > 0 && (
          <section className="space-y-2">
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 border-b border-slate-100 dark:border-slate-800/60 pb-1">
              6. Open & Unresolved Questions
            </h2>
            <ul className="list-disc list-inside text-sm space-y-1 text-slate-700 dark:text-slate-300">
              {meeting.unresolved_questions.map((q) => (
                <li key={q.id}>
                  {q.question} <span className="text-xs text-slate-500">(Raised by: {q.raised_by})</span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
};
