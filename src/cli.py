import typer
from rich import print
from pathlib import Path
import uuid

from src.ingest.ingest import discover_files, extract_text
from src.embed.embedder import embed_texts, embed_query
from src.store.vectorstore import add_documents, search

app = typer.Typer(help="PersonalRAGVault - Local personal RAG")

@app.command()
def ingest(path: Path = typer.Argument(..., help="Folder to ingest")):
    """Ingest supported files from a directory"""
    print(f"[bold green]Scanning[/bold green] {path}")
    files = discover_files(path)
    print(f"Found {len(files)} supported files")

    docs = []
    for file in files:
        text = extract_text(file)
        if not text.strip():
            continue
        docs.append({
            "id": str(uuid.uuid4()),
            "text": text[:2000],
            "metadata": {"source": str(file)}
        })

    if not docs:
        print("No usable text found.")
        return

    print(f"Embedding {len(docs)} documents...")
    texts = [d["text"] for d in docs]
    embeddings = embed_texts(texts)

    for i, doc in enumerate(docs):
        doc["embedding"] = embeddings[i]

    add_documents(docs)
    print("[bold green]Ingestion complete.[/bold green]")

@app.command()
def query(q: str, top_k: int = 5):
    """Query your personal knowledge base with RAG + Ollama"""
    print(f"[bold cyan]Query:[/bold cyan] {q}")

    # Embed the query
    query_embedding = embed_query(q)

    # Retrieve relevant chunks
    results = search(query_embedding, top_k=top_k)
    if not results:
        print("No results found in your knowledge base.")
        return

    context = "\n\n".join([r["text"] for r in results])

    print(f"[dim]Retrieved {len(results)} chunks. Generating answer...[/dim]")

    # Use Ollama for generation
    try:
        import ollama
        prompt = f"""You are a helpful assistant with access to the user's personal knowledge base.
Use the following context to answer the question. If the answer is not in the context, say so.

Context:
{context}

Question: {q}

Answer:"""

        response = ollama.chat(
            model="llama3.2",  # or any local model user has
            messages=[{"role": "user", "content": prompt}]
        )
        print("\n[bold green]Answer:[/bold green]")
        print(response["message"]["content"])
    except Exception as e:
        print(f"[yellow]Ollama error:[/yellow] {e}")
        print("\n[yellow]Raw retrieved context:[/yellow]")
        for r in results:
            print(f"- {r['text'][:300]}...")