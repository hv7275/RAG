import os
import json
import requests
import pandas as pd
import numpy as np
import faiss
from typing import List, Tuple, Dict, Any
from sklearn.metrics.pairwise import cosine_similarity as pairwise_cosine
from sklearn.feature_extraction.text import TfidfVectorizer


# -----------------------------
# Config
# -----------------------------
EMBED_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "bge-m3"
EMBED_OPTIONS = {"num_gpu": 0}   # set to {"num_gpu": 1} if you have GPU
JSON_DIR = "json_output"
PARQUET_PATH = "embeddings.parquet"
EMB_NPY_PATH = "embeddings.npy"
FAISS_PATH = "vector_index.faiss"

# Hybrid weighting: alpha * embedding_score + (1 - alpha) * lexical_score
ALPHA = 0.7


# Embedding
def create_embeddings(text_list: List[str]) -> List[List[float]]:
    """Call local embedding server and return embeddings as lists of floats."""
    payload = {
        "model": EMBED_MODEL,
        "input": text_list,
        "options": EMBED_OPTIONS
    }
    try:
        resp = requests.post(EMBED_URL, json=payload, timeout=120)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Embedding request failed: {e}\nResponse text: {getattr(e, 'response', None)}")

    data = resp.json()
    embs = data.get("embeddings")
    if not embs or not isinstance(embs, list):
        raise RuntimeError(f"Bad embedding response: {data}")
    return embs

