# Meeting Intelligence System (MIS) - Codebase & Working Principle Guide

> **A 100% Local-First, Privacy-Preserving AI Meeting Intelligence System**  
> Runs entirely on local Windows hardware with local GPU/CPU inference using Ollama (`qwen3:8b`), `faster-whisper`, `pyannote/speaker-diarization-3.1`, and FAISS vector retrieval. Zero external API calls, zero telemetry, zero SaaS subscriptions.

---

## 1. System Architecture Overview

The Meeting Intelligence System (MIS) is engineered with a **local-first microservice architecture**, composed of a Next.js web application frontend, a FastAPI Python backend, a local SQLite relational database, local GPU/CPU ML model runtimes, and local vector storage.

```text
+-----------------------------------------------------------------------------------+
|                           Next.js 14+ Frontend (React 19)                         |
|  - Live Audio Recorder (MediaRecorder API)  - Synchronized Audio Player           |
|  - Interactive Transcript & Speaker Renamer - Extractions Editor                  |
|  - Real-Time Job Progress Tracker (Polling) - RAG Chatbot with [HH:MM:SS] Citations|
|  - Participation Analytics & Charts        - Multi-Format Exporter (MD/JSON/PDF)  |
+-----------------------------------------+-----------------------------------------+
                                          | HTTP REST / JSON APIs
                                          v
+-----------------------------------------------------------------------------------+
|                            FastAPI Backend (Python 3.12)                          |
|  - REST Endpoints (/meetings, /jobs, /chat, /export, /settings, /audio)           |
|  - SQLAlchemy ORM & SQLite Storage (`backend/data/mis.db`)                        |
|  - Async Background Processing Pipeline Worker                                    |
+-----------------------------------------+-----------------------------------------+
                                          |
    +-------------------------------------+-------------------------------------+
    |                                     |                                     |
    v                                     v                                     v
+-----------------------+     +-----------------------+     +-----------------------+
|   Audio Preprocessor  |     |   Speech-to-Text      |     |  Speaker Diarizer     |
| - FFmpeg Subprocess   | --> | - faster-whisper      | --> | - pyannote 3.1        |
| - 16kHz Mono WAV      |     | - CUDA fp16 / CPU int8|     | - Graceful Fallback   |
+-----------------------+     +-----------+-----------+     +-----------+-----------+
                                          |                               |
                                          +---------------+---------------+
                                                          |
                                                          v
                                                +-------------------+
                                                |  Speaker Aligner  |
                                                | - Overlap Mapping |
                                                | - Speaker Stats   |
                                                +---------+---------+
                                                          |
                                                          v
                                                +-------------------+
                                                | Semantic Chunker  |
                                                | - 350-word chunks |
                                                | - Overlap & Meta  |
                                                +---------+---------+
                                                          |
                                                          v
                                                +-------------------+
                                                | Ollama LLM (Qwen3)|
                                                | - Structured JSON |
                                                | - Map-Reduce Extra|
                                                +---------+---------+
                                                          |
                                                          v
                                                +-------------------+
                                                | FAISS Vector RAG  |
                                                | - all-MiniLM-L6-v2|
                                                | - Timestamped Search|
                                                +-------------------+
```

---

## 2. Technology Stack & Key Dependencies

| Domain | Technology / Library | Purpose |
|---|---|---|
| **Frontend Framework** | Next.js 14+ (React 19, TypeScript) | Responsive UI, client routing, media controls, state management |
| **Styling & Icons** | Tailwind CSS, Lucide React, Chart.js | Modern dark-mode UI design, interactive data charts |
| **Backend API** | FastAPI (Python 3.12), Uvicorn | High-performance async REST API framework |
| **Database & ORM** | SQLite, SQLAlchemy 2.0 | Local persistent relational database stored at `./backend/data/mis.db` |
| **Audio Preprocessing** | FFmpeg | Audio conversion to standardized 16kHz mono 16-bit PCM WAV |
| **Speech-to-Text** | `faster-whisper` (`whisper-large-v3-turbo`) | CTranslate2-accelerated local transcription with CUDA float16 / CPU int8 |
| **Speaker Diarization**| `pyannote/speaker-diarization-3.1` | Neural speaker segmentation (gated open weights model on HuggingFace) |
| **LLM Inference** | Ollama (`qwen3:8b` or `qwen2.5:7b`) | Local HTTP LLM service (`http://localhost:11434`) for structured JSON extractions |
| **Embeddings** | `sentence-transformers` (`all-MiniLM-L6-v2`) | 384-dimensional dense vector embeddings for semantic search |
| **Vector Database** | Meta `FAISS` (`IndexFlatIP`) | Local vector index for RAG chatbot timestamp retrieval |
| **PDF Generation** | `ReportLab` | Structured PDF layout generation for Minutes of Meeting |

