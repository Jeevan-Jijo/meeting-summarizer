'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Play, Pause, RotateCcw, ArrowRight, Volume2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { formatSecondsToTime } from '@/lib/utils';

interface AudioRecorderProps {
  onRecordingComplete: (file: File, title: string) => void;
  isSubmitting?: boolean;
}

export const AudioRecorder: React.FC<AudioRecorderProps> = ({
  onRecordingComplete,
  isSubmitting = false
}) => {
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [meetingTitle, setMeetingTitle] = useState<string>('');
  const [audioLevels, setAudioLevels] = useState<number[]>(new Array(16).fill(10));

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close();
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Web Audio API for visualizer
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioCtx.createAnalyser();
      const source = audioCtx.createMediaStreamSource(stream);
      analyser.fftSize = 64;
      source.connect(analyser);

      audioContextRef.current = audioCtx;
      analyserRef.current = analyser;

      const updateWaveform = () => {
        if (!analyserRef.current) return;
        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteFrequencyData(dataArray);

        const sampleBars = [];
        const step = Math.floor(dataArray.length / 16);
        for (let i = 0; i < 16; i++) {
          const val = dataArray[i * step] || 0;
          sampleBars.push(Math.max(10, (val / 255) * 100));
        }
        setAudioLevels(sampleBars);
        animationFrameRef.current = requestAnimationFrame(updateWaveform);
      };
      updateWaveform();

      // Media Recorder
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const mimeType = mediaRecorder.mimeType || 'audio/webm';
        const blob = new Blob(chunksRef.current, { type: mimeType });
        setRecordedBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
      };

      mediaRecorder.start(250);
      setIsRecording(true);
      setIsPaused(false);
      setElapsedSeconds(0);
      setAudioUrl(null);
      setRecordedBlob(null);

      timerIntervalRef.current = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err: any) {
      alert(`Microphone access error: ${err.message}`);
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && isRecording && !isPaused) {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && isRecording && isPaused) {
      mediaRecorderRef.current.resume();
      setIsPaused(false);
      timerIntervalRef.current = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      setIsRecording(false);
      setIsPaused(false);
    }
  };

  const resetRecording = () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioUrl(null);
    setRecordedBlob(null);
    setElapsedSeconds(0);
  };

  const handleSubmit = () => {
    if (!recordedBlob) return;
    const extension = recordedBlob.type.includes('ogg') ? 'ogg' : 'webm';
    const filename = `meeting_recording_${Date.now()}.${extension}`;
    const file = new File([recordedBlob], filename, { type: recordedBlob.type });
    const finalTitle = meetingTitle.trim() || `Live Recording - ${new Date().toLocaleDateString()}`;
    onRecordingComplete(file, finalTitle);
  };

  return (
    <div className="flex flex-col items-center justify-center p-8 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/40 text-center space-y-6">
      {!isRecording && !audioUrl && (
        <div className="space-y-4 max-w-md">
          <div className="w-20 h-20 mx-auto rounded-full bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-600 dark:text-teal-400">
            <Mic className="w-10 h-10" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Live Meeting Recording</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Record your in-person or speaker-output meeting directly using your browser microphone.
            </p>
          </div>
          <Button onClick={startRecording} variant="primary" size="lg" className="w-full">
            <Mic className="w-5 h-5" />
            Start Recording
          </Button>
        </div>
      )}

      {isRecording && (
        <div className="w-full max-w-md space-y-6 animate-fade-in">
          <div className="flex items-center justify-center gap-2 text-rose-500 text-xs font-semibold uppercase tracking-wider">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
            {isPaused ? 'Recording Paused' : 'Recording Live'}
          </div>

          <div className="text-4xl font-mono font-bold text-slate-900 dark:text-white">
            {formatSecondsToTime(elapsedSeconds)}
          </div>

          {/* Audio Visualizer Waveform */}
          <div className="h-16 flex items-center justify-center gap-1 px-4 bg-slate-100 dark:bg-slate-800/60 rounded-xl">
            {audioLevels.map((lvl, idx) => (
              <div
                key={idx}
                className="w-2 bg-teal-500 rounded-full transition-all duration-75 ease-out"
                style={{ height: `${isPaused ? 8 : lvl}%` }}
              />
            ))}
          </div>

          {/* Controls */}
          <div className="flex items-center justify-center gap-3">
            {isPaused ? (
              <Button onClick={resumeRecording} variant="secondary">
                <Play className="w-4 h-4" /> Resume
              </Button>
            ) : (
              <Button onClick={pauseRecording} variant="secondary">
                <Pause className="w-4 h-4" /> Pause
              </Button>
            )}
            <Button onClick={stopRecording} variant="danger">
              <Square className="w-4 h-4" /> Finish Recording
            </Button>
          </div>
        </div>
      )}

      {audioUrl && !isRecording && (
        <div className="w-full max-w-md space-y-5 animate-slide-up">
          <div className="p-4 rounded-xl bg-teal-50 dark:bg-teal-950/30 border border-teal-200 dark:border-teal-800/50 space-y-2">
            <div className="flex items-center justify-between text-sm font-medium text-teal-800 dark:text-teal-200">
              <span className="flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-teal-600" /> Recording Ready
              </span>
              <span className="font-mono">{formatSecondsToTime(elapsedSeconds)}</span>
            </div>
            <audio src={audioUrl} controls className="w-full h-10 mt-2" />
          </div>

          <div className="text-left space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Meeting Title</label>
            <input
              type="text"
              placeholder="e.g. Q3 Architecture Review & Roadmap"
              value={meetingTitle}
              onChange={(e) => setMeetingTitle(e.target.value)}
              className="w-full px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
            />
          </div>

          <div className="flex items-center gap-3">
            <Button onClick={resetRecording} variant="outline" className="flex-1" disabled={isSubmitting}>
              <RotateCcw className="w-4 h-4" /> Discard & Retake
            </Button>
            <Button onClick={handleSubmit} variant="primary" className="flex-1" isLoading={isSubmitting}>
              Process Meeting <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