# Data Loading
def load_chunks_from_json(json_dir: str) -> pd.DataFrame:
    """Load all chunks from JSON files into a DataFrame with metadata."""
    json_files = [f for f in os.listdir(json_dir) if f.endswith(".json")]
    if not json_files:
        raise FileNotFoundError(f"No .json files found in {json_dir}")

    all_rows = []
    chunk_id = 0

    for filename in json_files:
        filepath = os.path.join(json_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Filename without extension is used as a rough title key
        video_title = os.path.splitext(filename)[0]
        # If your filenames are like "VideoName_123", keep the left part:
        title = video_title.rsplit("_", 1)[0]

        chunks = data.get("chunks", [])
        if not chunks:
            continue

        # batch embed per file to reduce HTTP overhead
        text_list = [c.get("text", "") for c in chunks]
        embeddings = create_embeddings(text_list)

        for chunk, emb in zip(chunks, embeddings):
            all_rows.append({
                "chunk_id": chunk_id,
                "title": title,
                "chunk": chunk.get("text", ""),
                "embedding": emb
            })
            chunk_id += 1

    if not all_rows:
        raise RuntimeError("No chunks loaded/embedded.")
    df = pd.DataFrame(all_rows)
    return df

# Index Building
def build_faiss_ip_index(emb_matrix: np.ndarray) -> faiss.Index:
    """
    Build a FAISS IndexFlatIP over L2-normalized vectors.
    Cosine similarity on normalized vectors equals their inner product.
    """
    emb_matrix = emb_matrix.astype("float32", copy=False)
    faiss.normalize_L2(emb_matrix)
    d = emb_matrix.shape[1]
    index = faiss.IndexFlatIP(d)
    index.add(emb_matrix)
    return index


def build_tfidf(chunks: List[str]) -> Tuple[TfidfVectorizer, Any]:
    """
    Build a TF-IDF vectorizer and sparse matrix for lexical similarity.
    """
    vectorizer = TfidfVectorizer(
        max_features=50000,
        ngram_range=(1, 2),
        strip_accents="unicode",
        lowercase=True
    )
    tfidf_matrix = vectorizer.fit_transform(chunks)
    return vectorizer, tfidf_matrix

# Retrieval
def search_hybrid(
    query: str,
    df: pd.DataFrame,
    index: faiss.Index,
    emb_matrix_norm: np.ndarray,
    tfidf_vectorizer: TfidfVectorizer,
    tfidf_matrix,
    alpha: float = ALPHA,
    top_k: int = 5,
    doc_agg: bool = True
) -> Dict[str, Any]:
    """
    Hybrid search:
    - Embed query, L2-normalize, FAISS IP for embedding scores.
    - TF-IDF vectorize query for lexical scores.
    - Normalize both score arrays to [0,1] and blend: alpha * emb + (1-alpha) * tfidf.
    - Optionally aggregate chunk scores by 'title' to pick best document.
    """
    # 1) Embedding score (cosine via IP on normalized vectors)
    q_emb = np.array(create_embeddings([query])[0], dtype=np.float32).reshape(1, -1)
    faiss.normalize_L2(q_emb)
    # search a larger pool then cut to top_k after blending
    pool_k = max(top_k * 5, 50)
    emb_scores, emb_idxs = index.search(q_emb, pool_k)
    emb_scores = emb_scores.ravel()
    emb_idxs = emb_idxs.ravel()

    # 2) Lexical score (cosine on TF-IDF)
    q_tfidf = tfidf_vectorizer.transform([query])
    # pairwise cosine returns dense ndarray
    tfidf_scores_full = (q_tfidf @ tfidf_matrix.T).toarray().ravel()

    # Align lexical scores to the same candidate pool (emb_idxs)
    tfidf_scores = tfidf_scores_full[emb_idxs]

    # 3) Normalize and blend
    def minmax(x: np.ndarray) -> np.ndarray:
        if x.size == 0:
            return x
        xmin, xmax = float(np.min(x)), float(np.max(x))
        if xmax <= xmin:
            return np.zeros_like(x)
        return (x - xmin) / (xmax - xmin)

    emb_norm = minmax(emb_scores)
    tfidf_norm = minmax(tfidf_scores)
    blended = alpha * emb_norm + (1.0 - alpha) * tfidf_norm

    # 4) Get final top_k by blended score
    order = np.argsort(blended)[::-1]
    top_idx = emb_idxs[order][:top_k]
    top_scores = blended[order][:top_k]

    top_rows = []
    for rank, (i, s) in enumerate(zip(top_idx, top_scores), start=1):
        row = df.iloc[int(i)]
        top_rows.append({
            "rank": rank,
            "chunk_id": int(row["chunk_id"]),
            "title": row["title"],
            "score": float(s),
            "chunk": row["chunk"]
        })

    # 5) Document-level aggregation to guess "main topic" (best title)
    agg = None
    best_title = None
    if doc_agg:
        # sum blended scores for all candidate pool, not just top_k
        pooled = {}
        for i, s in zip(emb_idxs, blended[order]):  # already sorted by blended descending
            r = df.iloc[int(i)]
            pooled[r["title"]] = pooled.get(r["title"], 0.0) + float(s)
        agg = sorted(pooled.items(), key=lambda x: x[1], reverse=True)
        best_title = agg[0][0] if agg else None

    return {
        "top_chunks": top_rows,
        "best_title": best_title,
        "doc_aggregation": agg
    }

# Main (build + query)
def main():
    # 1) Load + embed chunks
    print("Loading JSON chunks and creating embeddings...")
    df = load_chunks_from_json(JSON_DIR)
    print(f"Chunks processed: {df.shape}")

    # 2) Persist metadata
    df.to_parquet(PARQUET_PATH, index=False)
    print(f"Saved metadata to {PARQUET_PATH}")

    # 3) Build FAISS (cosine via IP on normalized vectors)
    emb_matrix = np.array(df["embedding"].tolist(), dtype=np.float32)
    np.save(EMB_NPY_PATH, emb_matrix)
    print(f"Saved dense embedding matrix to {EMB_NPY_PATH}")

    # Keep a normalized copy for safety/debug
    emb_matrix_norm = emb_matrix.copy()
    faiss.normalize_L2(emb_matrix_norm)

    index = build_faiss_ip_index(emb_matrix_norm.copy())
    faiss.write_index(index, FAISS_PATH)
    print(f"FAISS IP index saved to {FAISS_PATH}")

    # 4) Build TF-IDF for hybrid
    print("Building TF-IDF matrix...")
    tfidf_vectorizer, tfidf_matrix = build_tfidf(df["chunk"].tolist())
    print(f"TF-IDF matrix shape: {tfidf_matrix.shape}")

    # 5) Example query
    incoming_query = "What is the main topic of the video1"
    print("\nQuery:", incoming_query)
    results = search_hybrid(
        incoming_query,
        df=df,
        index=index,
        emb_matrix_norm=emb_matrix_norm,
        tfidf_vectorizer=tfidf_vectorizer,
        tfidf_matrix=tfidf_matrix,
        alpha=ALPHA,
        top_k=5,
        doc_agg=True
    )

    # Print results
    print("\nTop chunk matches:")
    for r in results["top_chunks"]:
        print(f"{r['rank']}. [score={r['score']:.4f}] title={r['title']}  chunk_id={r['chunk_id']}")
        preview = r['chunk'].strip().replace("\n", " ")
        if len(preview) > 220:
            preview = preview[:220] + "..."
        print(preview)
        print("-" * 80)

    if results["best_title"]:
        print(f"\nPredicted main topic (best title by aggregated score): {results['best_title']}")
    else:
        print("\nCould not determine best title — not enough signal.")


if __name__ == "__main__":
    main()