---

## 3. Step-by-Step Working Principle & Pipeline Lifecycle

When a user records audio live in the browser or uploads an audio/video file, the system executes an automated 11-stage background processing pipeline:

```text
[UPLOADED] ──► [QUEUED] ──► [PREPROCESSING] ──► [TRANSCRIBING] ──► [DIARIZING] ──► [ALIGNING]
                                                                                     │
[COMPLETED] ◄── [FINALIZING] ◄── [INDEXING] ◄── [ANALYZING] ◄── [CHUNKING] ◄─────────┘
```

### Stage Details

1. **Upload & Ingestion (`UPLOADED` -> `QUEUED`)**:
   - The user selects a file (`.mp3`, `.wav`, `.m4a`, `.mp4`, `.webm`, `.flac`, `.ogg`, `.mkv`) or uses the browser microphone recorder.
   - FastAPI endpoint `POST /api/v1/meetings/upload` receives the file, saves it into `./backend/data/uploads`, creates a `Meeting` record and `ProcessingJob` in SQLite, and launches an asynchronous background task.

2. **Audio Normalization (`PREPROCESSING`)**:
   - `app/services/audio_processor.py` invokes FFmpeg via subprocess.
   - Source audio is converted to standard **16kHz mono 16-bit PCM WAV** at `./backend/data/processed/meeting_{id}_norm.wav`.

3. **Speech Transcription (`TRANSCRIBING`)**:
   - `app/services/transcriber.py` loads `faster-whisper`.
   - Auto-detects audio language and generates precise timestamped transcript segments `(start_time, end_time, text, confidence)`.
   - Uses CUDA float16 GPU acceleration if available; gracefully falls back to CPU int8 quantization. Memory is immediately freed upon completion.

4. **Speaker Diarization (`DIARIZING`)**:
   - `app/services/diarizer.py` executes PyAnnote 3.1 neural speaker diarization on the normalized WAV file.
   - Identifies acoustic speaker turns `(speaker_tag, start_time, end_time)`.
   - **Graceful Fallback**: If no HuggingFace token (`HF_TOKEN`) is provided or PyAnnote fails, the system defaults to single-speaker fallback without breaking downstream analysis.

5. **Speaker & Segment Alignment (`ALIGNING`)**:
   - `app/services/aligner.py` calculates temporal overlap between Whisper transcript segments and PyAnnote speaker turns.
   - Assigns speaker labels (`Speaker 1`, `Speaker 2`, etc.) to each transcript segment.
   - Computes participation analytics: speaking time (seconds), percentage of total speech, turn count, and average turn duration per speaker.

6. **Semantic Chunking (`CHUNKING`)**:
   - `app/services/chunker.py` groups aligned segments into semantic text chunks of ~350 words with 40-word overlapping windows.
   - Preserves metadata for each chunk: segment IDs, exact start/end timestamps, and formatted speaker text blocks.

7. **LLM Structured Extraction (`ANALYZING`)**:
   - `app/services/llm_service.py` connects to the local Ollama daemon (`http://localhost:11434`) using model `qwen3:8b`.
   - Uses a **Map-Reduce** extraction workflow:
     1. Chunks are analyzed in parallel/sequence to extract candidate entities.
     2. A synthesis prompt aggregates chunk extractions into a unified meeting intelligence document.
   - Extracted entities saved to SQLite:
     - **Executive Summary** & Agenda Topics
     - **Key Discussion Points** (with category & timestamps)
     - **Key Decisions** (with context, impact, and direct evidence)
     - **Action Items** (Assignee, Priority, Deadline, Status)
     - **Important Dates & Schedules** (with ambiguity flag `needs_confirmation`)
     - **Strategic Takeaways & Open Questions**
     - **Sentiment & Tone Estimates** per speaker and overall meeting

8. **Vector Indexing (`INDEXING`)**:
   - `app/services/vector_store.py` converts semantic chunks into dense vector embeddings using `sentence-transformers/all-MiniLM-L6-v2`.
   - Creates a local FAISS `IndexFlatIP` index stored on disk at `./backend/data/vector_indices/meeting_{id}/`.

