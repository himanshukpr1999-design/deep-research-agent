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

## 🎓 Research Council — multi-agent debate mode

A council of AI professors debates any proposition — **grounded in real web evidence, with an independent fact-checker**, so the debate can't drift into hallucination.

**The council:**
| Agent | Role |
|---|---|
| 🎙️ Moderator | Frames the question, keeps rounds on track, writes the final verdict |
| 🟢 Prof. Advocate | Builds the strongest evidence-backed case in favor |
| 🔴 Prof. Skeptic | Stress-tests claims, hunts for counter-evidence |
| 🔵 Prof. Empiricist | Weighs source quality and ranks claims by evidence strength |
| 🛡️ Fact-Checker | Verifies every statement against the evidence base, flags unsupported claims publicly |

**Anti-hallucination design (3 layers):**
1. **Grounding** — before the debate, a shared evidence base is gathered from the live web; every item gets an ID like `[E3]`
2. **Mandatory citations** — professors may only assert facts that cite an evidence ID; gaps must be answered with "insufficient evidence", never filled from memory
3. **Adversarial fact-checking** — after every statement an independent checker compares each claim against the actual source text; flags are injected back into the debate so the council self-corrects, and unverified claims are excluded from the verdict

**Run it:**
```bash
# CLI
python council.py "Is nuclear power essential for decarbonization?" --rounds 2

# Web UI (live debate floor)
streamlit run council_app.py
```

The verdict separates **points of consensus** (fact-checked claims only, with citations), **open disagreements**, **claims that did not survive fact-checking**, and an overall **confidence level**.

## Setup

```bash
git clone https://github.com/yourname/research-agent
cd research-agent
pip install -r requirements.txt
```

Then create a `.env` file with ONE of these keys (both have free tiers):

```
GEMINI_API_KEY=your-key-here     # free at https://aistudio.google.com/apikey
# or
NVIDIA_API_KEY=your-key-here     # free at https://build.nvidia.com/
```

If both are set, Gemini is used. Override the model with `LLM_MODEL` (e.g. `LLM_MODEL=gemini-2.5-pro`).

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
   GEMINI_API_KEY = "your-key"
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
