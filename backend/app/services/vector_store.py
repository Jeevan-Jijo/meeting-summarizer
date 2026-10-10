import os
import pickle
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.services.audio_processor import format_timestamp
from app.schemas.chat import Citation
from app.services.llm_service import OllamaClient

_EMBEDDER_INSTANCE = None

class SimpleFallbackEmbedder:
    """Fast deterministic local fallback embedder for offline / test environments."""
    def __init__(self, dim: int = 384):
        self.dim = dim

    def encode(self, texts: List[str], convert_to_numpy: bool = True, normalize_embeddings: bool = True) -> np.ndarray:
        vectors = []
        for text in texts:
            vec = np.zeros(self.dim, dtype=np.float32)
            words = text.lower().split()
            for word in words:
                h = abs(hash(word)) % self.dim
                vec[h] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0 and normalize_embeddings:
                vec = vec / norm
            vectors.append(vec)
        return np.array(vectors, dtype=np.float32)

def get_embedder():
    """Load local sentence-transformers embedding model with robust offline fallback."""
    global _EMBEDDER_INSTANCE
    if _EMBEDDER_INSTANCE is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading sentence-transformers model '{settings.EMBEDDING_MODEL}' on {settings.EMBEDDING_DEVICE}...")
            # Set local_files_only or fast timeout
            _EMBEDDER_INSTANCE = SentenceTransformer(
                settings.EMBEDDING_MODEL,
                device=settings.EMBEDDING_DEVICE
            )
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer ({e}). Using deterministic local embedding fallback.")
            _EMBEDDER_INSTANCE = SimpleFallbackEmbedder(384)
    return _EMBEDDER_INSTANCE

