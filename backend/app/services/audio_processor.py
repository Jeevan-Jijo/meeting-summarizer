import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Tuple, Optional
from app.core.logging import logger

def get_ffmpeg_binary_path(binary_name: str = "ffmpeg") -> Optional[str]:
    """Find ffmpeg or ffprobe executable in PATH or WinGet installation directories."""
    path = shutil.which(binary_name)
    if path:
        return path
    
    # Check WinGet packages directory fallback
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        winget_dir = os.path.join(local_appdata, r"Microsoft\WinGet\Packages")
        if os.path.exists(winget_dir):
            for root, _, files in os.walk(winget_dir):
                target = f"{binary_name}.exe"
                if target in files:
                    full_path = os.path.join(root, target)
                    return full_path
    return None

def format_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS format."""
    total_seconds = int(round(seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def is_ffmpeg_available() -> bool:
    """Check if ffmpeg executable is available in PATH or WinGet."""
    return get_ffmpeg_binary_path("ffmpeg") is not None

def get_audio_duration(file_path: str) -> float:
    """Extract audio duration using ffprobe or fallback."""
    ffprobe_bin = get_ffmpeg_binary_path("ffprobe")
    if not ffprobe_bin:
        logger.warning("ffprobe not found in PATH, using fallback duration estimation.")
        return 0.0
    
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
    except Exception as e:
        logger.warning(f"Failed to get audio duration via ffprobe: {e}")
        return 0.0

def _execute_ffmpeg(cmd: list) -> Tuple[int, str, str]:
    """Run FFmpeg synchronously in a thread."""
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as ex:
        return -1, "", str(ex)

async def normalize_audio(input_path: str, output_path: str) -> Tuple[bool, str, float]:
    """
    Normalize audio to 16kHz mono 16-bit PCM WAV using FFmpeg.
    Returns (success, message, duration_seconds).
    """
    ffmpeg_bin = get_ffmpeg_binary_path("ffmpeg")
    if not ffmpeg_bin:
        return False, "FFmpeg is not installed or not in system PATH", 0.0

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", input_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_path
    ]
    
    try:
        returncode, stdout, stderr = await asyncio.to_thread(_execute_ffmpeg, cmd)
        
        if returncode != 0:
            err_msg = stderr.strip() if stderr else "Unknown FFmpeg error"
            logger.error(f"FFmpeg normalization failed (code {returncode}): {err_msg}")
            return False, f"FFmpeg failed: {err_msg[:200]}", 0.0
            
        duration = get_audio_duration(output_path)
        logger.info(f"Normalized audio: {output_path} (Duration: {duration:.2f}s)")
        return True, "Audio normalized successfully", duration

    except Exception as e:
        logger.error(f"Error executing FFmpeg: {e}")
        return False, str(e), 0.0
