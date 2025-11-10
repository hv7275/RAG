import os
import re
import json
import time
import math
import argparse
import requests
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import CrossEncoder

# Local reranker (no Ollama)
RERANKER = CrossEncoder("BAAI/bge-reranker-base")

try:
    from sklearn.metrics.pairwise import cosine_similarity as sk_cosine
    SKLEARN_AVAILABLE = True
except:
    SKLEARN_AVAILABLE = False


# ====== CONFIG ======
EMBED_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "bge-m3"
EMBED_TIMEOUT_SECS = 60
RETRY_ATTEMPTS = 4
RETRY_BACKOFF_BASE = 2.0

JSON_DIR = "json_output"
OUT_PARQUET = "embeddings.parquet"
OUT_NPY = "embeddings.npy"
OUT_FAISS = "vector_index.faiss"

CHUNK_TARGET_TOKENS = 500
CHUNK_OVERLAP_RATIO = 0.25
BATCH_SIZE = 1
# =====================


def _load_tokenizer():
    try:
        import tiktoken
        return tiktoken.get_encoding("cl100k_base")
    except:
        return None

_TOK = _load_tokenizer()

def count_tokens(text: str) -> int:
    if _TOK:
        return len(_TOK.encode(text))
    return max(1, math.ceil(len(text) / 4))


# Remove timestamps + filler words
TIMESTAMP_RE = re.compile(
    r"(\[?\(?\b(?:\d{1,2}:){1,2}\d{2}\b\)?\]?|\b\d{1,2}h\d{2}m(?:\d{2}s)?\b)",
    re.IGNORECASE
)

FILLERS = {
    "uh","um","erm","er","ah","eh","hmm",
    "you know","like","so yeah","sort of","kind of","i mean",
    "okay","ok","right","yeah","y'know"
}

def clean_text(raw: str):
    if not raw:
        return ""
    text = TIMESTAMP_RE.sub(" ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    for phrase in sorted([f for f in FILLERS if " " in f], key=len, reverse=True):
        text = re.sub(rf"(?i)\b{re.escape(phrase)}\b", "", text)
    tokens = text.split()
    tokens = [t for t in tokens if re.sub(r"[^\w']", "", t.lower()) not in FILLERS]
    return " ".join(tokens).strip()


def sec_to_hhmmss(v):
    if v is None:
        return None
    v = max(0, int(round(float(v))))
    h = v // 3600
    m = (v % 3600) // 60
    s = v % 60
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def load_sentences(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "chunks" in data:
        items = data["chunks"]
    elif "segments" in data:
        items = data["segments"]
    else:
        raise ValueError(filepath)

    out = []
    for item in items:
        text = clean_text(item.get("text",""))
        if text:
            out.append({"text": text, "start": item.get("start"), "end": item.get("end")})
    return out


def chunk_sentences(sentences):
    chunks = []
    buf_t, buf_s, buf_e = [], [], []
    buf_tok = 0

    def flush():
        if not buf_t:
            return None
        text = " ".join(buf_t).strip()
        starts = [x for x in buf_s if x is not None]
        ends = [x for x in buf_e if x is not None]
        return {
            "text": text,
            "start": min(starts) if starts else None,
            "end": max(ends) if ends else None,
            "tokens": count_tokens(text)
        }

    i = 0
    while i < len(sentences):
        s = sentences[i]
        t = s["text"]
        tok = count_tokens(t)

        if buf_tok + tok <= CHUNK_TARGET_TOKENS or not buf_t:
            buf_t.append(t); buf_s.append(s["start"]); buf_e.append(s["end"])
            buf_tok += tok; i += 1
        else:
            ch = flush()
            if ch:
                chunks.append(ch)

            keep = int(round(ch["tokens"] * CHUNK_OVERLAP_RATIO))
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
    if ch:
        chunks.append(ch)
    return chunks


def create_embeddings(text_list):
    payload = {
        "model": EMBED_MODEL,
        "input": text_list,
        "keep_alive": 0,
        "options": {"num_gpu": 0}
    }
    last = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            r = requests.post(EMBED_URL, json=payload, timeout=EMBED_TIMEOUT_SECS)
            r.raise_for_status()
            return r.json()["embeddings"]
        except Exception as e:
            last = e
            time.sleep(RETRY_BACKOFF_BASE ** attempt)
    raise RuntimeError(last)


def create_embeddings_batched(texts):
    out = []
    for i in range(0, len(texts), BATCH_SIZE):
        out.extend(create_embeddings(texts[i:i+BATCH_SIZE]))
    return out


def build_faiss(emb):
    emb = emb.astype("float32")
    faiss.normalize_L2(emb)
    idx = faiss.IndexFlatIP(emb.shape[1])
    idx.add(emb)
    return idx


def process():
    rows = []
    cid = 0
    for f in sorted(os.listdir(JSON_DIR)):
        if not f.endswith(".json"):
            continue
        sents = load_sentences(os.path.join(JSON_DIR, f))
        chunks = chunk_sentences(sents)
        texts = [c["text"] for c in chunks]
        embs = create_embeddings_batched(texts)
        title = os.path.splitext(f)[0]

        for c, e in zip(chunks, embs):
            rows.append({
                "chunk_id": cid,
                "title": title,
                "chunk": c["text"],
                "start": sec_to_hhmmss(c["start"]),
                "end": sec_to_hhmmss(c["end"]),
                "embedding": e
            })
            cid += 1

    df = pd.DataFrame(rows)
    emb = np.array(df["embedding"].tolist(), dtype=np.float32)
    np.save(OUT_NPY, emb)
    df.to_parquet(OUT_PARQUET, index=False)
    faiss.write_index(build_faiss(emb), OUT_FAISS)
    return df, emb


def rerank(query, docs):
    pairs = [(query, d) for d in docs]
    scores = RERANKER.predict(pairs)
    return scores


def search(query, df, index, final_k=5, pool_k=50):
    q = np.array(create_embeddings([query]), dtype=np.float32)
    faiss.normalize_L2(q)
    scores, idxs = index.search(q, pool_k)
    idxs = idxs.ravel()

    docs = [df.iloc[i]["chunk"] for i in idxs]
    reranked = rerank(query, docs)
    order = np.argsort(reranked)[::-1][:final_k]

    print("\n=== RESULTS ===\n")
    for rank, j in enumerate(order, 1):
        i = idxs[j]
        row = df.iloc[i]
        print(f"{rank}. score={reranked[j]:.4f} | {row['title']} | {row['start']}–{row['end']}")
        print(row["chunk"][:400], "...\n" + "-"*80)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default=None)
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()

    if args.rebuild or not os.path.exists(OUT_PARQUET):
        df, emb = process()
        index = build_faiss(emb)
    else:
        df = pd.read_parquet(OUT_PARQUET)
        emb = np.load(OUT_NPY).astype(np.float32)
        index = build_faiss(emb)

    if args.query:
        search(args.query, df, index)
    else:
        print("Ready. Use:  python read_chunks.py --query \"your question\"")


if __name__ == "__main__":
    main()
