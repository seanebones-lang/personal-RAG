# Recording a demo GIF

1. Start Ollama (optional) and open a terminal in the project root.
2. Run `personalragvault ingest ~/Downloads` (or a small fixture folder).
3. Run `personalragvault query "your question"` and show Rich results.
4. Run `personalragvault ui` and show result cards + document preview.
5. Export to GIF (macOS): QuickTime screen recording → convert with `ffmpeg`:

```bash
ffmpeg -i recording.mov -vf "fps=10,scale=800:-1:flags=lanczos" -t 20 docs/assets/demo.gif
```

Keep the GIF under ~5 MB for GitHub README embedding.
