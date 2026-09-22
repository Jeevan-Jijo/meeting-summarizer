'use client';

import React, { useState, useEffect } from 'react';
import { UserCheck, Edit3 } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Speaker } from '@/lib/types';
import { api } from '@/lib/api';

interface SpeakerRenameModalProps {
  isOpen: boolean;
  onClose: () => void;
  meetingId: number;
  speaker: Speaker | null;
  onSpeakerUpdated: (updatedSpeaker: Speaker) => void;
}

export const SpeakerRenameModal: React.FC<SpeakerRenameModalProps> = ({
  isOpen,
  onClose,
  meetingId,
  speaker,
  onSpeakerUpdated,
}) => {
  const [name, setName] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (speaker) {
      setName(speaker.display_name);
      setError(null);
    }
  }, [speaker]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!speaker) return;
    if (!name.trim()) {
      setError('Speaker name cannot be blank.');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const updated = await api.renameSpeaker(meetingId, speaker.id, name.trim());
      onSpeakerUpdated(updated);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to update speaker name.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Rename Speaker">
      <form onSubmit={handleSubmit} className="space-y-4">
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Renaming <strong>{speaker?.speaker_tag}</strong> ({speaker?.display_name}) will automatically update all transcript segments, action items, and analytics for this meeting.
        </p>

        {error && (
          <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-500">
            {error}
          </div>
        )}

        <div>
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
            Display Name
          </label>
          <input
            type="text"
            required
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Alex Rivers"
            className="w-full px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
        </div>

        <div className="flex justify-end gap-2 pt-3">
          <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" isLoading={isLoading}>
            <UserCheck className="w-4 h-4" /> Save Changes
          </Button>
        </div>
      </form>
    </Modal>
  );
};
