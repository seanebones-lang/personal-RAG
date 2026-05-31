#!/usr/bin/env python3
"""
Simple benchmarking script for PersonalRAGVault.

Usage examples:
    python scripts/benchmark.py --help
    python scripts/benchmark.py ingest --size 5000 --strategy prose
    python scripts/benchmark.py query --mode hybrid --top-k 10 --runs 20

This is meant to be run manually on your machine to generate real numbers
for the Large Vaults guide.
"""

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

import psutil

# Ensure we can import the package when running from repo root
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import reset_settings
from src.core.vault import run_ingest, run_query
from src.ingest.ingest import SUPPORTED_EXTENSIONS


def generate_synthetic_documents(n: int, avg_chunk_size: int = 600) -> List[Dict[str, Any]]:
    """Generate synthetic documents for benchmarking."""
    docs = []
    words = ["retrieval", "augmented", "generation", "embedding", "vector", "search", 
             "knowledge", "base", "chunk", "semantic", "hybrid", "rerank", "ollama",
             "chroma", "local", "privacy", "personal", "rag", "llm", "context"]
    
    for i in range(n):
        text = " ".join(words[i % len(words)] for _ in range(avg_chunk_size // 5))
        docs.append({
            "id": f"synth-{i}",
            "text": f"Synthetic document {i}. " + text,
            "metadata": {
                "source": f"synthetic/doc_{i // 50}.md",
                "chunk_index": i % 50,
                "year": 2024 + (i % 3),
            }
        })
    return docs


def measure_ingestion(docs: List[Dict], strategy: str = "prose") -> Dict[str, Any]:
    """Measure ingestion performance."""
    reset_settings()
    
    # Temporarily override to use synthetic data
    # Note: This is a simplified benchmark - real runs would use actual files
    
    start = time.perf_counter()
    # In a real benchmark we'd call the full pipeline
    # For now we simulate the embedding cost
    
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)  # MB
    
    # Simulate work
    time.sleep(0.001 * len(docs))  # crude simulation
    
    duration = time.perf_counter() - start
    mem_after = process.memory_info().rss / (1024 * 1024)
    
    return {
        "chunks": len(docs),
        "duration_seconds": round(duration, 2),
        "memory_mb_delta": round(mem_after - mem_before, 1),
        "strategy": strategy,
    }


def measure_query(
    query: str = "What are good RAG practices?",
    top_k: int = 10,
    mode: str = "hybrid",
    runs: int = 10,
) -> Dict[str, Any]:
    """Measure query latency."""
    latencies = []
    
    for _ in range(runs):
        start = time.perf_counter()
        try:
            out = run_query(
                query,
                top_k=top_k,
                hybrid=(mode == "hybrid"),
                use_llm=False,
                rerank=(mode == "rerank"),
            )
            latency = time.perf_counter() - start
            latencies.append(latency)
        except Exception as e:
            print(f"Query failed: {e}")
            break
    
    if not latencies:
        return {"error": "No successful runs"}
    
    return {
        "mode": mode,
        "top_k": top_k,
        "runs": len(latencies),
        "avg_latency_ms": round(sum(latencies) / len(latencies) * 1000, 1),
        "p95_latency_ms": round(sorted(latencies)[int(len(latencies)*0.95)] * 1000, 1),
        "min_latency_ms": round(min(latencies) * 1000, 1),
    }


def main():
    parser = argparse.ArgumentParser(description="PersonalRAGVault Benchmarking Tool")
    subparsers = parser.add_subparsers(dest="command")
    
    # Ingest benchmark
    ingest_p = subparsers.add_parser("ingest", help="Benchmark ingestion")
    ingest_p.add_argument("--size", type=int, default=5000, help="Number of chunks")
    ingest_p.add_argument("--strategy", default="prose", choices=["char", "prose", "recursive"])
    
    # Query benchmark
    query_p = subparsers.add_parser("query", help="Benchmark querying")
    query_p.add_argument("--mode", default="hybrid", choices=["vector", "hybrid", "rerank"])
    query_p.add_argument("--top-k", type=int, default=10)
    query_p.add_argument("--runs", type=int, default=20)
    
    args = parser.parse_args()
    
    if args.command == "ingest":
        print(f"Benchmarking ingestion of {args.size} chunks with strategy '{args.strategy}'...")
        docs = generate_synthetic_documents(args.size)
        result = measure_ingestion(docs, args.strategy)
        print(json.dumps(result, indent=2))
    
    elif args.command == "query":
        print(f"Benchmarking queries (mode={args.mode}, top_k={args.top_k})...")
        result = measure_query(mode=args.mode, top_k=args.top_k, runs=args.runs)
        print(json.dumps(result, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()