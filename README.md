# 🔍 Deep Research Agent

An AI agent that researches any topic and produces a comprehensive, multi-source report with citations.

Built with **Groq + Llama 3.3 70B** using the ReAct pattern (Reason + Act) — tool use, structured note-taking, and reflection. **100% free to run.**

## What it does

Give it a topic. It will:
1. **Plan** the research approach
2. **Search** the web for relevant sources
3. **Read** full pages from the most promising URLs
4. **Take structured notes** from each source
5. **Reflect** on gaps and search for missing angles
6. **Synthesize** a final report with citations

## Architecture

```
┌─────────────────────────────────────────────────────┐
│         Groq — Llama 3.3 70B Versatile              │
│            ReAct Reasoning Loop                      │
└─────────────┬───────────────────────────────────────┘
              │
       ┌──────┴──────┬────────────┬──────────────┐
       ▼             ▼            ▼              ▼
   search_web    read_page   take_notes    [reflection]
   DuckDuckGo    BS4 parser  structured     internal
                              storage
```

**Why this design:**
- **Groq**: free tier, no credit card required, ultra-fast inference
- **Llama 3.3 70B**: best open-source model for tool use and reasoning
- **DuckDuckGo over Google/Bing**: free, no API key, sufficient quality
- **BeautifulSoup over headless browser**: 10x faster, works for 90% of sites
- **Structured notes over raw text**: enables better synthesis, prevents context bloat
- **Reflection step**: makes the agent recognize gaps instead of stopping early

## Setup

```bash
git clone https://github.com/yourname/research-agent
cd research-agent
pip install -r requirements.txt
export GROQ_API_KEY="your-key-here"
```

Get a **free** Groq API key at: https://console.groq.com/ (no credit card needed)

## Usage

**CLI mode:**
```bash
python agent.py "Impact of AI on radiology"
```

**Web UI:**
```bash
streamlit run app.py
```

## Deploy to Streamlit Cloud (free, 5 minutes)

1. Push this folder to a new GitHub repo
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo and pick `app.py` as the main file
4. In Settings → Secrets, add:
   ```
   GROQ_API_KEY = "your-key"
   ```
5. Deploy. You get a public URL.

## What I learned building this

- **Tool design matters more than prompts** — well-typed schemas guide the agent better than long instructions
- **Note-taking prevents context explosion** — without structured notes, sources blur together by source 4
- **Reflection beats raw iteration count** — telling the agent to ask "what's missing?" is worth more than 5 extra iterations
- **Groq is genuinely free** — fast inference with no billing required, perfect for side projects

## What's next

- [ ] Add Wikipedia API as a structured source
- [ ] PDF reading for academic papers (arXiv, Google Scholar)
- [ ] Multi-agent variant: separate "researcher" and "fact-checker" agents
- [ ] Citation verification step
- [ ] Caching for repeat queries

## Built by

[himanshu]

Part of my journey to becoming an AI Engineer.
