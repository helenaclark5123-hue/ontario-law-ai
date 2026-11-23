# The Bridge

**You deserve justice. We help you get there.**

**Try it:** https://ontario-law-ai-hairmdjbph7rmavchjbpbd.streamlit.app/

The Bridge helps everyday people in Ontario understand their rights and take
action, in plain, warm language, grounded in the real text of the law. It
answers only from the law sections it finds, cites the exact section for
every point, and points people to the right official body or free legal help.
It doesn't replace lawyers; it helps people show up ready. Built as a school
project by vibe coding with Claude Code.

**This is legal information, not legal advice.**

**Laws covered:** 27 Ontario Acts and 22 of their main regulations, grouped
into housing, work, money, family, health, benefits, rights and school,
driving and court, and everyday rules. The full list is on the app's
How it works page and in `get_laws.py`.

## How it works

1. **Get the laws** (`get_laws.py`): downloads the Acts and regulations from the
   [A2AJ Canadian Legal Data](https://huggingface.co/datasets/a2aj/canadian-laws)
   dataset (an unofficial copy of Ontario e-Laws).
2. **Chunk** (`make_chunks.py`): one chunk per section, keeping the section
   number and heading.
3. **Search by meaning** (`search.py`): embeds every chunk with the free
   `BAAI/bge-small-en-v1.5` model in a ChromaDB database (`db/`). Questions are
   also rewritten into legal terms (`answer.py`), and Claude Haiku picks the 8
   best sections from about 40 matches (`rerank.py`).
4. **Answer** (`answer.py`, `chat.py`): Claude Haiku answers only from those
   sections, cites a section for every point, and says when it can't find
   something. Warm tone, information not advice, any language.
5. **Next steps and safety** (`help.py`): verified links to official bodies
   and free legal help; a "talk to a professional" box for serious situations;
   911 first for immediate danger.
6. **Checks:** an AI-judge evaluation (`evaluate.py`), a citation checker
   (`citations.py`), a semantic entropy confidence score (`entropy.py`, also
   the app's "How sure is this?" button), and a "Flag this answer" button.
7. **Get ready for a lawyer** (`summary.py`): a one-page PDF summary of the
   conversation.
8. **Self-updating** (`update_laws.py`): re-downloads the laws, compares every
   section, and re-embeds only the ones that changed (`logs/update_log.md`).
9. **App** (`app.py`, `views/`, `ui.py`): a Streamlit website.

Test results are saved in `results/`; the full history is in `CHANGES_SUMMARY.md`.

## Run it on your computer

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=your-key-here" > .env
.venv/bin/streamlit run app.py --server.address localhost
```

## Limitations

- Only 27 Acts and some of their regulations; no city bylaws or court decisions.
  The law text is an unofficial copy, only as current as A2AJ's last update.
- Search can miss the right section when people describe problems in everyday words.
- Translations into other languages are unofficial.
- On Streamlit Community Cloud, "Check for updates" changes and flagged answers
  are lost when the app restarts.
