# read_chunks.py
import os
import re
import json
import time
import math
from typing import List, Dict, Any, Tuple

import numpy as np
import pandas as pd
import requests
import faiss
from dotenv import load_dotenv

load_dotenv()

# =========================
# Defaults (env-overridable)
# =========================
DEFAULT_EMBED_URL = os.environ.get("EMBED_URL", "http://127.0.0.1:11434/api/embed")
DEFAULT_EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text:latest")

# IMPORTANT: pass the BASE (host:port) or a full endpoint; we normalize it.
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
DEFAULT_GEN_MODEL = os.environ.get("GEN_MODEL", "llama3.2:3b")

JSON_DIR = os.environ.get("JSON_DIR", "json_output")
OUT_PARQUET = os.environ.get("OUT_PARQUET", "embeddings.parquet")
OUT_NPY = os.environ.get("OUT_NPY", "embeddings.npy")
OUT_FAISS = os.environ.get("OUT_FAISS", "vector_index.faiss")

CHUNK_TARGET_TOKENS = int(os.environ.get("CHUNK_TARGET_TOKENS", "500"))
CHUNK_OVERLAP_RATIO = float(os.environ.get("CHUNK_OVERLAP_RATIO", "0.25"))

EMBED_TIMEOUT_SECS = int(os.environ.get("EMBED_TIMEOUT_SECS", "60"))
MAX_CHARS_PER_TEXT = int(os.environ.get("MAX_CHARS_PER_TEXT", "4000"))
INTER_BATCH_SLEEP = float(os.environ.get("INTER_BATCH_SLEEP", "0.15"))

# Generation options (forwarded to Ollama via "options")
GEN_NUM_CTX = int(os.environ.get("GEN_NUM_CTX", "2048"))
GEN_NUM_PREDICT = int(os.environ.get("GEN_NUM_PREDICT", "256"))
# Force CPU if your GPU VRAM is low: set to 0. (You can also export OLLAMA_NUM_GPU=0)
GEN_GPU_LAYERS = os.environ.get("GEN_GPU_LAYERS")  # None or int as string

# ==========
# Tokenizer
# ==========
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
    return max(1, math.ceil(len(text) / 4))  # rough fallback

# ==========================
# JSON and text pre-processing
# ==========================
TIMESTAMP_RE = re.compile(r"(\[?\(?\b(?:\d{1,2}:){1,2}\d{2}\b\)?\]?)")

def clean_text(raw: str) -> str:
    if not raw:
        return ""
    text = TIMESTAMP_RE.sub(" ", raw)
    return re.sub(r"\s+", " ", text).strip()

