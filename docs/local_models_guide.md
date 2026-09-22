# Local Models and Hardware Acceleration Guide

This system is completely local-first. No audio, transcripts, or queries leave your machine.

## Supported Models

| Task | Primary Local Model | Fallback Local Model | VRAM / RAM |
|---|---|---|---|
| **Speech-to-Text** | `openai/whisper-large-v3-turbo` | `base.en` or `small` | ~1.5 - 3.5 GB VRAM |
| **Speaker Diarization** | `pyannote/speaker-diarization-3.1` | Single/Turn Heuristic | ~1.2 GB VRAM / CPU |
| **LLM Reasoning** | `qwen3:8b` via Ollama | `qwen2.5:7b` / `llama3.2:3b` | ~5.2 GB VRAM |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | CPU fallback | ~120 MB RAM |

---

## 1. Setting Up Ollama & Qwen3:8b

1. Install Ollama from [ollama.com](https://ollama.com) (or check `ollama --version`).
2. Pull the model:
   ```bash
   ollama pull qwen3:8b
   ```
   *Note: If `qwen3:8b` is not yet available, you can also pull `qwen2.5:7b` or `llama3.2:3b`:*
   ```bash
   ollama pull qwen2.5:7b
   ```
3. Verify Ollama is serving on port 11434:
   ```bash
   curl http://localhost:11434/api/tags
   ```

---

## 2. Setting Up faster-whisper

- The system uses `faster-whisper` (CTranslate2 backend).
- By default, it detects CUDA support. If NVIDIA CUDA Toolkit and cuDNN libraries are present, it uses `cuda` with `float16`.
- If CUDA is not detected, it smoothly falls back to CPU computation with `int8` quantization.

---

## 3. Sequential GPU Execution

To prevent out-of-memory errors on 8 GB Laptop GPUs:
1. `faster-whisper` processes audio.
2. `pyannote.audio` processes audio.
3. GPU cache is cleared (`torch.cuda.empty_cache()`).
4. `Ollama` performs chunk and summary inference.
