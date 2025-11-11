# read_chunks.py
import os
import re
import json
import time
import math
import argparse
import traceback
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import faiss
from dotenv import load_dotenv
from urllib.parse import urlparse, urlunparse

# Load environment variables from .env (if present)
load_dotenv()


try:
    from sklearn.metrics.pairwise import cosine_similarity as sk_cosine
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

# sentence-transformers CrossEncoder (optional local reranker)
try:
    from sentence_transformers import CrossEncoder
    RERANKER_AVAILABLE = True
except Exception:
    RERANKER_AVAILABLE = False

# Optional HF text-generation backend
try:
    from transformers import pipeline as hf_pipeline, AutoTokenizer, AutoModelForCausalLM
    HF_AVAILABLE = True
except Exception:
    HF_AVAILABLE = False

# ---------- Defaults (override via CLI or env) ----------
DEFAULT_EMBED_URL = os.environ.get("EMBED_URL", "http://127.0.0.1:11434/api/embed")
DEFAULT_EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")

# Ollama generate endpoint/model defaults
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
DEFAULT_GEN_MODEL = os.environ.get("GEN_MODEL", "llama3.2")  # pick any local small instruct model you have

# Optional: comma-separated local models (for tooling / selection UIs). Read from .env if present.
_AVAILABLE_EMBEDS = os.environ.get("AVAILABLE_EMBED_MODELS", "")
AVAILABLE_EMBED_MODELS = [s.strip() for s in _AVAILABLE_EMBEDS.split(",") if s.strip()] if _AVAILABLE_EMBEDS else []

# I/O defaults (can be overridden via .env or CLI)
JSON_DIR = os.environ.get("JSON_DIR", "json_output")
OUT_PARQUET = os.environ.get("OUT_PARQUET", "embeddings.parquet")
OUT_NPY = os.environ.get("OUT_NPY", "embeddings.npy")
OUT_FAISS = os.environ.get("OUT_FAISS", "vector_index.faiss")

# Chunking defaults
CHUNK_TARGET_TOKENS = int(os.environ.get("CHUNK_TARGET_TOKENS", "500"))
CHUNK_OVERLAP_RATIO = float(os.environ.get("CHUNK_OVERLAP_RATIO", "0.25"))

# Small batch sizes for low-RAM CPU usage
EMBED_BATCH_SIZE = int(os.environ.get("EMBED_BATCH_SIZE", "4"))

# HTTP robustness
EMBED_TIMEOUT_SECS = int(os.environ.get("EMBED_TIMEOUT_SECS", "60"))
RETRY_ATTEMPTS = int(os.environ.get("RETRY_ATTEMPTS", "4"))
RETRY_BACKOFF_BASE = float(os.environ.get("RETRY_BACKOFF_BASE", "2.0"))

# Safety/truncation (Ollama may 500 on very long inputs)
MAX_CHARS_PER_TEXT = int(os.environ.get("MAX_CHARS_PER_TEXT", "6000"))

# Pacing delay between embedding batches (helps with flakiness on CPU)
INTER_BATCH_SLEEP = float(os.environ.get("INTER_BATCH_SLEEP", "0.05"))

# ---------- Token counter (approx) ----------
def _load_tokenizer():
    try:
        import tiktoken
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None

_TOK = _load_tokenizer()

def count_tokens(text: str) -> int:
    if _TOK:
        return len(_TOK.encode(text))
    return max(1, math.ceil(len(text) / 4))

# ---------- Cleaning ----------
TIMESTAMP_RE = re.compile(
    r"""
    (\[?\(?\b(?:\d{1,2}:){1,2}\d{2}\b\)?\]?) |   # [HH:MM:SS] / (MM:SS) / HH:MM:SS / MM:SS
    (\b\d{1,2}h\d{2}m(?:\d{2}s)?\b)              # 1h23m45s / 01h02m
    """,
    re.VERBOSE | re.IGNORECASE
)

FILLERS = {
    "uh", "um", "erm", "er", "ah", "eh", "hmm",
    "you know", "like", "so yeah", "sort of", "kind of", "i mean",
    "okay", "ok", "right", "yeah", "y'know"
}

