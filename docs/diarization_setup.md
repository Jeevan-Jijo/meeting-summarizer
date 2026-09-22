# Speaker Diarization Setup (pyannote.audio 3.1)

Pyannote.audio provides open-weights speaker diarization to separate and label different speakers (*Speaker 1*, *Speaker 2*, etc.).

Because Pyannote is distributed under a gated Hugging Face license, a free Hugging Face token is required to download its weights for the first run.

---

## How to Enable Diarization

### Step 1: Create a Free Hugging Face Account
1. Go to [huggingface.co/join](https://huggingface.co/join).
2. Accept the user conditions on the model pages:
   - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)

### Step 2: Generate an Access Token
1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
2. Create a new token with **Read** permissions (e.g. named `pyannote-mis`).
3. Copy the token string (e.g., `hf_xxxxxxxxxxxxxxxxxxxxxx`).

### Step 3: Configure `HF_TOKEN`
You can provide the token in any of these ways:

#### Option A: In the `.env` file (Backend)
Open `backend/.env` (or project root `.env`) and set:
```env
HF_TOKEN=hf_your_actual_token_here
```

#### Option B: In Windows Environment Variable
In PowerShell:
```powershell
$env:HF_TOKEN = "hf_your_actual_token_here"
```
Or permanently in System Properties > Environment Variables.

---

## Graceful Fallback Mode (No Token)

If `HF_TOKEN` is not set or the user hasn't accepted the model terms:
- The system **will NOT fail** the meeting pipeline.
- It automatically marks speaker labels as `Unknown Speaker` (or single speaker).
- A warning badge is displayed in the UI informing the user that speaker separation requires an `HF_TOKEN`.
- Users can still manually rename speakers and review all transcripts, action items, summaries, and chat.
