'use client';

import React from 'react';
import { User, Clock, MessageSquare, Flame, AlertCircle, Info, ShieldAlert } from 'lucide-react';
import { Speaker, MeetingSummary } from '@/lib/types';
import { formatSecondsToTime } from '@/lib/utils';
import { ProgressBar } from '@/components/ui/ProgressBar';

interface AnalyticsChartsProps {
  speakers: Speaker[];
  durationSeconds: number;
  summary?: MeetingSummary;
}

const BAR_COLORS: ('brand' | 'emerald' | 'indigo' | 'amber')[] = ['brand', 'indigo', 'emerald', 'amber'];

export const AnalyticsCharts: React.FC<AnalyticsChartsProps> = ({
  speakers,
  durationSeconds,
  summary,
}) => {
  const totalSpeech = speakers.reduce((acc, s) => acc + s.speaking_time_seconds, 0);
  const totalSilence = Math.max(0, durationSeconds - totalSpeech);
  const silencePercentage = durationSeconds > 0 ? (totalSilence / durationSeconds) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Participation Stats Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/50 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Total Speaking Time</span>
            <Clock className="w-4 h-4 text-teal-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
            {formatSecondsToTime(totalSpeech)}
          </div>
          <p className="text-xs text-slate-400">
            Across {speakers.length} identified speaker{speakers.length === 1 ? '' : 's'}
          </p>
        </div>

        <div className="p-5 rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/50 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Speaker Turn Transitions</span>
            <MessageSquare className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
            {speakers.reduce((acc, s) => acc + s.turn_count, 0)}
          </div>
          <p className="text-xs text-slate-400">Total conversation turn switches</p>
        </div>

        <div className="p-5 rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/50 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Silence / Pauses</span>
            <Flame className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
            {formatSecondsToTime(totalSilence)}
          </div>
          <p className="text-xs text-slate-400">{silencePercentage.toFixed(1)}% of total meeting</p>
        </div>
      </div>

      {/* Speaker Participation Breakdown */}
      <div className="p-6 rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/50 space-y-5">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <User className="w-4 h-4 text-teal-500" /> Speaker Speaking Distribution
          </h3>
          <span className="text-xs text-slate-400">Factual timing statistics</span>
        </div>

        <div className="space-y-4">
          {speakers.length === 0 ? (
            <div className="p-6 text-center text-slate-400 text-xs">No speaker analytics available.</div>
          ) : (
            speakers.map((spk, idx) => {
              const color = BAR_COLORS[idx % BAR_COLORS.length];
              return (
                <div key={spk.id} className="space-y-2 p-3.5 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200/40 dark:border-slate-700/40">
                  <div className="flex items-center justify-between text-xs font-medium">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-900 dark:text-slate-100">
                        {spk.display_name}
                      </span>
                      <span className="text-slate-400 font-mono text-[11px]">({spk.speaker_tag})</span>
                      {spk.estimated_tone && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
                          {spk.estimated_tone}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-slate-600 dark:text-slate-300 font-mono">
                      <span>{spk.speaking_percentage.toFixed(1)}%</span>
                      <span>•</span>
                      <span>{formatSecondsToTime(spk.speaking_time_seconds)}</span>
                    </div>
                  </div>

                  <ProgressBar progress={spk.speaking_percentage} color={color} />

                  <div className="flex justify-between text-[11px] text-slate-500 dark:text-slate-400 pt-1">
                    <span>{spk.turn_count} speech turns</span>
                    <span>Avg turn: {spk.avg_turn_seconds.toFixed(1)}s</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* AI Sentiment & Tone Estimate (with mandatory disclaimer) */}
      <div className="p-6 rounded-xl border border-amber-500/20 bg-amber-500/5 dark:bg-amber-950/20 space-y-3">
        <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 font-semibold text-sm">
          <Info className="w-4 h-4 shrink-0" />
          <span>AI Sentiment & Discussion Tone Estimate</span>
        </div>

        <div className="space-y-1.5 text-xs text-slate-700 dark:text-slate-300">
          <p>
            <strong>Estimated Overall Tone:</strong>{' '}
            <span className="font-semibold text-teal-600 dark:text-teal-400">
              {summary?.overall_sentiment_estimate || 'Constructive / Professional'}
            </span>
          </p>
          {summary?.sentiment_justification && (
            <p className="text-slate-600 dark:text-slate-400 italic">
              "{summary.sentiment_justification}"
            </p>
          )}
        </div>

        <div className="pt-2 border-t border-amber-500/20 text-[11px] text-amber-600/80 dark:text-amber-400/80 flex items-start gap-1.5">
          <ShieldAlert className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>
            <strong>Disclaimer:</strong> Sentiment and tone observations are probabilistic AI estimates derived solely from transcribed vocabulary and turn pacing. They are not objective evaluations and must not be used for individual performance reviews.
          </span>
        </div>
      </div>
    </div>
  );
};
