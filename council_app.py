"""
Web UI for the Research Council — fact-grounded multi-agent debate
Run with: streamlit run council_app.py
"""
import os
import html
import time

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Research Council", page_icon="🎓", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: linear-gradient(135deg, #0a0a0f 0%, #0d1117 40%, #0a0f1e 100%); min-height: 100vh; }

.hero-wrap { text-align: center; padding: 2.5rem 0 1.5rem; }
.hero-logo {
    font-size: 2.6rem; font-weight: 700; letter-spacing: -2px;
    background: linear-gradient(90deg, #f59e0b, #a78bfa, #4f8ef7);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.3rem;
}
.hero-tagline { color: #555; font-size: 0.85rem; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 2rem; }

.stTextInput > div > div > input {
    background: #111827 !important; border: 1.5px solid #2d3748 !important;
    border-radius: 40px !important; color: #f0f0f0 !important;
    font-size: 1rem !important; padding: 0.85rem 1.5rem !important;
}
.stTextInput > div > div > input:focus { border-color: #a78bfa !important; }
.stButton > button { border-radius: 40px !important; font-weight: 500 !important; }
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #f59e0b, #a78bfa) !important;
    border: none !important; color: white !important;
}

.bubble {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px; padding: 1.1rem 1.4rem; margin-bottom: 14px;
}
.bubble-mod      { border-left: 3px solid #a78bfa; }
.bubble-advocate { border-left: 3px solid #34d399; }
.bubble-skeptic  { border-left: 3px solid #f87171; }
.bubble-emp      { border-left: 3px solid #60a5fa; }
.speaker { font-weight: 600; color: #e2e8f0; font-size: 0.92rem; }
.speaker-title { color: #6b7280; font-size: 0.72rem; margin-left: 8px; }
.round-tag { float: right; color: #4b5563; font-size: 0.7rem; }
.statement { color: #9ca3af; font-size: 0.86rem; line-height: 1.7; margin-top: 0.5rem; white-space: pre-wrap; }

.flag-box {
    margin-top: 0.7rem; background: rgba(248,113,113,0.07);
    border: 1px solid rgba(248,113,113,0.25); border-radius: 10px;
    padding: 0.6rem 0.9rem; font-size: 0.76rem; color: #fca5a5;
}
.check-ok { color: #34d399; font-size: 0.74rem; margin-top: 0.6rem; }

.evi-card {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px; padding: 0.7rem 1rem; margin-bottom: 8px; font-size: 0.8rem;
}
.evi-id { color: #fbbf24; font-weight: 600; }
.evi-title { color: #d1d5db; }
.evi-url { color: #34d399; font-size: 0.7rem; }

.verdict-card {
    background: rgba(167,139,250,0.05); border: 1px solid rgba(167,139,250,0.3);
    border-radius: 16px; padding: 1.8rem 2.2rem; color: #d1d5db; line-height: 1.8; font-size: 0.9rem;
}
.section-label {
    font-size: 0.7rem; font-weight: 600; color: #374151; text-transform: uppercase;
    letter-spacing: 1.5px; margin: 1.2rem 0 0.75rem; padding-bottom: 0.5rem;
    border-bottom: 1px solid #1f2937;
}
.phase-banner { color: #a78bfa; font-size: 0.8rem; padding: 0.4rem 0; }
</style>
""", unsafe_allow_html=True)

if not os.getenv("NVIDIA_API_KEY"):
    try:
        os.environ["NVIDIA_API_KEY"] = st.secrets["NVIDIA_API_KEY"]
    except Exception:
        pass

if not os.getenv("NVIDIA_API_KEY"):
    st.markdown('<div style="text-align:center;padding:3rem;color:#f87171;">⚠️ NVIDIA_API_KEY not set. '
                'Add it to your .env file.<br><br>'
                '<a href="https://build.nvidia.com/" style="color:#60a5fa;">Get a free key at build.nvidia.com</a></div>',
                unsafe_allow_html=True)
    st.stop()

from council import run_council, render_markdown, summarize_flags

BUBBLE_CLASS = {
    "Moderator": "bubble-mod",
    "Prof. Advocate": "bubble-advocate",
    "Prof. Skeptic": "bubble-skeptic",
    "Prof. Empiricist": "bubble-emp",
}
AVATAR = {"Moderator": "🎙️", "Prof. Advocate": "🟢", "Prof. Skeptic": "🔴", "Prof. Empiricist": "🔵"}

st.markdown("""
<div class="hero-wrap">
    <div class="hero-logo">Research Council</div>
    <div class="hero-tagline">AI professors · Evidence-grounded debate · Fact-checked</div>
</div>
""", unsafe_allow_html=True)

_, col_main, _ = st.columns([1, 4, 1])
with col_main:
    topic = st.text_input("topic", placeholder="Give the council a proposition to debate...",
                          label_visibility="collapsed", key="topic_input")
    c1, c2, _ = st.columns([2, 2, 4])
    with c1:
        go = st.button("Convene Council ⚖", type="primary", use_container_width=True)
    with c2:
        rounds = st.selectbox("Rounds", [1, 2, 3], index=1, label_visibility="collapsed")

def render_statement(entry) -> str:
    cls = BUBBLE_CLASS.get(entry["speaker"], "bubble-mod")
    avatar = AVATAR.get(entry["speaker"], "🎓")
    flags = summarize_flags(entry["checks"])
    body = html.escape(entry["statement"])
    out = (f'<div class="bubble {cls}">'
           f'<span class="speaker">{avatar} {html.escape(entry["speaker"])}</span>'
           f'<span class="speaker-title">{html.escape(entry["title"])}</span>'
           f'<span class="round-tag">Round {entry["round"]}</span>'
           f'<div class="statement">{body}</div>')
    if flags:
        out += f'<div class="flag-box"><b>⚠ Fact-checker flags</b><br>{html.escape(flags).replace(chr(10), "<br>")}</div>'
    elif entry["checks"]:
        out += '<div class="check-ok">✓ All claims verified against evidence</div>'
    out += '</div>'
    return out

if go and topic:
    _, res_col, _ = st.columns([0.2, 5, 0.2])
    with res_col:
        phase_ph = st.empty()
        evi_label_ph = st.empty()
        evi_ph = st.empty()
        st.markdown('<div class="section-label">Debate floor</div>', unsafe_allow_html=True)
        debate_ph = st.empty()
        verdict_ph = st.empty()

        evidence_html = []
        debate_html = []
        start = time.time()

        def on_event(event, payload):
            if event == "phase":
                phase_ph.markdown(f'<div class="phase-banner">⟳ {payload["detail"]}…</div>',
                                  unsafe_allow_html=True)
            elif event == "evidence":
                evidence_html.append(
                    f'<div class="evi-card"><span class="evi-id">[{payload["id"]}]</span> '
                    f'<span class="evi-title">{html.escape(payload["title"])}</span><br>'
                    f'<span class="evi-url">{html.escape(payload["url"][:90])}</span></div>'
                )
                evi_label_ph.markdown('<div class="section-label">Shared evidence base</div>',
                                      unsafe_allow_html=True)
                evi_ph.markdown("".join(evidence_html), unsafe_allow_html=True)
            elif event == "statement":
                debate_html.append(render_statement(payload))
                debate_ph.markdown("".join(debate_html), unsafe_allow_html=True)
            elif event == "verdict":
                verdict_ph.markdown(f'<div class="verdict-card">{payload["text"]}</div>',
                                    unsafe_allow_html=True)
            elif event == "error":
                st.error(payload["message"])

        result = run_council(topic, rounds=rounds, on_event=on_event)

        phase_ph.markdown(
            f'<div class="phase-banner">✓ Council adjourned · {len(result["evidence"])} sources · '
            f'{int(time.time() - start)}s</div>', unsafe_allow_html=True)

        if result["transcript"]:
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button(
                "⬇ Download full debate as markdown",
                render_markdown(result),
                file_name=f"council_{topic[:30].replace(' ', '_')}.md",
                mime="text/markdown",
            )
