import os
import gc
from typing import List, Dict, Any, Tuple
from app.core.config import settings
from app.core.logging import logger

class Diarizer:
    def __init__(self, token: str = None):
        raw_token = token or settings.HF_TOKEN or os.environ.get("HF_TOKEN", "") or ""
        self.token = raw_token.strip()
        self.pipeline = None

    def is_available(self) -> Tuple[bool, str]:
        """Check if pyannote can be loaded with valid token."""
        if not self.token:
            return False, "Hugging Face token (HF_TOKEN) is not configured. Falling back to single-speaker mode."
        try:
            import pyannote.audio
            return True, "pyannote.audio available with token"
        except ImportError:
            return False, "pyannote.audio package is not installed in the environment."

    def load_pipeline(self):
        """Load the pyannote speaker diarization pipeline."""
        if self.pipeline is not None:
            return self.pipeline
            
        if not self.token:
            logger.info("No HF_TOKEN provided; skipping pyannote loading.")
            return None
            
        try:
            from pyannote.audio import Pipeline
            import torch
            
            logger.info(f"Loading pyannote pipeline '{settings.DIARIZATION_MODEL}'...")
            try:
                self.pipeline = Pipeline.from_pretrained(
                    settings.DIARIZATION_MODEL,
                    token=self.token
                )
            except TypeError:
                self.pipeline = Pipeline.from_pretrained(
                    settings.DIARIZATION_MODEL,
                    use_auth_token=self.token
                )
            
            if torch.cuda.is_available() and settings.WHISPER_DEVICE != "cpu":
                self.pipeline.to(torch.device("cuda"))
                logger.info("pyannote diarization loaded on CUDA")
            else:
                logger.info("pyannote diarization loaded on CPU")
                
            return self.pipeline
        except Exception as e:
            logger.warning(
                f"Could not load pyannote pipeline ({e}). "
                f"Please ensure you accepted terms at https://huggingface.co/pyannote/speaker-diarization-3.1 "
                f"and generated a token at https://huggingface.co/settings/tokens. "
                f"Gracefully continuing with Unknown Speaker tags."
            )
            self.pipeline = None
            return None

    def _fallback_diarize(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Local acoustic feature clustering diarization fallback when pyannote is unavailable.
        Uses wave + numpy + sklearn AgglomerativeClustering with spectral subband analysis.
        """
        try:
            import wave
            import numpy as np
            from sklearn.cluster import AgglomerativeClustering
            from sklearn.preprocessing import StandardScaler

            logger.info(f"Running acoustic feature diarization fallback on {audio_path}...")
            with wave.open(audio_path, 'rb') as wf:
                sr = wf.getframerate()
                n_channels = wf.getnchannels()
                frames = wf.readframes(wf.getnframes())
                raw_samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
                if n_channels > 1:
                    raw_samples = raw_samples[::n_channels]

            if len(raw_samples) == 0:
                return []

            window_size = int(sr * 1.5)
            hop_size = int(sr * 0.75)
            total_samples = len(raw_samples)
            
            windows = []
            timestamps = []
            
            for start in range(0, total_samples - window_size + 1, hop_size):
                chunk = raw_samples[start:start + window_size]
                rms = np.sqrt(np.mean(chunk**2))
                if rms < 100:  # Ignore silence
                    continue
                
                fft_mag = np.abs(np.fft.rfft(chunk * np.hanning(len(chunk))))
                if len(fft_mag) == 0:
                    continue
                
                subband_len = max(1, len(fft_mag) // 16)
                feats = [np.log1p(np.mean(fft_mag[i*subband_len:(i+1)*subband_len])) for i in range(16)]
                zcr = np.mean(np.abs(np.diff(np.sign(chunk))))
                feats.append(zcr)
                feats.append(np.log1p(rms))
                
                windows.append(feats)
                timestamps.append((start / sr, (start + window_size) / sr))

            if len(windows) < 4:
                return []

            X = StandardScaler().fit_transform(np.array(windows))
            n_clusters = min(4, max(2, len(windows) // 40))
            clustering = AgglomerativeClustering(n_clusters=n_clusters, metric='cosine', linkage='average')
            labels = clustering.fit_predict(X)
            
            turns = []
            current_speaker = f"SPEAKER_{labels[0]:02d}"
            turn_start, turn_end = timestamps[0]
            
            for (t_start, t_end), label in zip(timestamps[1:], labels[1:]):
                spk = f"SPEAKER_{label:02d}"
                if spk == current_speaker and t_start <= turn_end + 1.0:
                    turn_end = t_end
                else:
                    turns.append({"start": round(turn_start, 2), "end": round(turn_end, 2), "speaker": current_speaker})
                    current_speaker = spk
                    turn_start, turn_end = t_start, t_end
            
            turns.append({"start": round(turn_start, 2), "end": round(turn_end, 2), "speaker": current_speaker})
            logger.info(f"Acoustic fallback diarization complete: found {len(turns)} turns across {len(set(t['speaker'] for t in turns))} speakers.")
            return turns
        except Exception as e:
            logger.error(f"Fallback diarization error: {e}")
            return []

    def diarize(self, audio_path: str) -> Tuple[List[Dict[str, Any]], bool, str]:
        """
        Diarize audio file.
        Returns (speaker_turns_list, is_real_diarization, status_message).
        speaker_turns_list format: [{'start': 0.0, 'end': 12.5, 'speaker': 'SPEAKER_00'}, ...]
        """
        pipeline = self.load_pipeline()
        
        if pipeline is None:
            turns = self._fallback_diarize(audio_path)
            if turns:
                return turns, True, "Speaker diarization completed via acoustic clustering fallback"
            return [], False, "Diarization skipped (HF_TOKEN not set or model access not granted)."
            
        try:
            logger.info(f"Running pyannote diarization on {audio_path}...")
            diarization = pipeline(audio_path)
            
            turns = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                turns.append({
                    "start": round(turn.start, 2),
                    "end": round(turn.end, 2),
                    "speaker": str(speaker)
                })
                
            logger.info(f"Diarization complete: found {len(turns)} turns across {len(set(t['speaker'] for t in turns))} speakers.")
            return turns, True, "Speaker diarization completed successfully"
        except Exception as e:
            logger.error(f"Error during pyannote diarization inference: {e}")
            turns = self._fallback_diarize(audio_path)
            if turns:
                return turns, True, "Speaker diarization completed via acoustic clustering fallback after pyannote error"
            return [], False, f"Diarization error: {str(e)}"

    def unload(self):
        """Free VRAM after diarization step."""
        self.pipeline = None
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        logger.info("Diarization pipeline unloaded and VRAM cleared.")
