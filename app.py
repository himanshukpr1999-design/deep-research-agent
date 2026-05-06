"""
Web UI for the Groq Research Agent
Run with: streamlit run app.py
"""
import streamlit as st
import os
import io
from contextlib import redirect_stdout
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Deep Research Agent", page_icon="🔍", layout="wide")

st.markdown("""
<style>
.main-header {
    font-family: Georgia, serif;
    font-size: 2.5rem;
    font-weight: 400;
    color: #1a1a1a;
    margin-bottom: 0.2rem;
}
.subtitle {
    color: #666;
    font-size: 0.95rem;
    margin-bottom: 2rem;
}
.stTextInput > div > div > input {
    font-size: 1.1rem;
    padding: 0.75rem;
}
</style>
<div class="main-header">🔍 Deep Research Agent</div>
<div class="subtitle">Powered by Groq + Llama 3.3 · Multi-source research · Real citations · 100% Free</div>
""", unsafe_allow_html=True)

# API key check — try env first, then Streamlit secrets
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        os.environ["GROQ_API_KEY"] = api_key
    except Exception:
        pass

if not api_key:
    st.error("⚠️ GROQ_API_KEY not set. Add it to your environment or Streamlit secrets.")
    st.info("Get a **free** Groq API key at: https://console.groq.com/")
    st.stop()

# Lazy import after API key is set
from agent import run_research_agent, notes_storage

col1, col2 = st.columns([3, 1])
with col1:
    topic = st.text_input(
        "Research topic",
        placeholder="e.g. 'Impact of AI agents on knowledge work in 2026'",
        label_visibility="collapsed"
    )
with col2:
    research_btn = st.button("Research", type="primary", use_container_width=True)

st.caption("The agent will search the web, read 5+ sources, take structured notes, and synthesize a report. Takes ~30-90 seconds.")

if research_btn and topic:
    with st.spinner("Researching... watch the live trace below"):
        buf = io.StringIO()
        with redirect_stdout(buf):
            report = run_research_agent(topic)
        trace = buf.getvalue()

    tab1, tab2, tab3 = st.tabs(["📄 Final Report", "🧠 Agent Trace", "📚 Sources Read"])

    with tab1:
        st.markdown(report)
        st.download_button(
            "Download report (markdown)",
            report,
            file_name=f"research_{topic[:30].replace(' ', '_')}.md",
            mime="text/markdown"
        )

    with tab2:
        st.code(trace, language="text")
        st.caption("Live trace of the agent's reasoning, tool calls, and observations.")

    with tab3:
        if notes_storage:
            for i, note in enumerate(notes_storage, 1):
                with st.expander(f"Source {i}: {note['source'][:80]}"):
                    st.markdown(f"**Relevance:** {note['relevance']}")
                    st.markdown("**Key facts:**")
                    for fact in note['key_facts']:
                        st.markdown(f"- {fact}")
        else:
            st.info("No notes collected.")

with st.sidebar:
    st.markdown("### About this agent")
    st.markdown("""
A **production-grade research agent** built with:
- **Groq** for ultra-fast free inference
- **Llama 3.3 70B** as the reasoning model
- **Tool use** for web search and reading
- **ReAct loop** with reflection
- **Structured note-taking** for synthesis

**Architecture:**
1. Agent plans research strategy
2. Searches web for sources
3. Reads pages and takes notes
4. Reflects on gaps
5. Synthesizes final report
""")

    st.markdown("---")
    st.markdown("### Try these topics")
    samples = [
        "AI agent regulations 2026",
        "Best AI engineer interview prep",
        "Llama vs GPT-4 comparison",
    ]
    for s in samples:
        if st.button(s, use_container_width=True):
            st.session_state["topic"] = s
            st.rerun()
