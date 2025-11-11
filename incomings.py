# incomings.py
import os
import argparse
import numpy as np
import pandas as pd
import faiss

from read_chunks import (
    JSON_DIR, OUT_PARQUET, OUT_FAISS, OUT_NPY,
    DEFAULT_EMBED_URL, DEFAULT_EMBED_MODEL,
    DEFAULT_OLLAMA_URL, DEFAULT_GEN_MODEL,
    process_json_dir, save_artifacts,
    embed_query, build_faiss_ip_index, search_index,
    generate_answer
)

def load_or_build_embeddings(json_dir, embed_url, embed_model):
    if os.path.exists(OUT_PARQUET) and os.path.exists(OUT_NPY) and os.path.exists(OUT_FAISS):
        df = pd.read_parquet(OUT_PARQUET)
        emb = np.load(OUT_NPY)
        idx = faiss.read_index(OUT_FAISS)
        return df, emb, idx

    df = process_json_dir(json_dir, embed_url, embed_model)
    if df.empty:
        raise RuntimeError(f"No chunks produced from {json_dir}. Are your JSON files valid?")
    emb, idx = save_artifacts(df)
    return df, emb, idx

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-q", "--query", required=True, help="User query")
    ap.add_argument("--k", type=int, default=4, help="Top-k hits")
    ap.add_argument("--json_dir", default=JSON_DIR)
    ap.add_argument("--embed_url", default=DEFAULT_EMBED_URL)
    ap.add_argument("--embed_model", default=DEFAULT_EMBED_MODEL)
    ap.add_argument("--ollama_url", default=DEFAULT_OLLAMA_URL)
    ap.add_argument("--model", default=DEFAULT_GEN_MODEL)
    ap.add_argument("--max_ctx", type=int, default=4000)
    args = ap.parse_args()

    # Build or load artifacts
    df, emb, idx = load_or_build_embeddings(args.json_dir, args.embed_url, args.embed_model)

    # Embed the query and search
    q = embed_query(args.query, args.embed_url, args.embed_model)
    D, I = search_index(idx, q, args.k)

    # Convert FAISS indices to Python ints and filter -1s (just in case)
    hits = [int(i) for i in I[0] if i >= 0]

    # Generate answer
    try:
        ans = generate_answer(
            args.query, df, hits, args.max_ctx,
            gen_model=args.model, ollama_url=args.ollama_url
        )
        print("\n=== ANSWER ===\n")
        print(ans)
    except Exception as e:
        print("\n[!!!] GENERATION FAILED — SEE ABOVE ERROR MESSAGE\n")
        raise

if __name__ == "__main__":
    main()