9. **Finalizing (`FINALIZING` -> `COMPLETED`)**:
   - SQLite status is updated to `COMPLETED`. Progress hits 100%. The Next.js frontend UI receives the completed state on its next poll and renders all meeting views.

---

## 4. Codebase Directory Structure & Module Guide

```text
MIS/
├── backend/                        # FastAPI Backend Application
│   ├── app/
│   │   ├── api/                    # API Route Handlers
│   │   │   ├── audio.py            # Audio streaming & file serving
│   │   │   ├── chat.py             # Local RAG chatbot endpoint & chat history
│   │   │   ├── export.py           # Markdown, JSON, and PDF export endpoints
│   │   │   ├── jobs.py             # Background job progress polling
│   │   │   ├── meetings.py         # Meeting CRUD, upload, speaker rename, extractions CRUD
│   │   │   ├── router.py           # Master API router uniting endpoints
│   │   │   └── settings.py         # System health, Ollama status, & config endpoints
│   │   ├── core/                   # System Core & Config
│   │   │   ├── config.py           # Pydantic BaseSettings, paths, environment variables
│   │   │   ├── database.py         # SQLAlchemy engine & session factory
│   │   │   └── logging.py          # Centralized logging setup
│   │   ├── models/                 # Database Schema
│   │   │   └── db_models.py        # SQLAlchemy ORM models (Meeting, Speaker, Segment, etc.)
│   │   ├── schemas/                # Pydantic Data Contracts
│   │   │   ├── analysis.py         # Pydantic extractions schemas for Ollama responses
│   │   │   ├── chat.py             # RAG Chat query & citation schemas
│   │   │   ├── job.py              # Processing job progress schemas
│   │   │   └── meeting.py          # Meeting request & response DTOs
│   │   ├── services/               # Core Processing Pipeline Engines
│   │   │   ├── aligner.py          # Whisper segment + PyAnnote speaker overlap alignment
│   │   │   ├── analytics_service.py# Participation stats & time calculations
│   │   │   ├── audio_processor.py  # FFmpeg audio normalization to 16kHz mono WAV
│   │   │   ├── chunker.py          # Metadata-preserving semantic chunker
│   │   │   ├── diarizer.py         # PyAnnote 3.1 speaker diarization wrapper
│   │   │   ├── export_service.py   # Markdown, JSON, and ReportLab PDF generators
│   │   │   ├── llm_service.py      # Ollama HTTP client & structured JSON extractions
│   │   │   ├── pipeline_worker.py  # Sequential background pipeline orchestrator
│   │   │   ├── transcriber.py      # faster-whisper STT engine wrapper
│   │   │   └── vector_store.py     # FAISS vector store & RAG Q&A engine
│   │   └── main.py                 # FastAPI app entry point & lifespan handler
│   ├── data/                       # Local Storage Directory (git-ignored)
│   │   ├── uploads/                # Raw user uploaded/recorded audio files
│   │   ├── processed/              # Normalized 16kHz mono WAV files
│   │   ├── vector_indices/         # FAISS vector indexes per meeting
│   │   └── mis.db                  # SQLite database file
│   ├── pytest.ini                  # Pytest configuration
│   └── requirements.txt            # Python dependencies
│
├── frontend/                       # Next.js Web Frontend
│   ├── src/
│   │   ├── app/                    # Next.js App Router Pages
│   │   │   ├── globals.css         # Tailwind & custom CSS styles
│   │   │   ├── layout.tsx          # Master application layout with navigation header
│   │   │   ├── page.tsx            # Main Dashboard & upload entry point
│   │   │   ├── meetings/
│   │   │   │   ├── page.tsx        # Meetings list with search & status filter
│   │   │   │   ├── new/page.tsx    # Dedicated recording/upload page
│   │   │   │   └── [id]/page.tsx   # Detailed Meeting Workspace (10 tabs + RAG Chatbot)
│   │   │   └── settings/page.tsx   # System settings, model checks, & configuration
│   │   ├── components/
│   │   │   ├── layout/Header.tsx   # Top navigation header component
│   │   │   ├── meetings/
│   │   │   │   ├── AnalyticsCharts.tsx    # Participation charts (Chart.js / SVG)
│   │   │   │   ├── AudioRecorder.tsx      # Browser Web Audio API mic recorder
│   │   │   │   ├── ChatPane.tsx           # Interactive RAG Chatbot drawer with citations
│   │   │   │   ├── ExtractionsList.tsx    # Interactive list editor for decisions/actions
│   │   │   │   ├── FileUploader.tsx       # Drag-and-drop file upload component
│   │   │   │   ├── MinutesView.tsx        # Formatted Minutes of Meeting (MoM) preview
│   │   │   │   ├── SpeakerRenameModal.tsx # Modal to customize speaker names
│   │   │   │   └── TranscriptView.tsx     # Synchronized interactive transcript viewer
│   │   │   └── ui/                        # Reusable UI primitives (Button, Card, Input, etc.)
│   │   └── lib/
│   │       ├── api.ts              # Axios/Fetch API client wrapping backend REST endpoints
│   │       ├── types.ts            # TypeScript interfaces matching backend Pydantic models
│   │       └── utils.ts            # Formatting utilities (timestamp, badge colors)
│   ├── package.json
│   └── tailwind.config.ts
│
├── docs/                           # Technical documentation & guides
├── scripts/                        # Utility startup scripts
└── docker-compose.yml              # Containerization orchestration file
```