class MeetingVectorStore:
    def __init__(self, meeting_id: int):
        self.meeting_id = meeting_id
        self.index_dir = settings.VECTOR_DIR / f"meeting_{meeting_id}"
        self.index_file = self.index_dir / "index.faiss"
        self.meta_file = self.index_dir / "metadata.pkl"
        self.index = None
        self.chunks_metadata: List[Dict[str, Any]] = []

    def build_index(self, chunks: List[Any]):
        """
        Build and save FAISS index for a meeting's transcript chunks.
        chunks: List of TranscriptChunk or dicts
        """
        import faiss

        if not chunks:
            logger.warning(f"No chunks to index for meeting {self.meeting_id}")
            return

        embedder = get_embedder()
        texts = []
        meta_list = []

        for chk in chunks:
            if hasattr(chk, "to_dict"):
                chk_dict = chk.to_dict()
            elif isinstance(chk, dict):
                chk_dict = chk
            else:
                # Handle SQLAlchemy TranscriptChunkModel or generic objects
                chk_dict = {
                    "chunk_index": getattr(chk, "chunk_index", 0),
                    "start_time": getattr(chk, "start_time", 0.0),
                    "end_time": getattr(chk, "end_time", 0.0),
                    "start_timestamp": format_timestamp(getattr(chk, "start_time", 0.0)),
                    "end_timestamp": format_timestamp(getattr(chk, "end_time", 0.0)),
                    "segment_ids": getattr(chk, "segment_ids", []),
                    "formatted_text": getattr(chk, "formatted_text", ""),
                    "word_count": getattr(chk, "word_count", 0)
                }
            texts.append(chk_dict["formatted_text"])
            meta_list.append(chk_dict)

        logger.info(f"Embedding {len(texts)} chunks for meeting {self.meeting_id}...")
        embeddings = embedder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        embeddings = np.ascontiguousarray(embeddings, dtype=np.float32)

        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)

        os.makedirs(self.index_dir, exist_ok=True)
        faiss.write_index(index, str(self.index_file))

        with open(self.meta_file, "wb") as f:
            pickle.dump(meta_list, f)

        self.index = index
        self.chunks_metadata = meta_list
        logger.info(f"Vector index saved for meeting {self.meeting_id} ({len(meta_list)} chunks).")

    def load_index(self) -> bool:
        """Load index and metadata from disk."""
        import faiss

        if not self.index_file.exists() or not self.meta_file.exists():
            return False

        try:
            self.index = faiss.read_index(str(self.index_file))
            with open(self.meta_file, "rb") as f:
                self.chunks_metadata = pickle.load(f)
            return True
        except Exception as e:
            logger.error(f"Failed to load vector index for meeting {self.meeting_id}: {e}")
            return False

    def delete_index(self) -> bool:
        """Delete FAISS index and metadata directory for this meeting."""
        import shutil
        if self.index_dir.exists():
            try:
                shutil.rmtree(self.index_dir)
                self.index = None
                self.chunks_metadata = []
                logger.info(f"Deleted vector index directory for meeting {self.meeting_id}")
                return True
            except Exception as e:
                logger.error(f"Error deleting vector index directory for meeting {self.meeting_id}: {e}")
                return False
        return False

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Search top-k most relevant chunks for the query."""
        if self.index is None:
            if not self.load_index():
                logger.warning(f"No index found for meeting {self.meeting_id}")
                return []

        embedder = get_embedder()
        query_vec = embedder.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        query_vec = np.ascontiguousarray(query_vec, dtype=np.float32)

        k = min(top_k, self.index.ntotal)
        if k == 0:
            return []

        scores, indices = self.index.search(query_vec, k)
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.chunks_metadata):
                item = dict(self.chunks_metadata[idx])
                item["similarity_score"] = float(scores[0][i])
                results.append(item)

        return results

    async def answer_question(self, query: str, meeting_title: str) -> Tuple[str, List[Citation]]:
        """
        Retrieve chunks and prompt Ollama to generate an evidence-backed answer with citations.
        """
        top_chunks = self.search(query, top_k=3)

        if not top_chunks:
            return "Information about this topic was not found in this meeting's recording.", []

        # Build context from top chunks
        context_blocks = []
        citations_map: List[Citation] = []

        for chk in top_chunks:
            start_ts = format_timestamp(chk["start_time"])
            end_ts = format_timestamp(chk["end_time"])
            ts_str = f"{start_ts} - {end_ts}"
            context_blocks.append(f"[Time: {ts_str}]\n{chk['formatted_text']}")
            
            citations_map.append(Citation(
                segment_id=chk["segment_ids"][0] if chk["segment_ids"] else None,
                start_time=chk["start_time"],
                end_time=chk["end_time"],
                timestamp_str=ts_str,
                speaker_label="Meeting Segment",
                text=chk["formatted_text"][:200] + "..." if len(chk["formatted_text"]) > 200 else chk["formatted_text"]
            ))

        rag_prompt = f"""
You are the Meeting Intelligence AI assistant. Answer the user's question accurately using ONLY the provided meeting excerpts.

Rules:
1. Base your answer strictly on the transcript excerpts below.
2. If the answer is not mentioned in or cannot be deduced from the excerpts, respond exactly: "This information was not found in the meeting recording."
3. Cite the relevant timestamps in your response using format [HH:MM:SS].
4. Keep the answer clear, helpful, and concise.

MEETING TITLE: {meeting_title}

RELEVANT MEETING EXCERPTS:
{chr(10).join(context_blocks)}

USER QUESTION:
{query}

ANSWER:
"""
        ollama = OllamaClient()
        model = await ollama.resolve_model()
        
        try:
            import httpx
            payload = {
                "model": model,
                "prompt": rag_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 1024
                }
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(f"{ollama.base_url}/api/generate", json=payload)
                if res.status_code == 200:
                    answer = res.json().get("response", "").strip()
                    return answer, citations_map
        except Exception as e:
            logger.error(f"Error calling Ollama for Q&A: {e}")

        # Fallback response
        return f"Based on the transcript excerpt around {citations_map[0].timestamp_str}: {top_chunks[0]['formatted_text'][:250]}...", citations_map
