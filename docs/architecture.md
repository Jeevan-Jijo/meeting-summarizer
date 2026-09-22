# Meeting Intelligence System (MIS) - Architecture Overview

## System Architecture

```text
+-------------------------------------------------------------------------+
|                          Next.js Frontend (React 19 / App Router)       |
|  - Audio Recorder (Web Audio API)    - Transcript & Synchronized Player |
|  - Meeting Analytics & Charts        - RAG Chatbot with Citations       |
|  - Live Processing Progress Polling  - Markdown / JSON / PDF Export     |
+------------------------------------+------------------------------------+
                                     | HTTP REST / JSON
                                     v
+------------------------------------+------------------------------------+
|                          FastAPI Backend (Python 3.12)                  |
|  - REST Endpoints (/meetings, /jobs, /chat, /export, /settings, /audio)  |
|  - SQLite Database with SQLAlchemy ORM                                   |
|  - Async Background Processing Pipeline Worker                          |
+------------------------------------+------------------------------------+
                                     |
    +--------------------------------+-------------------------------+
    |                                |                               |
    v                                v                               v
+-------------------+      +-------------------+           +-------------------+
| Audio Normalizer  |      | Speech-to-Text    |           | Speaker Diarizer  |
| - FFmpeg Subproc  | ---> | - faster-whisper  | ------->  | - pyannote 3.1    |
| - 16kHz Mono WAV  |      | - CUDA float16    |           | - Graceful no-tok |
+-------------------+      +---------+---------+           +---------+---------+
                                     |                               |
                                     +---------------+---------------+
                                                     |
                                                     v
                                           +-------------------+
                                           | Speaker Aligner   |
                                           | - Overlap Mapping |
                                           | - HH:MM:SS format |
                                           +---------+---------+
                                                     |
                                                     v
                                           +-------------------+
                                           | Semantic Chunker  |
                                           | - Sentence-aware  |
                                           | - Metadata tagged |
                                           +---------+---------+
                                                     |
                                                     v
                                           +-------------------+
                                           | Ollama LLM (Qwen3)|
                                           | - Structured JSON |
                                           | - Map-Reduce Syn  |
                                           +---------+---------+
                                                     |
                                                     v
                                           +-------------------+
                                           | Vector Store RAG  |
                                           | - all-MiniLM-L6-v2|
                                           | - FAISS Index     |
                                           +-------------------+
```

## Processing States Lifecycle

```text
[UPLOADED]
   │
   ▼
[QUEUED]
   │
   ▼
[PREPROCESSING] ─── FFmpeg normalizes audio to 16kHz mono WAV
   │
   ▼
[TRANSCRIBING]  ─── faster-whisper produces timestamped transcript
   │
   ▼
[DIARIZING]     ─── pyannote.audio generates speaker turn intervals (or fallback)
   │
   ▼
[ALIGNING]      ─── Computes timestamp overlap to assign Speaker 1, 2, ...
   │
   ▼
[CHUNKING]      ─── Chunks transcript semantically with speaker/timestamp metadata
   │
   ▼
[ANALYZING]     ─── Ollama Qwen3:8b extracts Summary, Key Points, Action Items, etc.
   │
   ▼
[INDEXING]      ─── sentence-transformers creates vectors & builds FAISS index
   │
   ▼
[FINALIZING]    ─── Synthesizes Participation stats and Minutes of Meeting
   │
   ▼
[COMPLETED] / [FAILED]
```

## Memory Management for 8 GB VRAM
- **Whisper & Diarization**: Runs first. PyTorch memory is freed with `torch.cuda.empty_cache()` and garbage collection before Ollama LLM calls.
- **Ollama LLM**: Runs after transcription/diarization stages finish.
- **Vector Embeddings**: Runs on CPU via `sentence-transformers` using `all-MiniLM-L6-v2` (approx 80MB RAM footprint).
