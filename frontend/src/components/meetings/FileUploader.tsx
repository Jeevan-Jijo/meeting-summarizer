'use client';

import React, { useState, useRef } from 'react';
import { UploadCloud, FileAudio, FileVideo, X, ArrowRight, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { formatFileSize } from '@/lib/utils';

interface FileUploaderProps {
  onUploadSubmit: (file: File, title: string, description?: string) => void;
  isSubmitting?: boolean;
}

const SUPPORTED_EXTS = ['.mp3', '.wav', '.m4a', '.mp4', '.webm', '.ogg', '.flac', '.mkv', '.aac'];

export const FileUploader: React.FC<FileUploaderProps> = ({
  onUploadSubmit,
  isSubmitting = false,
}) => {
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const validateAndSetFile = (file: File) => {
    setError(null);
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!SUPPORTED_EXTS.includes(ext)) {
      setError(`Unsupported format "${ext}". Please upload: ${SUPPORTED_EXTS.join(', ')}`);
      return;
    }
    if (file.size > 500 * 1024 * 1024) {
      setError('File size exceeds the 500 MB limit.');
      return;
    }

    setSelectedFile(file);
    if (!title) {
      const cleanName = file.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ');
      setTitle(cleanName.charAt(0).toUpperCase() + cleanName.slice(1));
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select an audio or video recording file.');
      return;
    }
    onUploadSubmit(selectedFile, title || selectedFile.name, description);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Drop Area */}
      {!selectedFile ? (
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all ${
            dragActive
              ? 'border-teal-500 bg-teal-500/10'
              : 'border-slate-300 dark:border-slate-700 hover:border-teal-500/60 dark:hover:border-teal-500/60 bg-white dark:bg-slate-900/40'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={SUPPORTED_EXTS.join(',')}
            onChange={handleChange}
            className="hidden"
          />

          <div className="w-16 h-16 mx-auto rounded-full bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-600 dark:text-teal-400 mb-4">
            <UploadCloud className="w-8 h-8" />
          </div>

          <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
            Click to upload or drag & drop meeting recording
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Supports audio and video files up to 500 MB
          </p>

          <div className="mt-4 flex flex-wrap justify-center gap-1.5">
            {['MP3', 'WAV', 'M4A', 'MP4', 'WEBM', 'FLAC', 'OGG', 'MKV'].map((ext) => (
              <span
                key={ext}
                className="px-2 py-0.5 text-[10px] font-mono font-medium rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700"
              >
                .{ext.toLowerCase()}
              </span>
            ))}
          </div>
        </div>
      ) : (
        /* Selected File Card */
        <div className="p-4 rounded-xl border border-teal-500/30 bg-teal-500/5 flex items-center justify-between animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-teal-500/20 text-teal-600 dark:text-teal-400 flex items-center justify-center">
              {selectedFile.type.includes('video') ? (
                <FileVideo className="w-5 h-5" />
              ) : (
                <FileAudio className="w-5 h-5" />
              )}
            </div>
            <div>
              <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate max-w-sm">
                {selectedFile.name}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {formatFileSize(selectedFile.size)}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setSelectedFile(null)}
            className="p-1.5 text-slate-400 hover:text-rose-500 transition rounded-lg hover:bg-rose-500/10"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {error && (
        <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 text-xs text-rose-600 dark:text-rose-400 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Metadata Inputs */}
      <div className="space-y-4">
        <div>
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1.5">
            Meeting Title *
          </label>
          <input
            type="text"
            required
            placeholder="e.g. Sprint Review & Technical Planning"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
        </div>

        <div>
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1.5">
            Description / Context (Optional)
          </label>
          <textarea
            rows={2}
            placeholder="Add relevant meeting background or agenda points..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 resize-none"
          />
        </div>
      </div>

      <Button
        type="submit"
        variant="primary"
        size="lg"
        className="w-full"
        isLoading={isSubmitting}
        disabled={!selectedFile}
      >
        Upload & Process Meeting <ArrowRight className="w-4 h-4" />
      </Button>
    </form>
  );
};