def sec_to_hhmmss(v):
    if v is None:
        return None
    v = int(max(0, round(float(v))))
    h, r = divmod(v, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def load_sentences_from_json(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("chunks") or data.get("segments")
    if not items:
        return []
    out = []
    for it in items:
        t = clean_text(it.get("text",""))
        if t:
            out.append({"text": t, "start": it.get("start"), "end": it.get("end")})
    return out

# =====================
# Chunking with overlap
# =====================
def _flush_chunk(buf, starts, ends):
    if not buf:
        return None
    txt = " ".join(buf)
    return {
        "text": txt,
        "start": min(starts) if starts else None,
        "end": max(ends) if ends else None,
        "tokens": count_tokens(txt)
    }

def chunk_sentences(sents, target_tokens=CHUNK_TARGET_TOKENS, overlap_ratio=CHUNK_OVERLAP_RATIO):
    """
    Token-budget chunker with overlap by reusing the tail of the previous chunk.
    """
    if not sents:
        return []

    chunks = []
    i = 0
    n = len(sents)
    s_tok = [(s["text"], count_tokens(s["text"]), s.get("start"), s.get("end")) for s in sents]

    while i < n:
        buf = []
        starts, ends = [], []
        tok = 0
        j = i
        while j < n:
            t, nt, st, en = s_tok[j]
            if not buf or tok + nt <= target_tokens:
                buf.append(t); starts.append(st); ends.append(en); tok += nt
                j += 1
            else:
                break
        ch = _flush_chunk(buf, starts, ends)
        if ch:
            chunks.append(ch)

        if j >= n:
            break

        if overlap_ratio > 0 and buf:
            keep = max(1, int(round(len(buf) * overlap_ratio)))
            i = j - keep
        else:
            i = j

    return chunks

# ===============
# Embedding calls
# ===============
def _embed_batch(texts: List[str], url: str, model: str):
    """
    Call Ollama embed; if model missing, auto-pull and retry once.
    """
    try:
        r = requests.post(url, json={"model": model, "input": texts}, timeout=EMBED_TIMEOUT_SECS)
        r.raise_for_status()
        data = r.json()
        return data["embeddings"]
    except requests.exceptions.HTTPError as e:
        # If embed model missing, try to pull and retry
        status = getattr(e.response, "status_code", None)
        body = e.response.text if getattr(e, "response", None) is not None else ""
        base = _normalize_base_url(url)
        missing_hint = status in (400, 404) and ("not found" in body.lower() or "unknown model" in body.lower())
        if missing_hint:
            print(f"[INFO] Embedding model '{model}' missing. Attempting to pull...")
            if _ensure_model_present(base, model):
                r2 = requests.post(url, json={"model": model, "input": texts}, timeout=EMBED_TIMEOUT_SECS)
                r2.raise_for_status()
                data2 = r2.json()
                return data2["embeddings"]
        # Otherwise, re-raise original
        raise

def create_embeddings(texts: List[str], url=DEFAULT_EMBED_URL, model=DEFAULT_EMBED_MODEL):
    out = []
    for t in texts:
        out.extend(_embed_batch([t[:MAX_CHARS_PER_TEXT]], url, model))
        time.sleep(INTER_BATCH_SLEEP)
    return out

# ==========
# FAISS bits
# ==========
def build_faiss_ip_index(emb: np.ndarray):
    emb = emb.astype("float32", copy=True)
    faiss.normalize_L2(emb)
    idx = faiss.IndexFlatIP(emb.shape[1])
    idx.add(emb)
    return idx

# ==========================
# Pipeline: process JSON dir
# ==========================
def process_json_dir(json_dir, embed_url, embed_model, max_chars=MAX_CHARS_PER_TEXT):
    files = [f for f in os.listdir(json_dir) if f.lower().endswith(".json")]
    rows = []
    cid = 0
    for fname in sorted(files):
        fp = os.path.join(json_dir, fname)
        sents = load_sentences_from_json(fp)
        chunks = chunk_sentences(sents, CHUNK_TARGET_TOKENS, CHUNK_OVERLAP_RATIO)
        texts = [c["text"][:max_chars] for c in chunks]
        if not texts:
            continue
        embs = create_embeddings(texts, embed_url, embed_model)
        for c, e in zip(chunks, embs):
            rows.append({
                "chunk_id": cid,
                "title": fname,
                "chunk": c["text"],
                "start": sec_to_hhmmss(c["start"]),
                "end": sec_to_hhmmss(c["end"]),
                "embedding": e
            })
            cid += 1
    return pd.DataFrame(rows)

def save_artifacts(df: pd.DataFrame):
    df.to_parquet(OUT_PARQUET, index=False)
    emb = np.array(df["embedding"].tolist(), dtype=np.float32)
    np.save(OUT_NPY, emb)
    idx = build_faiss_ip_index(emb)
    faiss.write_index(idx, OUT_FAISS)
    return emb, idx

# ===============
# Query-time ops
# ===============
def embed_query(text: str, url=DEFAULT_EMBED_URL, model=DEFAULT_EMBED_MODEL):
    return np.array(create_embeddings([text], url, model), dtype=np.float32)

def search_index(index: faiss.Index, q: np.ndarray, k: int):
    q = q.astype("float32")
    faiss.normalize_L2(q)
    return index.search(q, k)  # (D, I)

# ==================
# Prompt + Generation
# ==================
def build_prompt(query: str, contexts: List[Dict[str, Any]], limit: int = 4000):
    intro = "Answer the question using ONLY the information from the provided transcript excerpts. Provide a clear, direct answer without including chunk IDs, prefixes, or phrases like 'I would suggest' or 'the following answer'. Just provide the answer directly."
    parts = []
    used = 0
    intro_len = len(intro) + len(f"\n\nQuestion: {query}\n\nContext:\n") + len("\n\nAnswer:")
    available = limit - intro_len - 200  # Reserve some space
    
    for c in contexts:
        block = f"[chunk_id={c['chunk_id']}]\n{c['chunk']}\n"
        if used + len(block) > available and parts:
            break
        parts.append(block)
        used += len(block)
    
    if not parts:
        # If no context fits, use at least the first chunk truncated
        if contexts:
            first_chunk = contexts[0]['chunk']
            truncated = first_chunk[:available-100] + "..."
            parts.append(f"[chunk_id={contexts[0]['chunk_id']}]\n{truncated}\n")
    
    return f"{intro}\n\nQuestion: {query}\n\nContext:\n" + "\n---\n".join(parts) + "\n\nAnswer:"

def _normalize_base_url(url: str) -> str:
    """
    Accepts either a base like 'http://127.0.0.1:11434' or a full endpoint.
    Returns the base 'http://host:port' with any trailing '/api/...'
    stripped.
    """
    base = url.strip().rstrip("/")
    for suffix in ("/api/chat", "/api/generate", "/api/embeddings", "/api/embed"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            base = base.rstrip("/")
    return base

def _list_ollama_models(base_url: str) -> List[Dict[str, Any]]:
    """
    Fetch available Ollama models from /api/tags.
    Returns a list of model dicts with at least 'name' and 'size' (bytes).
    """
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=30)
        r.raise_for_status()
        data = r.json() or {}
        models = data.get("models") or []
        # Normalize fields we care about
        norm = []
        for m in models:
            name = m.get("name") or m.get("model") or ""
            # Ollama docs: 'size' in bytes; sometimes 'bytes' is used
            size = m.get("size", m.get("bytes", 0))
            details = m.get("details") or {}
            families = details.get("families") or m.get("families") or []
            try:
                size_int = int(size)
            except Exception:
                size_int = 0
            norm.append({"name": name, "size": size_int, "families": families})
        return norm
    except Exception as e:
        print(f"[WARN] Unable to list Ollama models from /api/tags: {e}")
        return []

def _ensure_model_present(base_url: str, model_name: str) -> bool:
    """
    Ensure a given Ollama model is available locally.
    If missing, request a pull via /api/pull and wait (stream=False).
    Returns True if present/available, False otherwise.
    """
    try:
        models = _list_ollama_models(base_url)
        if any((m.get("name") or "").lower() == model_name.lower() for m in models):
            return True
        # Not present → pull
        print(f"[INFO] Pulling model '{model_name}' (this may take a while)...")
        r = requests.post(f"{base_url}/api/pull", json={"name": model_name, "stream": False}, timeout=600)
        # Some Ollama versions return 200 with status; others may 201; treat 2xx as ok
        if r.status_code // 100 != 2:
            print(f"[ERROR] Pull request failed for '{model_name}': {r.status_code} {r.text}")
            return False
        # Verify appears in tags after pull
        models_after = _list_ollama_models(base_url)
        ok = any((m.get("name") or "").lower() == model_name.lower() for m in models_after)
        if not ok:
            print(f"[WARN] Model '{model_name}' not visible after pull; Ollama may still be finalizing.")
        return ok
    except Exception as e:
        print(f"[ERROR] Failed ensuring model '{model_name}': {e}")
        return False

def _is_generation_model(meta: Dict[str, Any]) -> bool:
    """
    Best-effort filter to identify usable text-generation models (not embeddings).
    """
    name = (meta.get("name") or "").lower()
    families = [str(f).lower() for f in (meta.get("families") or [])]
    # Exclude well-known embedding names
    bad_name_parts = [
        "embed", "embedding", "all-minilm", "minilm", "nomic", "e5", "bge", "gte",
        "mxbai", "sfr", "specter", "text-embedding", "gte-small", "gte-base",
    ]
    if any(p in name for p in bad_name_parts):
        return False
    # If families indicate embedding/encoder-only, skip
    if any(f in ("embedding", "encoder", "bert") for f in families):
        return False
    # Otherwise assume it can generate
    return True

def _pick_chat_candidates(models: List[Dict[str, Any]], exclude: str) -> List[str]:
    candidates = []
    for m in models:
        n = m.get("name")
        if not n or n == exclude:
            continue
        if not _is_generation_model(m):
            continue
        candidates.append(m)
    # Prefer those with known size; smallest first; unknown size last
    candidates.sort(key=lambda m: (0 if (m.get("size") or 0) > 0 else 1, m.get("size") or 0))
    return [m["name"] for m in candidates]

def answer_via_ollama(prompt: str, url: str = DEFAULT_OLLAMA_URL, model: str = DEFAULT_GEN_MODEL):
    """
    Try /api/chat first; on 500, fallback to /api/generate.
    Adds useful debug on non-200s and prevents double '/api/chat/api/chat'.
    Also allows forcing CPU or limiting GPU layers through GEN_GPU_LAYERS.
    """
    base = _normalize_base_url(url)
    chat_url = f"{base}/api/chat"
    gen_url = f"{base}/api/generate"

    options = {
        "num_ctx": GEN_NUM_CTX,
        "num_predict": GEN_NUM_PREDICT,
    }
    if GEN_GPU_LAYERS is not None:
        # Set to "0" to force CPU if VRAM is low.
        try:
            options["gpu_layers"] = int(GEN_GPU_LAYERS)
        except ValueError:
            pass

    chat_payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": options,
    }

    try:
        r = requests.post(chat_url, json=chat_payload, timeout=180)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            if "message" in data and isinstance(data["message"], dict):
                return (data["message"].get("content") or "").strip()
            # Some Ollama builds may use "content"
            if "content" in data:
                return (data.get("content") or "").strip()
        return str(data)

    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", None)
        body = e.response.text if getattr(e, "response", None) is not None else ""
        error_msg = f"HTTP {status} error from /api/chat: {body[:500]}"
        print(f"[INFO] /api/chat failed with status {status}, falling back to /api/generate")
        print(f"[DEBUG] Chat error response:\n {body}\n")

        if status == 500:
            gen_payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": options,
            }
            try:
                # Try with the model, but if prompt is too long, truncate it
                prompt_to_send = prompt
                max_prompt_chars = GEN_NUM_CTX * 3  # Rough estimate: 3 chars per token
                if len(prompt_to_send) > max_prompt_chars:
                    print(f"[WARN] Prompt too long ({len(prompt_to_send)} chars), truncating to {max_prompt_chars} chars")
                    prompt_to_send = prompt_to_send[:max_prompt_chars] + "\n\n[Prompt truncated due to length]"
                    gen_payload["prompt"] = prompt_to_send
                
                # Use longer timeout for first request (model loading)
                r2 = requests.post(gen_url, json=gen_payload, timeout=180)
                print(f"[DEBUG] /api/generate status: {r2.status_code}")
                
                # Check status before raising
                if r2.status_code != 200:
                    error_body = r2.text[:1000] if r2.text else "No error body"
                    print(f"[DEBUG] /api/generate error response: {error_body}")
                    
                    # Try to parse error for more details
                    try:
                        error_json = r2.json()
                        if "error" in error_json:
                            error_body = error_json["error"]
                    except:
                        pass
                    
                    # Raise with detailed error
                    raise requests.exceptions.HTTPError(
                        f"HTTP {r2.status_code}: {error_body}",
                        response=r2
                    )
                
                print(f"[DEBUG] /api/generate raw response length: {len(r2.text)} chars")
                data2 = r2.json()
                response_text = data2.get("response") or ""
                if not response_text and "error" in data2:
                    raise RuntimeError(f"Ollama returned error: {data2['error']}")
                return response_text.strip()
            except requests.exceptions.HTTPError as e2:
                # Get detailed error information
                status2 = getattr(e2.response, "status_code", None)
                body2 = e2.response.text if getattr(e2, "response", None) is not None else ""
                error_msg2 = f"HTTP {status2} error from /api/generate: {body2[:500]}"
                print(f"[ERROR] {error_msg2}")
                
                # For 500 errors, try CPU mode first (often fixes memory/VRAM issues)
                if status2 == 500:
                    print("[INFO] Attempting CPU fallback (gpu_layers=0)...")
                    try:
                        # Ensure options dict exists and set gpu_layers=0
                        if "options" not in gen_payload:
                            gen_payload["options"] = {}
                        gen_payload["options"]["gpu_layers"] = 0
                        # Also reduce context if it's very large
                        if gen_payload["options"].get("num_ctx", GEN_NUM_CTX) > 1024:
                            gen_payload["options"]["num_ctx"] = 1024
                            print("[INFO] Reduced context window to 1024 for CPU mode")
                        
                        r2b = requests.post(gen_url, json=gen_payload, timeout=180)
                        print(f"[DEBUG] /api/generate (cpu retry) status: {r2b.status_code}")
                        if r2b.status_code == 200:
                            data2b = r2b.json()
                            response_text = data2b.get("response") or ""
                            if response_text:
                                print("[SUCCESS] CPU fallback succeeded")
                                return response_text.strip()
                        else:
                            print(f"[DEBUG] /api/generate (cpu retry) error: {r2b.text[:500]}")
                    except requests.exceptions.Timeout as timeout_error:
                        print(f"[WARN] CPU fallback timed out: {timeout_error}")
                    except Exception as cpu_error:
                        print(f"[WARN] CPU fallback also failed: {cpu_error}")
                
                # If the backend reports OOM/VRAM errors, try CPU retry then auto-fallback to smaller chat models.
                all_body = (body or "") + (body2 or "")
                oom_hint = "requires more system memory" in all_body.lower() or "not enough memory" in all_body.lower() or status2 == 500
                if oom_hint and status2 != 500:  # Skip if we already tried CPU above
                    print("[WARN] Model appears too large for available memory/VRAM.")
                    # First attempt: force CPU by setting gpu_layers=0, retry same model
                    try:
                        if "options" not in gen_payload:
                            gen_payload["options"] = {}
                        gen_payload["options"]["gpu_layers"] = 0
                        print("[INFO] Retrying with same model on CPU (gpu_layers=0)...")
                        r2b = requests.post(gen_url, json=gen_payload, timeout=180)
                        print(f"[DEBUG] /api/generate (cpu retry) status: {r2b.status_code}")
                        if r2b.status_code == 200:
                            data2b = r2b.json()
                            return (data2b.get("response") or "").strip()
                    except (requests.exceptions.HTTPError, requests.exceptions.Timeout) as retry_error:
                        print(f"[WARN] CPU retry failed: {retry_error}")
                        pass

                    # Second attempt: iterate through smallest chat-capable models
                    models = _list_ollama_models(base)
                    candidates = _pick_chat_candidates(models, exclude=model)

                    # If none available locally, try to pull recommended small chat models
                    if not candidates:
                        for rec in ("llama3.2:1b", "qwen2.5:1.5b"):
                            if _ensure_model_present(base, rec):
                                candidates.append(rec)

                    if candidates:
                        for fallback in candidates[:5]:
                            try:
                                print(f"[INFO] Retrying with smaller model: '{fallback}'")
                                gen_payload["model"] = fallback
                                r3 = requests.post(gen_url, json=gen_payload, timeout=180)
                                print(f"[DEBUG] /api/generate (fallback) status: {r3.status_code}")
                                print(f"[DEBUG] /api/generate (fallback) raw response:\n {r3.text}\n")
                                r3.raise_for_status()
                                data3 = r3.json()
                                return (data3.get("response") or "").strip()
                            except requests.exceptions.HTTPError as e3:
                                txt = e3.response.text if getattr(e3, "response", None) is not None else ""
                                if "does not support generate" in (txt.lower() if txt else ""):
                                    # Skip embedding-only models that slipped through
                                    continue
                                # For other HTTP errors, keep trying next candidate
                                continue
                    print("[ERROR] No usable smaller chat models succeeded.")
                    print("Tips:")
                    print(" - Pull a smaller chat model, e.g.:  ollama pull llama3.2:1b  (or qwen2.5:1.5b)")
                    print(" - Or force CPU by setting environment variable GEN_GPU_LAYERS=0")
                # If not OOM-related or all fallbacks failed, raise with detailed error
                raise RuntimeError(f"Failed to generate answer. {error_msg2}") from e2

        # Non-500 errors → re-raise for visibility with better error message
        raise RuntimeError(f"Failed to generate answer. {error_msg}") from e

    except requests.exceptions.Timeout as e:
        raise RuntimeError(f"Request to Ollama timed out. The model may be taking too long to respond. Try using a smaller model or reducing the prompt length. Details: {str(e)}") from e
    except requests.exceptions.RequestException as e:
        error_detail = str(e)
        if "Connection" in error_detail:
            raise RuntimeError(f"Failed to connect to Ollama at {base}. Is Ollama running? Please start Ollama and try again. Details: {error_detail}") from e
        else:
            raise RuntimeError(f"Request to Ollama failed: {error_detail}") from e

