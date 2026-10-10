# Meeting Intelligence System (MIS)

> **A 100% Local-First, Privacy-Preserving AI Meeting Intelligence System**  
> Runs entirely on your local Windows PC with local GPU/CPU inference, Ollama (`qwen3:8b`), NVIDIA Parakeet (`nvidia/parakeet-tdt-0.6b-v2`), PyAnnote diarization, and FAISS vector retrieval. Zero external API calls, zero subscriptions, zero cloud data leaks.

---

## Key Capabilities

1. **Browser Recording & File Ingestion**: Record meetings live via the browser microphone or upload any audio/video file (`.mp3`, `.wav`, `.m4a`, `.mp4`, `.webm`, `.flac`, `.ogg`, `.mkv`).
2. **Audio Normalization**: Automatic FFmpeg 16kHz mono 16-bit PCM normalization.
3. **Timestamped Speech-to-Text**: High-speed, local transcription using **NVIDIA Parakeet** (`nvidia/parakeet-tdt-0.6b-v2` via NVIDIA NeMo toolkit with CUDA / CPU fallback).
4. **Speaker Diarization**: Open-weights speaker identification using `pyannote/speaker-diarization-3.1` (with graceful fallback if no HuggingFace token is provided).
5. **Manual Speaker Renaming**: Rename `Speaker 1` to real names with instant global updates across all transcript segments and analytics.
6. **Structured LLM Extractions (Ollama Qwen3)**:
   - Executive Summary
   - Key Points & Decisions
   - Action Items (Assignee, Priority, Deadline, Source Evidence)
   - Important Dates & Scheduled Events (with ambiguity flag `needs_confirmation`)
   - Takeaways & Unresolved Questions
   - Sentiment & Tone Estimate (explicitly labelled as AI estimate)
   - Participation Statistics (speaking time, percentage of speech, turns, average turn length)
   - Structured Minutes of Meeting (MoM)
7. **RAG Meeting Chatbot**: Local FAISS vector index with `all-MiniLM-L6-v2` embeddings answering questions citing precise transcript timestamps `[HH:MM:SS]`.
8. **Interactive Editor**: Edit or delete AI-extracted items and rename participants.
9. **Multi-Format Export**: Export meeting minutes and records as **Markdown**, **JSON**, and **PDF**.

---

## Hardware & Prerequisites

- **Operating System**: Windows 11 (or 10 / Linux)
- **Processor & GPU**: Tested on AMD Ryzen 7 7840HS, NVIDIA RTX 4060 Laptop GPU (8 GB VRAM), 16 GB RAM.
- **Python**: Python 3.9 - 3.12
- **Node.js**: Node.js 20+ (v24.x tested)
- **FFmpeg**: Installed and in system `PATH`
- **Ollama**: Installed and serving locally on `http://localhost:11434`

---

## Quick Start Guide

### Step 1: Clone or Open Project
```powershell
cd e:\PROJECTS\MIS
```

### Step 2: Set Up Ollama with Qwen3
In a PowerShell window:
```powershell
# Ensure Ollama is running, then pull the target model
ollama pull qwen3:8b

# Or if using a fallback model
ollama pull qwen2.5:7b
```

### Step 3: Set Up Backend (Python)
```powershell
# Create Python virtual environment
python -m venv backend/venv

# Activate virtual environment
.\backend\venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r backend/requirements.txt

# (Optional) Set your free HuggingFace token for PyAnnote Diarization
$env:HF_TOKEN = "hf_your_token_here"

# Start the FastAPI backend server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend API is now running at `http://127.0.0.1:8000` (Swagger docs: `http://127.0.0.1:8000/docs`).

### Step 4: Set Up Frontend (Next.js)
In a new terminal:
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your web browser.

---

## Speaker Diarization Setup (pyannote.audio)

PyAnnote 3.1 is an open-weights model requiring a one-time free terms acceptance on Hugging Face:
1. Accept terms at [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1) and [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0).
2. Generate a token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
3. Set `HF_TOKEN` in `.env` or in your environment.

> **Graceful Fallback**: If no `HF_TOKEN` is set, the system automatically labels segments as `Unknown Speaker` or single speaker without breaking transcription, analysis, or chatbot features.

---

## Processing Pipeline States

1. `UPLOADED` - Audio/video uploaded or recorded.
2. `QUEUED` - Job registered in SQLite database.
3. `PREPROCESSING` - Audio converted to 16kHz mono WAV via FFmpeg.
4. `TRANSCRIBING` - NVIDIA Parakeet generates timestamped segments.
5. `DIARIZING` - PyAnnote segments speakers.
6. `ALIGNING` - Matches transcript segments with speaker turns.
7. `CHUNKING` - Semantic chunking with preserved metadata.
8. `ANALYZING` - Ollama extracts structured JSON entities.
9. `INDEXING` - Vector embeddings & FAISS index creation.
10. `FINALIZING` - Participation statistics & Minutes generation.
11. `COMPLETED` / `FAILED` - Results ready or error reported.

---

## Troubleshooting

### CUDA / GPU Acceleration
- If PyTorch CUDA acceleration is unavailable or disabled, the backend automatically falls back to CPU computation (`float32`).
- To force CPU or GPU mode, set `PARAKEET_DEVICE=cuda` or `PARAKEET_DEVICE=cpu` in backend settings / environment.

### Memory Management (8 GB VRAM)
- GPU stages are executed sequentially: NVIDIA Parakeet transcribes and PyAnnote diarizes, then VRAM cache is freed before Ollama LLM requests are dispatched.

### Ollama Connectivity
- Check that Ollama is running: `Invoke-RestMethod http://localhost:11434/api/tags`.
- Check active models on the **Settings** page in the web app.

---

## Privacy Statement

All audio recordings, transcripts, vector indices, and LLM inferences remain **strictly on your local machine**.
- Zero telemetry.
- Zero external API calls.
- SQLite database stored locally in `./backend/data/mis.db`.

---

## License Inventory

| Component | Upstream Model / Library | License |
|---|---|---|
| **Speech Recognition** | `NVIDIA Parakeet` / `nvidia/parakeet-tdt-0.6b-v2` (NVIDIA NeMo) | CC-BY-4.0 |
| **LLM Inference** | `qwen3:8b` / Qwen Team | Apache-2.0 |
| **Diarization** | `pyannote/speaker-diarization-3.1` | MIT (Gated Model) |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | Apache-2.0 |
| **Vector Search** | `FAISS` / Meta AI | MIT |
| **Media Processing**| `FFmpeg` | LGPL / GPL |
| **Application Code**| Meeting Intelligence System | MIT |