def clean_text(raw: str) -> str:
    if not raw:
        return ""
    text = TIMESTAMP_RE.sub(" ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    # multi-word first
    for phrase in sorted([f for f in FILLERS if " " in f], key=len, reverse=True):
        text = re.sub(rf"(?i)\b{re.escape(phrase)}\b", " ", text)
    # single words
    toks = text.split()
    toks = [t for t in toks if re.sub(r"[^\w']", "", t.lower()) not in FILLERS]
    text = " ".join(toks)
    return re.sub(r"\s+", " ", text).strip()

def sec_to_hhmmss(v):
    if v is None:
        return None
    try:
        v = float(v)
    except Exception:
        return None
    v = max(0, int(round(v)))
    h = v // 3600
    m = (v % 3600) // 60
    s = v % 60
    return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

# ---------- JSON loader ----------
def load_sentences_from_json(filepath: str) -> List[Dict[str, Any]]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = None
    if isinstance(data, dict):
        if "chunks" in data and isinstance(data["chunks"], list):
            items = data["chunks"]
        elif "segments" in data and isinstance(data["segments"], list):
            items = data["segments"]

    if items is None:
        raise ValueError(f"{os.path.basename(filepath)}: expected 'chunks' or 'segments'")

    out = []
    for item in items:
        text = clean_text(item.get("text", "") or "")
        if not text:
            continue
        out.append({
            "text": text,
            "start": item.get("start"),
            "end": item.get("end")
        })
    return out

# ---------- Chunking (500 tokens, ~25% overlap) ----------
def chunk_sentences(sentences: List[Dict[str, Any]],
                    target_tokens: int = CHUNK_TARGET_TOKENS,
                    overlap_ratio: float = CHUNK_OVERLAP_RATIO) -> List[Dict[str, Any]]:
    chunks = []
    buf_t, buf_s, buf_e = [], [], []
    buf_tok = 0

    def flush():
        if not buf_t:
            return None
        t = " ".join(buf_t).strip()
        starts = [x for x in buf_s if x is not None]
        ends = [x for x in buf_e if x is not None]
        return {
            "text": t,
            "start": min(starts) if starts else None,
            "end": max(ends) if ends else None,
            "tokens": count_tokens(t)
        }

    i = 0
    while i < len(sentences):
        s = sentences[i]
        t = s["text"]
        tok = count_tokens(t)

        if buf_tok + tok <= target_tokens or not buf_t:
            buf_t.append(t); buf_s.append(s.get("start")); buf_e.append(s.get("end"))
            buf_tok += tok; i += 1
        else:
            ch = flush()
            if ch: chunks.append(ch)
            keep = int(round(ch["tokens"] * overlap_ratio)) if ch else 0
            nt, ns, ne, nk = [], [], [], 0
            for j in range(len(buf_t)-1, -1, -1):
                t_j = count_tokens(buf_t[j])
                if nk + t_j > keep and nt:
                    break
                nt.insert(0, buf_t[j]); ns.insert(0, buf_s[j]); ne.insert(0, buf_e[j])
                nk += t_j
            buf_t, buf_s, buf_e = nt[:], ns[:], ne[:]
            buf_tok = sum(count_tokens(x) for x in buf_t)

    ch = flush()
    if ch: chunks.append(ch)
    return chunks

# ---------- Ollama embeddings (robust) ----------
def _truncate_texts(texts: List[str], max_chars: int) -> List[str]:
    if max_chars and max_chars > 0:
        return [t[:max_chars] for t in texts]
    return texts

_SESSION = requests.Session()

def _embed_batch(texts: List[str], embed_url: str, embed_model: str, timeout: int) -> List[List[float]]:
    payload = {
        "model": embed_model,
        "input": texts,
        "options": {"num_gpu": 0},  # CPU only
    }
    r = _SESSION.post(embed_url, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    embs = data.get("embeddings") or data.get("data")
    if not isinstance(embs, list):
        raise RuntimeError(f"Unexpected embed response: keys={list(data.keys())}")
    return embs

def _embed_with_retries(texts: List[str], embed_url: str, embed_model: str, timeout: int) -> List[List[float]]:
    last_exc = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return _embed_batch(texts, embed_url, embed_model, timeout)
        except Exception as e:
            last_exc = e
            time.sleep(RETRY_BACKOFF_BASE ** (attempt - 1))
    raise RuntimeError(f"Embed failed after {RETRY_ATTEMPTS} attempts: {last_exc}")

def create_embeddings(text_list: List[str],
                      embed_url: str,
                      embed_model: str,
                      timeout: int,
                      adaptive_split: bool = True,
                      max_chars_per_text: int = MAX_CHARS_PER_TEXT) -> List[List[float]]:
    texts = _truncate_texts(text_list, max_chars_per_text)

    if not adaptive_split:
        return _embed_with_retries(texts, embed_url, embed_model, timeout)

    # Try in one go; if fails, binary split down to singles
    def recurse(batch: List[str]) -> List[List[float]]:
        try:
            return _embed_with_retries(batch, embed_url, embed_model, timeout)
        except Exception:
            if len(batch) == 1:
                raise
            mid = len(batch) // 2
            left = recurse(batch[:mid])
            right = recurse(batch[mid:])
            return left + right

    return recurse(texts)

def create_embeddings_batched(texts: List[str],
                              embed_url: str,
                              embed_model: str,
                              batch_size: int,
                              timeout: int) -> List[List[float]]:
    out: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        out.extend(create_embeddings(batch, embed_url, embed_model, timeout))
        if INTER_BATCH_SLEEP:
            time.sleep(INTER_BATCH_SLEEP)
    return out

# ---------- FAISS helpers ----------
def build_faiss_ip_index(emb_matrix: np.ndarray) -> faiss.IndexFlatIP:
    em = emb_matrix.astype("float32", copy=True)
    faiss.normalize_L2(em)   # cosine via IP
    index = faiss.IndexFlatIP(em.shape[1])
    index.add(em)
    return index

def search_index(index: faiss.IndexFlatIP, q_vecs: np.ndarray, top_k: int = 5):
    q = q_vecs.astype("float32", copy=True)
    faiss.normalize_L2(q)
    scores, idxs = index.search(q, top_k)
    return scores, idxs

# ---------- Pipeline ----------
def process_json_dir(json_dir: str,
                     embed_url: str,
                     embed_model: str,
                     batch_size: int,
                     max_chars_per_text: int) -> pd.DataFrame:
    files = [f for f in os.listdir(json_dir) if f.endswith(".json")]
    if not files:
        raise FileNotFoundError(f"No .json files found in {json_dir}")

    rows = []
    cid = 0

    for fname in sorted(files):
        path = os.path.join(json_dir, fname)
        base = os.path.splitext(fname)[0]
        title = base.rsplit("_", 1)[0] if "_" in base else base

        sents = load_sentences_from_json(path)
        if not sents:
            continue

        chunks = chunk_sentences(sents, CHUNK_TARGET_TOKENS, CHUNK_OVERLAP_RATIO)
        texts = [(c["text"][:max_chars_per_text] if c["text"] else "") for c in chunks]

        embs = create_embeddings_batched(
            texts,
            embed_url=embed_url,
            embed_model=embed_model,
            batch_size=batch_size,
            timeout=EMBED_TIMEOUT_SECS
        )

        if len(embs) != len(chunks):
            raise RuntimeError(f"Embeddings mismatch for {fname}: {len(embs)} vs {len(chunks)}")

        for c, e in zip(chunks, embs):
            rows.append({
                "chunk_id": cid,
                "title": title,
                "chunk": c["text"],
                "start_sec": c["start"],
                "end_sec": c["end"],
                "start": sec_to_hhmmss(c["start"]),
                "end": sec_to_hhmmss(c["end"]),
                "tokens": c["tokens"],
                "embedding": e
            })
            cid += 1

    return pd.DataFrame(rows)

def save_artifacts(df: pd.DataFrame) -> Tuple[np.ndarray, faiss.IndexFlatIP]:
    df.to_parquet(OUT_PARQUET, index=False)
    emb = np.array(df["embedding"].tolist(), dtype=np.float32)
    np.save(OUT_NPY, emb)
    index = build_faiss_ip_index(emb)
    faiss.write_index(index, OUT_FAISS)
    return emb, index

# ---------- Query & optional rerank ----------
def embed_query(text: str, embed_url: str, embed_model: str) -> np.ndarray:
    embs = create_embeddings([text], embed_url, embed_model, EMBED_TIMEOUT_SECS)
    return np.array(embs, dtype=np.float32)  # (1, d)

def try_init_reranker(model_name: str, device: str = "cpu"):
    if not RERANKER_AVAILABLE:
        return None
    try:
        return CrossEncoder(model_name, device=device)
    except Exception:
        return None

def rerank_crossencoder(query: str, docs: List[str], reranker, batch_size: int = 8) -> List[Dict[str, float]]:
    pairs = [(query, d) for d in docs]
    scores = reranker.predict(pairs, batch_size=batch_size)
    return [{"index": i, "score": float(s)} for i, s in enumerate(scores)]

def print_hits(df: pd.DataFrame, idxs: np.ndarray, scores: np.ndarray, header: str, limit: int):
    print(f"\n{header}\n")
    idxs = idxs.ravel()[:limit]
    scores = scores.ravel()[:limit]
    for rank, (i, s) in enumerate(zip(idxs, scores), start=1):
        row = df.iloc[i]
        print(f"{rank}. score={s:.4f} | {row['title']} | {row['start']}–{row['end']} | chunk_id={row['chunk_id']}")
        print(row["chunk"][:500], "...")
        print("-" * 80)

def search_with_optional_rerank(query: str,
                                df: pd.DataFrame,
                                index: faiss.IndexFlatIP,
                                embed_url: str,
                                embed_model: str,
                                top_k: int = 50,
                                final_k: int = 5,
                                no_rerank: bool = False,
                                rerank_model: str = "BAAI/bge-reranker-base",
                                rerank_batch: int = 8):
    q = embed_query(query, embed_url, embed_model)
    scores, idxs = search_index(index, q, top_k=top_k)
    print_hits(df, idxs, scores, "=== ANN RESULTS (cosine via L2-norm + IP) ===", final_k)

    if no_rerank:
        return idxs.ravel(), scores.ravel()

    reranker = try_init_reranker(rerank_model, device="cpu")
    if reranker is None:
        print("\n[Info] Reranker unavailable. Install `sentence-transformers` to enable local reranking, "
              "or run with --no_rerank.\n")
        return idxs.ravel(), scores.ravel()

    docs = [df.iloc[i]["chunk"] for i in idxs.ravel()]
    rr = rerank_crossencoder(query, docs, reranker, batch_size=rerank_batch)
    rr_sorted = sorted(rr, key=lambda x: x["score"], reverse=True)[:final_k]

    print("\n=== RERANKED RESULTS (CrossEncoder on CPU) ===\n")
    top_indices = []
    top_scores = []
    for rank, item in enumerate(rr_sorted, start=1):
        i_local = idxs.ravel()[item["index"]]
        row = df.iloc[i_local]
        print(f"{rank}. score={item['score']:.4f} | {row['title']} | {row['start']}–{row['end']} | chunk_id={row['chunk_id']}")
        print(row["chunk"][:500], "...")
        print("-" * 80)
        top_indices.append(i_local)
        top_scores.append(item["score"])

    # If sklearn is there, sanity-check agreement
    if SKLEARN_AVAILABLE:
        emb = np.array(df["embedding"].tolist(), dtype=np.float32)
        faiss.normalize_L2(emb)
        sk = sk_cosine(emb, q).ravel()
        alt_top = np.argsort(sk)[::-1][:final_k]
        print("\n[Check] sklearn cosine top IDs:", alt_top.tolist())

    return np.array(top_indices, dtype=int), np.array(top_scores, dtype=float)

# ---------- Answer generation ----------
def build_prompt(query: str,
                 contexts: List[Dict[str, Any]],
                 max_ctx_chars: int = 4000) -> str:
    """
    Build a compact prompt with top contexts and inline provenance.
    """
    # Concatenate contexts with lightweight citations
    pieces = []
    used = 0
    for c in contexts:
        meta = f"[{c['title']} | {c['start']}–{c['end']} | chunk_id={c['chunk_id']}]"
        block = f"{meta}\n{c['chunk']}\n"
        if used + len(block) > max_ctx_chars and len(pieces) > 0:
            break
        pieces.append(block)
        used += len(block)

    context_text = "\n---\n".join(pieces)

    sys = (
        "You are a helpful assistant. Answer the user's question using ONLY the provided transcript excerpts. "
        "Cite evidence inline using the given [title | start–end | chunk_id] tags. "
        "If the answer isn't in the excerpts, say you don't have enough information."
    )
    prompt = (
        f"{sys}\n\n"
        f"Question:\n{query}\n\n"
        f"Transcript excerpts:\n{context_text}\n\n"
        f"Answer (include brief citations like [chunk_id=12] where relevant):"
    )
    return prompt

def answer_via_ollama(prompt: str,
                      ollama_url: str = DEFAULT_OLLAMA_URL,
                      model: str = DEFAULT_GEN_MODEL,
                      keep_alive: int = 0,
                      timeout: int = 120) -> str:
    # We'll try multiple candidate endpoints (useful if the configured URL is slightly off)
    parsed = urlparse(ollama_url)
    base = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
    candidates = [
        ollama_url,
        base + "/generate",
        base + "/api/generate",
        base + "/api/completions",
        base + "/completions",
    ]

    # Try a few payload shapes to support different servers (Ollama, TGI/HF, OpenAI-like)
    payload_variants = [
        {"model": model, "prompt": prompt, "stream": False, "keep_alive": keep_alive},
        {"model": model, "input": prompt},
        {"inputs": prompt},
        {"prompt": prompt},
        {"text": prompt},
        {"input": prompt},
    ]

    last_exc = None
    data = None
    working_url = None
    working_body = None

    def _post(url: str, body: dict):
        r = requests.post(url, json=body, timeout=timeout)
        # allow non-2xx to raise so we can move to next candidate
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return r.text

    for url in candidates:
        for body in payload_variants:
            try:
                data = _post(url, body)
                # got a response (200) — success!
                working_url = url
                working_body = body
                break
            except Exception as e:
                last_exc = e
                # try next body/endpoint
                continue
        if data is not None:
            break

    if data is None:
        # No successful candidate — surface the last exception
        if last_exc:
            raise last_exc
        raise RuntimeError(f"Failed to generate answer: no working endpoint found among {candidates}")

    # Debug: print working endpoint (optional; can remove later)
    # print(f"[DEBUG] Generation endpoint: {working_url}")


    # Normalize common response formats
    if isinstance(data, dict):
        # OpenAI-like completions: {"choices": [{"text": ...}]}
        if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
            first = data["choices"][0]
            return (first.get("text") or first.get("message", {}).get("content") or "").strip()

        # Ollama: {"response": "..."}
        if "response" in data:
            return str(data.get("response", "")).strip()

        # HF/TGI sometimes: {"generated_text": "..."} or {"results": [{"generated_text": "..."}]}
        if "generated_text" in data:
            return str(data.get("generated_text", "")).strip()
        if "results" in data and isinstance(data["results"], list) and data["results"]:
            return str(data["results"][0].get("generated_text") or data["results"][0].get("text") or "").strip()

        # Some endpoints return {"response":"..."} or {"output":"..."}
        if "output" in data:
            return str(data.get("output", "")).strip()

        # Fallback: find first string value in dict
        for k, v in data.items():
            if isinstance(v, str) and v.strip():
                return v.strip()

        return str(data)

    # If we got plain text
    return str(data)

def answer_via_hf(prompt: str,
                  model_name: str,
                  max_new_tokens: int = 256,
                  temperature: float = 0.2) -> Optional[str]:
    if not HF_AVAILABLE:
        return None
    try:
        pipe = hf_pipeline(
            "text-generation",
            model=model_name,
            device_map="auto" if os.environ.get("HF_DEVICE_MAP_AUTO") else None,
            torch_dtype=None
        )
        out = pipe(prompt, max_new_tokens=max_new_tokens, do_sample=(temperature > 0.0), temperature=temperature)
        if isinstance(out, list) and len(out) and "generated_text" in out[0]:
            return out[0]["generated_text"][len(prompt):].strip()
        # Some models return dict structure differently
        if isinstance(out, list) and len(out) and isinstance(out[0], dict):
            # try best-effort
            return (out[0].get("generated_text") or "").strip()
        return None
    except Exception:
        return None

def generate_answer(query: str,
                    df: pd.DataFrame,
                    hit_indices: np.ndarray,
                    max_ctx_chars: int,
                    backend: str = "ollama",
                    gen_model: str = DEFAULT_GEN_MODEL,
                    ollama_url: str = DEFAULT_OLLAMA_URL) -> str:
    contexts = []
    for i in hit_indices:
        row = df.iloc[int(i)]
        contexts.append({
            "title": row["title"],
            "start": row["start"],
            "end": row["end"],
            "chunk_id": int(row["chunk_id"]),
            "chunk": row["chunk"]
        })
    prompt = build_prompt(query, contexts, max_ctx_chars=max_ctx_chars)

    if backend == "ollama":
        return answer_via_ollama(prompt, ollama_url=ollama_url, model=gen_model)
    elif backend == "hf":
        ans = answer_via_hf(prompt, model_name=gen_model)
        if ans is None or len(ans.strip()) == 0:
            return "[Generation failed with HF backend]"
        return ans
    else:
        return "[No generation backend selected]"

# ---------- Main ----------
def main():
    p = argparse.ArgumentParser(description="CPU-friendly RAG: clean+chunk+embed (Ollama) + FAISS + optional rerank + answer generation.")
    p.add_argument("--json_dir", default=JSON_DIR, help="Directory with transcript JSON.")
    p.add_argument("--embed_url", default=DEFAULT_EMBED_URL, help="Ollama embed endpoint (e.g., http://127.0.0.1:11434/api/embed)")
    p.add_argument("--embed_model", default=DEFAULT_EMBED_MODEL, help="Embedding model in Ollama (e.g., bge-m3)")
    p.add_argument("--batch_size", type=int, default=EMBED_BATCH_SIZE, help="Embed batch size (small for CPU)")
    p.add_argument("--max_chars", type=int, default=MAX_CHARS_PER_TEXT, help="Truncate each chunk to this many chars")

    p.add_argument("--query", default=None, help="Optional query to test retrieval")
    p.add_argument("--top_k", type=int, default=5, help="Top-k to display / pass to generator")
    p.add_argument("--rebuild", action="store_true", help="Force rebuild from JSON")

    # Rerank
    p.add_argument("--no_rerank", action="store_true", help="Disable CrossEncoder reranking")
    p.add_argument("--rerank_model", default="BAAI/bge-reranker-base", help="sentence-transformers CrossEncoder name")
    p.add_argument("--rerank_batch", type=int, default=8, help="CrossEncoder predict batch size (CPU)")

    # Generation
    p.add_argument("--answer", action="store_true", help="Generate an answer from the top passages")
    p.add_argument("--gen_backend", choices=["ollama", "hf", "none"], default="ollama", help="Generator backend")
    p.add_argument("--gen_model", default=DEFAULT_GEN_MODEL, help="Generator model (Ollama model name or HF model id)")
    p.add_argument("--ollama_url", default=DEFAULT_OLLAMA_URL, help="Ollama /api/generate endpoint")
    p.add_argument("--max_ctx_chars_for_prompt", type=int, default=4000, help="Max chars of retrieved context in the prompt")
    args = p.parse_args()

    embed_url = args.embed_url
    embed_model = args.embed_model
    batch_size = max(1, int(args.batch_size))
    max_chars = max(1, int(args.max_chars))

    need_build = args.rebuild or not (os.path.exists(OUT_PARQUET) and os.path.exists(OUT_NPY) and os.path.exists(OUT_FAISS))

    if need_build:
        print(f"Processing JSON from: {args.json_dir}")
        df = process_json_dir(args.json_dir, embed_url, embed_model, batch_size, max_chars)
        print(f"Chunks processed: {df.shape[0]}")
        emb_matrix, index = save_artifacts(df)
        print(f"Saved {OUT_PARQUET}, {OUT_NPY}, {OUT_FAISS}")
    else:
        print("Loading existing artifacts...")
        df = pd.read_parquet(OUT_PARQUET)
        emb_matrix = np.load(OUT_NPY).astype(np.float32)
        index = build_faiss_ip_index(emb_matrix)

    if args.query:
        hit_indices, _ = search_with_optional_rerank(
            args.query, df, index,
            embed_url=embed_url,
            embed_model=embed_model,
            top_k=max(args.top_k, 5),
            final_k=args.top_k,
            no_rerank=args.no_rerank,
            rerank_model=args.rerank_model,
            rerank_batch=args.rerank_batch
        )

        if args.answer:
            print("\n=== GENERATED ANSWER ===\n")
            try:
                ans = generate_answer(
                    args.query,
                    df,
                    hit_indices=hit_indices[:args.top_k],
                    max_ctx_chars=args.max_ctx_chars_for_prompt,
                    backend=args.gen_backend,
                    gen_model=args.gen_model,
                    ollama_url=args.ollama_url
                )
                print(ans.strip() if ans else "[No answer returned]")
                print("\n========================\n")
            except requests.HTTPError as e:
                print(f"[Generation HTTP error] {e}")
            except Exception as e:
                print(f"[Generation failed] {type(e).__name__}: {e}")
    else:
        print("Ready. Provide --query 'your question' to test retrieval. Use --answer to generate a response.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n[Fatal Error]")
        print(type(e).__name__, str(e))
        traceback.print_exc()
        raise
