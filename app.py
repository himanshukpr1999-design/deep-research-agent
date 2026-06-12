"""
Web UI for the Groq Research Agent — Search Engine Style
Run with: streamlit run app.py
"""
import streamlit as st
import os
import io
import time
from contextlib import redirect_stdout
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="DeepSearch", page_icon="🔍", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Dark layered background */
.stApp {
    background: linear-gradient(135deg, #0a0a0f 0%, #0d1117 40%, #0a0f1e 100%);
    min-height: 100vh;
}

/* Hero section */
.hero-wrap {
    text-align: center;
    padding: 3rem 0 2rem;
}
.hero-logo {
    font-size: 3rem;
    font-weight: 700;
    letter-spacing: -2px;
    background: linear-gradient(90deg, #4f8ef7, #a78bfa, #60d9fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.3rem;
}
.hero-tagline {
    color: #555;
    font-size: 0.9rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 2.5rem;
}

/* Search box — Google style */
.search-container {
    max-width: 680px;
    margin: 0 auto 1.5rem;
}
.stTextInput > div > div > input {
    background: #111827 !important;
    border: 1.5px solid #2d3748 !important;
    border-radius: 40px !important;
    color: #f0f0f0 !important;
    font-size: 1rem !important;
    padding: 0.85rem 1.5rem !important;
    box-shadow: 0 0 0 0px #4f8ef7 !important;
    transition: all 0.3s !important;
}
.stTextInput > div > div > input:focus {
    border-color: #4f8ef7 !important;
    box-shadow: 0 0 20px rgba(79,142,247,0.15) !important;
}
.stTextInput > div > div > input::placeholder { color: #4a5568 !important; }

/* Buttons */
.stButton > button {
    border-radius: 40px !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    border: 1px solid #2d3748 !important;
    transition: all 0.2s !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4f8ef7, #7c6af5) !important;
    border: none !important;
    color: white !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(79,142,247,0.4) !important;
}
.stButton > button:not([kind="primary"]) {
    background: #111827 !important;
    color: #9ca3af !important;
    font-size: 0.78rem !important;
    padding: 0.3rem 0.9rem !important;
}
.stButton > button:not([kind="primary"]):hover {
    background: #1f2937 !important;
    color: #e5e7eb !important;
    border-color: #4f8ef7 !important;
}

/* Layer cards — search result style */
.result-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 12px;
    transition: all 0.2s;
    position: relative;
    overflow: hidden;
}
.result-card::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: linear-gradient(180deg, #4f8ef7, #a78bfa);
    border-radius: 3px 0 0 3px;
}
.result-card:hover {
    background: rgba(255,255,255,0.05);
    border-color: rgba(79,142,247,0.3);
    transform: translateX(4px);
}
.result-url {
    font-size: 0.72rem;
    color: #34d399;
    margin-bottom: 0.3rem;
    font-weight: 500;
}
.result-title {
    font-size: 1rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 0.5rem;
}
.result-snippet {
    font-size: 0.82rem;
    color: #6b7280;
    line-height: 1.6;
}
.result-facts {
    margin-top: 0.75rem;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}
.fact-tag {
    background: rgba(79,142,247,0.1);
    border: 1px solid rgba(79,142,247,0.2);
    color: #93c5fd;
    font-size: 0.72rem;
    padding: 3px 10px;
    border-radius: 20px;
}

/* Live terminal */
.terminal {
    background: #050810;
    border: 1px solid #1e2a3a;
    border-radius: 14px;
    padding: 1rem 1.25rem;
    font-family: 'Courier New', monospace;
    font-size: 0.78rem;
    min-height: 140px;
    max-height: 200px;
    overflow-y: auto;
    position: relative;
}
.terminal-bar {
    display: flex;
    gap: 6px;
    margin-bottom: 0.75rem;
    align-items: center;
}
.dot { width: 10px; height: 10px; border-radius: 50%; }
.dot-r { background: #ff5f57; }
.dot-y { background: #ffbd2e; }
.dot-g { background: #28ca41; }
.terminal-title { font-size: 0.7rem; color: #3d4f63; margin-left: 8px; }
.t-search { color: #60a5fa; }
.t-read   { color: #34d399; }
.t-note   { color: #fbbf24; }
.t-think  { color: #6b7280; }
.t-done   { color: #a78bfa; }
.t-error  { color: #f87171; }

/* Progress steps */
.progress-wrap {
    display: flex;
    align-items: center;
    margin: 1rem 0 1.5rem;
    gap: 0;
}
.p-step {
    flex: 1;
    text-align: center;
    font-size: 0.72rem;
    font-weight: 500;
    padding: 0.5rem 0.25rem;
    color: #374151;
    position: relative;
}
.p-step.done  { color: #34d399; }
.p-step.active { color: #60a5fa; }
.p-line {
    flex: 0.5;
    height: 1px;
    background: #1f2937;
}
.p-line.done { background: linear-gradient(90deg, #34d399, #60a5fa); }

/* Stats */
.stat-row {
    display: flex;
    gap: 12px;
    margin: 1rem 0;
}
.stat-box {
    flex: 1;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 0.75rem;
    text-align: center;
}
.stat-num { font-size: 1.6rem; font-weight: 700; color: #e2e8f0; }
.stat-lbl { font-size: 0.7rem; color: #4b5563; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.5px; }

/* Report */
.report-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    color: #d1d5db;
    line-height: 1.9;
    font-size: 0.93rem;
}
.report-card h1 { font-size: 1.5rem; font-weight: 700; color: #f9fafb; margin-bottom: 0.5rem; }
.report-card h2 { font-size: 1.1rem; font-weight: 600; color: #e5e7eb; margin-top: 1.5rem; border-left: 3px solid #4f8ef7; padding-left: 0.75rem; }
.report-card h3 { font-size: 0.95rem; font-weight: 600; color: #d1d5db; margin-top: 1rem; }
.report-card ul { padding-left: 1.25rem; }
.report-card li { margin-bottom: 0.4rem; color: #9ca3af; }
.report-card p { color: #9ca3af; }
.report-card a { color: #60a5fa; }
.report-card strong { color: #e2e8f0; font-weight: 600; }

/* Section label */
.section-label {
    font-size: 0.7rem;
    font-weight: 600;
    color: #374151;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #1f2937;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: transparent !important; border-bottom: 1px solid #1f2937 !important; }
.stTabs [data-baseweb="tab"] { color: #4b5563 !important; font-size: 0.85rem !important; }
.stTabs [aria-selected="true"] { color: #60a5fa !important; border-bottom: 2px solid #4f8ef7 !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 1rem !important; }

/* Divider */
hr { border-color: #1f2937 !important; margin: 1.5rem 0 !important; }

/* Download btn */
.stDownloadButton > button {
    background: rgba(79,142,247,0.1) !important;
    border: 1px solid rgba(79,142,247,0.3) !important;
    color: #60a5fa !important;
    border-radius: 10px !important;
    font-size: 0.82rem !important;
}

/* Success/error */
.stSuccess, .stAlert { border-radius: 12px !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ── API key ───────────────────────────────────────────────────────────────────
for key_name in ("GEMINI_API_KEY", "NVIDIA_API_KEY"):
    if not os.getenv(key_name):
        try:
            os.environ[key_name] = st.secrets[key_name]
        except Exception:
            pass

if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("NVIDIA_API_KEY")):
    st.markdown('<div style="text-align:center;padding:3rem;color:#f87171;">⚠️ No API key set. Add GEMINI_API_KEY or NVIDIA_API_KEY to your .env file.<br><br><a href="https://aistudio.google.com/apikey" style="color:#60a5fa;">Get a free Gemini key</a> · <a href="https://build.nvidia.com/" style="color:#60a5fa;">Get a free NVIDIA key</a></div>', unsafe_allow_html=True)
    st.stop()

from agent import run_research_agent, notes_storage

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-wrap">
    <div class="hero-logo">DeepSearch</div>
    <div class="hero-tagline">AI · Web · Multi-source · Free</div>
</div>
""", unsafe_allow_html=True)

# ── Search input ──────────────────────────────────────────────────────────────
col_pad1, col_main, col_pad2 = st.columns([1, 4, 1])
with col_main:
    topic = st.text_input(
        "search",
        placeholder="Search anything deeply...",
        label_visibility="collapsed",
        key="topic_input"
    )
    c1, c2, c3 = st.columns([2, 2, 4])
    with c1:
        go = st.button("Deep Search ↗", type="primary", use_container_width=True)
    with c2:
        lucky = st.button("I'm feeling lucky", use_container_width=True)

# ── Sample chips ──────────────────────────────────────────────────────────────
_, chip_col, _ = st.columns([1, 4, 1])
with chip_col:
    samples = ["AI regulation 2026", "Future of remote work", "Quantum computing", "Llama vs GPT-4", "Data analyst career"]
    cols = st.columns(len(samples))
    for i, s in enumerate(samples):
        with cols[i]:
            if st.button(s, key=f"chip_{i}", use_container_width=True):
                st.session_state["topic_input"] = s
                st.rerun()

# handle lucky
if lucky:
    import random
    lucky_topics = ["AI agents replacing jobs", "Dark web explained", "Quantum supremacy", "Future of money", "Mars colonization"]
    st.session_state["topic_input"] = random.choice(lucky_topics)
    st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ── Research run ──────────────────────────────────────────────────────────────
if go and topic:

    _, res_col, _ = st.columns([0.2, 5, 0.2])
    with res_col:

        # Progress steps
        step_names = ["Planning", "Searching", "Reading", "Taking notes", "Reflecting", "Writing report"]
        step_ph = st.empty()

        def render_steps(active=0):
            html = '<div class="progress-wrap">'
            for i, name in enumerate(step_names):
                if i < active:
                    cls = "done"
                elif i == active:
                    cls = "active"
                else:
                    cls = ""
                html += f'<div class="p-step {cls}">'
                if i < active:
                    html += f'✓ {name}'
                elif i == active:
                    html += f'⟳ {name}'
                else:
                    html += name
                html += '</div>'
                if i < len(step_names) - 1:
                    line_cls = "done" if i < active else ""
                    html += f'<div class="p-line {line_cls}"></div>'
            html += '</div>'
            step_ph.markdown(html, unsafe_allow_html=True)

        render_steps(0)

        # Stats
        stat_ph = st.empty()
        start_time = time.time()
        search_count = [0]
        read_count = [0]

        def update_stats():
            elapsed = int(time.time() - start_time)
            stat_ph.markdown(f"""
            <div class="stat-row">
                <div class="stat-box"><div class="stat-num">{len(notes_storage)}</div><div class="stat-lbl">Sources</div></div>
                <div class="stat-box"><div class="stat-num">{search_count[0]}</div><div class="stat-lbl">Searches</div></div>
                <div class="stat-box"><div class="stat-num">{read_count[0]}</div><div class="stat-lbl">Pages read</div></div>
                <div class="stat-box"><div class="stat-num">{elapsed}s</div><div class="stat-lbl">Elapsed</div></div>
            </div>
            """, unsafe_allow_html=True)

        update_stats()

        # Terminal
        st.markdown('<div class="section-label">Live agent trace</div>', unsafe_allow_html=True)
        log_ph = st.empty()
        log_lines = [
            '<div class="terminal-bar"><div class="dot dot-r"></div><div class="dot dot-y"></div><div class="dot dot-g"></div><div class="terminal-title">agent.log</div></div>'
        ]

        def add_log(text, cls="t-think"):
            log_lines.append(f'<div class="{cls}">› {text}</div>')
            if len(log_lines) > 25:
                log_lines.pop(1)
            log_ph.markdown(f'<div class="terminal">{"".join(log_lines)}</div>', unsafe_allow_html=True)

        add_log(f'Initializing research: "{topic}"', "t-think")

        # Capture stdout and parse into live UI
        class LiveWriter(io.StringIO):
            def write(self, text):
                super().write(text)
                t = text.strip()
                if not t:
                    return
                if "Tool: search_web" in t:
                    search_count[0] += 1
                    try:
                        q = t.split('"query":')[1].split('"')[1][:50]
                    except:
                        q = t[20:60]
                    add_log(f'search_web("{q}")', "t-search")
                    render_steps(1)
                    update_stats()
                elif "Tool: read_page" in t:
                    read_count[0] += 1
                    try:
                        u = t.split('"url":')[1].split('"')[1][:55]
                    except:
                        u = t[20:60]
                    add_log(f'read_page("{u}")', "t-read")
                    render_steps(2)
                    update_stats()
                elif "Stored" in t and "facts" in t:
                    add_log(f'take_notes() → {len(notes_storage)} sources saved', "t-note")
                    render_steps(3)
                    update_stats()
                elif "Agent:" in t:
                    snippet = t.replace("💭 Agent:", "").strip()[:100]
                    add_log(f'thinking: {snippet}', "t-think")
                    render_steps(4)
                elif "Research complete" in t:
                    add_log('synthesizing final report...', "t-done")
                    render_steps(5)
                    update_stats()
                elif "error" in t.lower() or "warning" in t.lower():
                    add_log(t[:100], "t-error")

        writer = LiveWriter()
        with redirect_stdout(writer):
            report = run_research_agent(topic)

        trace = writer.getvalue()
        render_steps(6)
        add_log(f'done. {len(notes_storage)} sources · {int(time.time()-start_time)}s', "t-done")
        update_stats()

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Results ───────────────────────────────────────────────────────────
        tab1, tab2, tab3 = st.tabs([f"Report", f"Sources ({len(notes_storage)})", "Raw trace"])

        with tab1:
            st.markdown(f'<div class="report-card">{report}</div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button(
                "⬇ Download report as markdown",
                report,
                file_name=f"research_{topic[:30].replace(' ', '_')}.md",
                mime="text/markdown"
            )

        with tab2:
            if notes_storage:
                st.markdown(f'<div class="section-label">{len(notes_storage)} sources researched</div>', unsafe_allow_html=True)
                for i, note in enumerate(notes_storage):
                    facts_html = "".join([f'<span class="fact-tag">{f[:70]}</span>' for f in note["key_facts"][:5]])
                    st.markdown(f"""
                    <div class="result-card">
                        <div class="result-url">{note['source'][:80]}</div>
                        <div class="result-title">Source {i+1}</div>
                        <div class="result-snippet">{note['relevance']}</div>
                        <div class="result-facts">{facts_html}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No sources collected.")

        with tab3:
            st.code(trace, language="text")