def clean_answer(answer: str) -> str:
    """
    Clean the answer by removing unwanted prefixes and chunk ID references.
    """
    if not answer:
        return answer
    
    # Remove leading/trailing whitespace
    answer = answer.strip()
    
    # Remove common unwanted prefixes (case-insensitive)
    unwanted_prefixes = [
        r"\[chunk_id=\d+\]\s*",  # [chunk_id=1] at start
        r"i would suggest the following answer:\s*",
        r"i would suggest:\s*",
        r"the following answer:\s*",
        r"here is the answer:\s*",
        r"answer:\s*",
        r"based on the context[,\s]*",
        r"according to the context[,\s]*",
    ]
    
    for pattern in unwanted_prefixes:
        answer = re.sub(pattern, "", answer, flags=re.IGNORECASE)
    
    # Remove any remaining [chunk_id=X] references anywhere in the text
    answer = re.sub(r"\[chunk_id=\d+\]\s*", "", answer, flags=re.IGNORECASE)
    
    # Clean up extra whitespace and newlines
    answer = re.sub(r"\s+", " ", answer)
    answer = re.sub(r"\n\s*\n", "\n", answer)  # Remove multiple newlines
    answer = answer.strip()
    
    return answer

def generate_answer(query: str, df: pd.DataFrame, hits: List[int], max_ctx: int = 4000,
                    gen_model: str = DEFAULT_GEN_MODEL, ollama_url: str = DEFAULT_OLLAMA_URL):
    # Build the context rows *as dicts*; this fixes the 'string indices' TypeError
    ctx = [{"chunk_id": int(df.iloc[i]["chunk_id"]), "chunk": df.iloc[i]["chunk"]} for i in hits]
    prompt = build_prompt(query, ctx, max_ctx)
    
    # Check prompt length and warn if too long
    if len(prompt) > max_ctx * 4:  # Rough estimate: 4 chars per token
        print(f"[WARN] Prompt is very long ({len(prompt)} chars), may cause issues")
    
    try:
        answer = answer_via_ollama(prompt, ollama_url, gen_model)
        # Clean the answer to remove unwanted prefixes and chunk IDs
        return clean_answer(answer)
    except Exception as e:
        # Re-raise with more context
        error_msg = str(e)
        if "Failed to connect" in error_msg or "Is Ollama running" in error_msg:
            raise RuntimeError(f"Ollama connection error: {error_msg}. Please ensure Ollama is running at {ollama_url}") from e
        elif "HTTP 500" in error_msg or "Internal Server Error" in error_msg:
            raise RuntimeError(f"Ollama server error: {error_msg}. The model '{gen_model}' may be having issues. Try a different model or check Ollama logs.") from e
        else:
            raise RuntimeError(f"Answer generation failed: {error_msg}") from e
