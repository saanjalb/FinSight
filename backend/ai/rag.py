"""
Lightweight RAG (Retrieval-Augmented Generation) over finance-education notes.

Pipeline:
  documents (ai/knowledge/*.md)
    -> chunk (one chunk per "## " section)
    -> embed (Gemini gemini-embedding-001) -> vectors, cached on disk
    -> at question time: embed the question, cosine-similarity vs chunks
    -> top-k chunks go to Gemini as the ONLY allowed source of facts
    -> answer + the source chunks shown to the user

Deliberately small: with ~20 chunks, an in-memory numpy matrix is all the
"vector database" needed. A real vector DB (pgvector, Chroma...) becomes
worthwhile at thousands of chunks — swapping it in would only change
KnowledgeIndex.search().

Grounding: the prompt forbids using outside knowledge. If the retrieved
excerpts don't answer the question, the model must reply NOT_COVERED and
we show a "not in my notes" message instead of an answer.
"""
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
CACHE_PATH = KNOWLEDGE_DIR / ".embeddings_cache.json"
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIMS = 768  # recommended size for this model; smaller = faster + less storage
GEN_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
TOP_K = 3
NOT_COVERED = "NOT_COVERED"

# An embedder takes (texts, task_type) and returns one vector per text.
Embedder = Callable[[list[str], str], np.ndarray]


@dataclass
class Chunk:
    doc_title: str
    heading: str
    text: str

    @property
    def embed_text(self) -> str:
        # Prefixing the title gives the embedding context for short sections.
        return f"{self.doc_title} — {self.heading}: {self.text}"


def load_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        front = re.match(r"---\n(.*?)\n---\n(.*)", raw, re.S)
        meta, body = (front.group(1), front.group(2)) if front else ("", raw)
        title_match = re.search(r"^title:\s*(.+)$", meta, re.M)
        title = title_match.group(1).strip() if title_match else path.stem
        for section in re.split(r"^## ", body, flags=re.M)[1:]:
            heading, _, text = section.partition("\n")
            chunks.append(Chunk(title, heading.strip(), text.strip()))
    return chunks


def _normalize(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    return m / np.where(norms == 0, 1, norms)


def gemini_embedder(client) -> Embedder:
    from google.genai import types

    def embed(texts: list[str], task_type: str) -> np.ndarray:
        vectors = []
        for i in range(0, len(texts), 100):  # API batch limit
            batch = texts[i : i + 100]
            resp = client.models.embed_content(
                model=EMBED_MODEL,
                contents=batch,
                config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=EMBED_DIMS),
            )
            # Guard: some embedding models silently return 1 vector for a whole batch.
            if len(resp.embeddings) != len(batch):
                raise RuntimeError("Embedding API returned a different number of vectors than inputs.")
            vectors.extend(e.values for e in resp.embeddings)
        return _normalize(np.array(vectors, dtype=np.float32))

    return embed


class KnowledgeIndex:
    def __init__(self, chunks: list[Chunk], matrix: np.ndarray):
        self.chunks = chunks
        self.matrix = matrix  # shape (n_chunks, dims), rows unit-length

    def search(self, query_vec: np.ndarray, k: int = TOP_K) -> list[tuple[Chunk, float]]:
        # Unit vectors, so dot product == cosine similarity.
        scores = self.matrix @ query_vec
        top = np.argsort(scores)[::-1][:k]
        return [(self.chunks[i], float(scores[i])) for i in top]


_index: KnowledgeIndex | None = None


def build_index(embedder: Embedder, use_cache: bool = True) -> KnowledgeIndex:
    chunks = load_chunks()
    texts = [c.embed_text for c in chunks]
    key = hashlib.sha256(json.dumps([EMBED_MODEL, EMBED_DIMS, texts]).encode()).hexdigest()

    if use_cache and CACHE_PATH.exists():
        cached = json.loads(CACHE_PATH.read_text())
        if cached.get("key") == key:  # documents unchanged since last embedding
            return KnowledgeIndex(chunks, np.array(cached["vectors"], dtype=np.float32))

    matrix = embedder(texts, "RETRIEVAL_DOCUMENT")
    if use_cache:
        CACHE_PATH.write_text(json.dumps({"key": key, "vectors": matrix.tolist()}))
    return KnowledgeIndex(chunks, matrix)


def _build_prompt(question: str, hits: list[tuple[Chunk, float]]) -> str:
    excerpts = "\n\n".join(f"[{i}] ({c.doc_title}) {c.text}" for i, (c, _) in enumerate(hits, 1))
    return f"""You answer personal-finance education questions using ONLY the numbered excerpts below.

Rules:
- Use only facts stated in the excerpts. Do not use outside knowledge.
- If the excerpts do not contain the answer, reply with exactly {NOT_COVERED} and nothing else.
- Cite the excerpts you used like [1] or [2] after the relevant sentence.
- Keep it short and clear (3-5 sentences). Do not give personalised investment advice.

Excerpts:
{excerpts}

Question: {question}"""


def answer_question(question: str) -> dict:
    """Returns {"answer", "sources", "grounded"} or {"error"}."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY is not set. Add it to your .env file (see .env.example)."}

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        embedder = gemini_embedder(client)

        global _index
        if _index is None:
            _index = build_index(embedder)

        query_vec = embedder([question], "RETRIEVAL_QUERY")[0]
        hits = _index.search(query_vec)

        response = client.models.generate_content(model=GEN_MODEL, contents=_build_prompt(question, hits))
        answer = (response.text or "").strip()

        if not answer or answer == NOT_COVERED:
            return {
                "answer": "That isn't covered in my finance-education notes, so I won't guess. Try asking about compound interest, emergency funds, SIPs, inflation, fixed vs variable expenses, or the 50/30/20 rule.",
                "sources": [],
                "grounded": False,
            }

        # Show the excerpts the answer actually cited; fall back to all retrieved.
        cited = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
        shown = [h for i, h in enumerate(hits, 1) if i in cited] or hits
        return {
            "answer": answer,
            "grounded": True,
            "sources": [
                {"title": c.doc_title, "section": c.heading, "snippet": c.text, "similarity": round(score, 3)}
                for c, score in shown
            ],
        }

    except Exception as e:
        msg = str(e)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            return {"error": "Gemini free-tier rate limit reached. Wait a minute and try again."}
        if "API key" in msg or "401" in msg or "403" in msg:
            return {"error": "Gemini rejected the API key. Check GEMINI_API_KEY in your .env file."}
        return {"error": f"Knowledge assistant failed: {msg[:200]}"}
