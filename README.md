# Ontario Law Assistant

**Try it:** https://ontario-law-ai-hairmdjbph7rmavchjbpbd.streamlit.app/

A legal Q&A assistant that answers questions about Ontario law using only the
real text of the law, cites the exact section, and updates itself when the law
changes. Built as a school project by vibe coding with Claude Code.

**Laws covered:** Residential Tenancies Act, 2006 · Employment Standards Act, 2000 ·
Consumer Protection Act, 2002. Statutes only, not regulations or case law.

**This is legal information, not legal advice.**

## How it works

1. **Get the laws** (`get_laws.py`): downloads the three Acts from the
   [A2AJ Canadian Legal Data](https://huggingface.co/datasets/a2aj/canadian-laws)
   dataset (an unofficial copy of Ontario e-Laws).
2. **Chunk** (`make_chunks.py`): splits each law into one chunk per section,
   keeping the section number and heading.
3. **Search by meaning** (`search.py`): embeds every chunk with the free
   `BAAI/bge-small-en-v1.5` model and stores them in a ChromaDB database (`db/`).
4. **Answer** (`answer.py`): retrieves the 5 closest sections and asks Claude
   Haiku to answer only from them, citing a section for every claim.
5. **App** (`app.py`): a Streamlit web app.
6. **Self-updating** (`update_laws.py`): re-downloads the laws, compares every
   section, and re-embeds only the ones that changed. Changes are logged in
   `logs/update_log.md`.

## Run it on your computer

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=your-key-here" > .env
.venv/bin/streamlit run app.py --server.address localhost
```

## Limitations

- Only three statutes; the law text is an unofficial copy, only as current as A2AJ's last update.
- Search can miss the right section when people describe problems in everyday words.
- On Streamlit Community Cloud, "Check for updates" changes are lost when the app restarts.