---

## 5. Key System Features & Capabilities

### 🎙️ Browser Recording & File Ingestion
- Live microphone recording using HTML5 `MediaRecorder` API with real-time waveform visualization.
- Multi-format file upload supporting `.mp3`, `.wav`, `.m4a`, `.mp4`, `.webm`, `.flac`, `.ogg`, `.mkv`.

### 👥 Manual Speaker Renaming with Cascading Updates
- When PyAnnote labels speakers as `Speaker 1`, `Speaker 2`, users can click to rename them to real names (e.g., "Alice Smith").
- Modifying a speaker name updates the `Speaker` table and **instantly cascades across all associated transcript segments**, analytics charts, and Minutes of Meeting extractions.

### 🔍 Local RAG Meeting Chatbot with Timestamp Citations
- Uses sentence-transformers embeddings + FAISS vector search to retrieve relevant meeting chunks.
- Prompts Ollama `qwen3:8b` to answer questions strictly based on transcript evidence.
- Every response includes clickable timestamp citations (`[00:04:15]`) that immediately seek the HTML5 audio player to the exact audio moment.

### ✏️ Interactive Extraction Editor
- Users can edit, update, or delete AI-generated action items, decisions, key points, and dates directly in the web UI.

### 📄 Multi-Format Export
- **Markdown (`.md`)**: GitHub-flavored Minutes of Meeting with structured tables and appendix transcript.
- **JSON (`.json`)**: Complete raw structured database representation.
- **PDF (`.pdf`)**: Formatted document with headers, decision callout boxes, and action item tables generated via ReportLab.

---

## 6. VRAM Management & Resource Optimization

The system is specifically designed to run smoothly on PCs with modest hardware (e.g., **8 GB VRAM GPU** like RTX 4060):

1. **Sequential Execution**: Whisper transcription and PyAnnote diarization run sequentially.
2. **GPU Cache Flushing**: PyTorch VRAM is explicitly cleared via `torch.cuda.empty_cache()` and Python `gc.collect()` before Ollama LLM requests are dispatched.
3. **CPU Vector Embeddings**: Embeddings via `sentence-transformers` run on CPU, preserving GPU VRAM exclusively for Ollama LLM inference.
4. **Ollama Offloading**: Ollama automatically handles VRAM allocation and layer offloading for `qwen3:8b`.

---

## 7. Database Schema Reference (SQLite)

- **`meetings`**: Master meeting record (title, date, duration, processing status).
- **`recordings`**: File metadata (original filename, file path, normalized WAV path, size, duration).
- **`speakers`**: Speaker identity & participation stats (tag, display_name, speaking_time, turn_count, avg_turn_seconds, estimated_tone).
- **`transcript_segments`**: Timestamped transcript fragments (start_time, end_time, raw_text, cleaned_text, speaker_id, speaker_label).
- **`processing_jobs`**: Job status, progress percentage, active step, execution logs, and error messages.
- **`meeting_summaries`**: Executive summary, agenda topics, overall sentiment estimate.
- **`key_points`**: Key discussion items with source segment IDs and timestamps.
- **`decisions`**: Reached decisions with context, impact, and source evidence text.
- **`action_items`**: Action items with assignee, priority, deadline, status (`is_completed`), and source text.
- **`important_dates`**: Mentioned dates with `needs_confirmation` flag.
- **`scheduled_events`**: Upcoming events, dates, and participants.
- **`takeaways`**: Strategic takeaways.
- **`unresolved_questions`**: Open questions raised during the meeting.
- **`chat_messages`**: History of user RAG chatbot interactions and timestamp citations.
