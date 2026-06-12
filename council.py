"""
Research Council — Multi-Agent Debate Grounded in Evidence
----------------------------------------------------------
A council of AI "professors" debates a topic over several rounds.
Hallucination is suppressed by three mechanisms:

  1. GROUNDING  — before the debate, a shared evidence base is gathered
                  from the live web (search + page reads). Every evidence
                  item gets an ID like [E3].
  2. CITATIONS  — professors may only assert facts that cite an evidence
                  ID. Anything without a citation must be phrased as
                  opinion/uncertainty, or the professor must say
                  "insufficient evidence".
  3. FACT-CHECK — after every statement, an independent fact-checker agent
                  compares each cited claim against the actual evidence
                  text and flags UNSUPPORTED or MISCITED claims. Flags are
                  injected back into the debate so the council self-corrects.

A moderator opens the debate, keeps rounds on track, and writes the final
verdict: points of consensus, live disagreements, and confidence levels.

Usage:
  python council.py "Is nuclear power essential for decarbonization?"
  python council.py "topic" --rounds 3
"""

import os
import re
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

# Reuse the existing research tools (search + page reader)
from agent import search_web, read_page, NVIDIA_BASE_URL, MODEL_NAME

DEBATE_TEMPERATURE = 0.4   # some rhetorical variety
CHECKER_TEMPERATURE = 0.0  # deterministic verification
MAX_EVIDENCE_ITEMS = 12
PAGE_CHARS = 1200


# ============================================================
# COUNCIL PERSONAS
# ============================================================

PROFESSORS = [
    {
        "name": "Prof. Advocate",
        "title": "Professor of Applied Sciences",
        "stance": (
            "You look for the strongest evidence-backed case IN FAVOR of the "
            "proposition or the most optimistic well-supported reading of the topic. "
            "You are rigorous, not a cheerleader: you concede points when evidence is against you."
        ),
    },
    {
        "name": "Prof. Skeptic",
        "title": "Professor of Critical Studies",
        "stance": (
            "You stress-test every claim. You look for counter-evidence, methodological "
            "weaknesses, missing context, and overgeneralization in what other panelists say. "
            "You are constructive: when evidence genuinely supports a claim, you say so."
        ),
    },
    {
        "name": "Prof. Empiricist",
        "title": "Professor of Research Methods",
        "stance": (
            "You care only about data quality. You weigh how strong each evidence item is "
            "(primary source vs. blog, recency, sample size, conflicts of interest) and "
            "rank which claims in the debate rest on solid versus shaky ground."
        ),
    },
]

PROFESSOR_RULES = """
HARD RULES (violations will be flagged publicly by the fact-checker):
1. Every factual claim MUST cite an evidence ID in square brackets, e.g. [E2] or [E1][E4].
2. You may ONLY cite evidence from the shared evidence base below. Never invent sources,
   numbers, dates, names, or quotes that are not in the evidence text.
3. If the evidence base does not cover something, say exactly: "insufficient evidence" —
   do not fill the gap from memory.
4. Clearly mark interpretation as interpretation ("In my reading...", "I would argue...").
5. Directly engage the other professors: agree, rebut, or refine their specific points by name.
6. Keep your statement under 200 words. Dense, specific, citation-heavy.
"""

MODERATOR_PROMPT = """You are the Moderator of an academic council debate.
You never assert facts yourself. You frame questions, summarize tension points,
and at the end deliver a verdict that ONLY aggregates what the professors said
and what the fact-checker verified. Claims flagged UNSUPPORTED must be excluded
from the verdict or explicitly labeled as unverified."""

CHECKER_PROMPT = """You are an adversarial fact-checker for an academic debate.
You receive (a) the shared evidence base and (b) one professor's statement.

For EACH factual claim in the statement, output a verdict:
- "supported"   : the cited evidence text actually supports the claim
- "partial"     : evidence is related but the claim overstates/distorts it
- "unsupported" : no citation, or the cited evidence does not contain this
- "opinion"     : clearly framed as interpretation, no verification needed

Judge ONLY against the evidence text provided. Do not use outside knowledge
to rescue a claim. Respond with strict JSON, no markdown fences:
{"checks": [{"claim": "<short paraphrase>", "cites": ["E1"], "verdict": "supported|partial|unsupported|opinion", "note": "<one line>"}]}
"""


# ============================================================
# LLM helper
# ============================================================

def _client() -> OpenAI:
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set NVIDIA_API_KEY in .env. Get a free key at https://build.nvidia.com/"
        )
    return OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)


def _chat(client: OpenAI, system: str, user: str, temperature: float) -> str:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=1024,
        temperature=temperature,
    )
    return (response.choices[0].message.content or "").strip()


def _parse_json(text: str) -> dict:
    """Best-effort JSON extraction from a model reply."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}


# ============================================================
# PHASE 1 — Shared evidence base
# ============================================================

def gather_evidence(client: OpenAI, topic: str, on_event=None) -> list:
    """Search the web from several angles and build a citable evidence base."""
    if on_event:
        on_event("phase", {"name": "evidence", "detail": "Gathering shared evidence base"})

    plan = _chat(
        client,
        "You generate diverse web search queries. Respond with strict JSON only.",
        f'Topic for an academic debate: "{topic}"\n'
        'Give 4 search queries covering: supporting evidence, criticism/counter-evidence, '
        'recent data/statistics, and expert analysis. '
        'JSON: {"queries": ["q1", "q2", "q3", "q4"]}',
        temperature=0.3,
    )
    queries = _parse_json(plan).get("queries") or [topic]
    queries = [q for q in queries if isinstance(q, str) and q.strip()][:4]

    evidence = []
    seen_urls = set()

    for query in queries:
        if len(evidence) >= MAX_EVIDENCE_ITEMS:
            break
        if on_event:
            on_event("search", {"query": query})
        try:
            results = json.loads(search_web(query, max_results=4))
        except (json.JSONDecodeError, TypeError):
            continue

        read_this_query = 0
        for r in results:
            url = r.get("url", "")
            if not url or url in seen_urls or "error" in r:
                continue
            if len(evidence) >= MAX_EVIDENCE_ITEMS or read_this_query >= 2:
                break
            seen_urls.add(url)
            content = read_page(url, max_chars=PAGE_CHARS)
            if content.startswith("Failed to read page"):
                continue
            read_this_query += 1
            item = {
                "id": f"E{len(evidence) + 1}",
                "title": r.get("title", "")[:120],
                "url": url,
                "query": query,
                "text": content,
            }
            evidence.append(item)
            if on_event:
                on_event("evidence", item)

    return evidence


def format_evidence(evidence: list, full_text: bool = True) -> str:
    blocks = []
    for e in evidence:
        if full_text:
            blocks.append(f"[{e['id']}] {e['title']}\nURL: {e['url']}\n{e['text']}")
        else:
            blocks.append(f"[{e['id']}] {e['title']} — {e['url']}")
    return "\n\n".join(blocks) if blocks else "(no evidence collected)"


# ============================================================
# PHASE 2 — Fact-checking
# ============================================================

def fact_check(client: OpenAI, evidence: list, speaker: str, statement: str) -> list:
    """Verify one statement against the evidence base. Returns a list of checks."""
    reply = _chat(
        client,
        CHECKER_PROMPT,
        f"EVIDENCE BASE:\n{format_evidence(evidence)}\n\n"
        f"STATEMENT BY {speaker}:\n{statement}",
        temperature=CHECKER_TEMPERATURE,
    )
    checks = _parse_json(reply).get("checks")
    if not isinstance(checks, list):
        return [{"claim": "(fact-checker output unparseable)", "cites": [],
                 "verdict": "partial", "note": "Could not verify this statement."}]
    cleaned = []
    for c in checks:
        if isinstance(c, dict) and c.get("verdict") in ("supported", "partial", "unsupported", "opinion"):
            cleaned.append({
                "claim": str(c.get("claim", ""))[:200],
                "cites": [str(x) for x in (c.get("cites") or [])],
                "verdict": c["verdict"],
                "note": str(c.get("note", ""))[:200],
            })
    return cleaned


def summarize_flags(checks: list) -> str:
    flags = [c for c in checks if c["verdict"] in ("unsupported", "partial")]
    if not flags:
        return ""
    lines = [f'- [{c["verdict"].upper()}] "{c["claim"]}" — {c["note"]}' for c in flags]
    return "\n".join(lines)


# ============================================================
# PHASE 3 — The debate
# ============================================================

def run_council(topic: str, rounds: int = 2, on_event=None) -> dict:
    """
    Run the full council debate. Returns:
    {
      "topic": str,
      "evidence": [...],
      "transcript": [{"round", "speaker", "title", "statement", "checks"}],
      "verdict": str,
    }
    """
    client = _client()

    evidence = gather_evidence(client, topic, on_event=on_event)
    if not evidence:
        msg = "Could not gather any web evidence — debate aborted to avoid an ungrounded discussion."
        if on_event:
            on_event("error", {"message": msg})
        return {"topic": topic, "evidence": [], "transcript": [], "verdict": msg}

    evidence_block = format_evidence(evidence)
    transcript = []

    def transcript_text() -> str:
        if not transcript:
            return "(debate has not started)"
        parts = []
        for t in transcript:
            parts.append(f"--- Round {t['round']} — {t['speaker']} ---\n{t['statement']}")
            flags = summarize_flags(t["checks"])
            if flags:
                parts.append(f"FACT-CHECKER FLAGS on {t['speaker']}:\n{flags}")
        return "\n\n".join(parts)

    # Moderator opens
    if on_event:
        on_event("phase", {"name": "debate", "detail": f"{rounds} round(s), {len(PROFESSORS)} professors"})
    opening = _chat(
        client,
        MODERATOR_PROMPT,
        f'Open a council debate on: "{topic}".\n'
        f"Evidence available:\n{format_evidence(evidence, full_text=False)}\n\n"
        "In under 120 words: state the question precisely and pose 2-3 sub-questions "
        "the professors should resolve.",
        temperature=0.3,
    )
    transcript.append({"round": 0, "speaker": "Moderator", "title": "Moderator",
                       "statement": opening, "checks": []})
    if on_event:
        on_event("statement", {"round": 0, "speaker": "Moderator", "title": "Moderator",
                               "statement": opening, "checks": []})

    for round_no in range(1, rounds + 1):
        for prof in PROFESSORS:
            system = (
                f"You are {prof['name']}, {prof['title']}, on an academic debate council.\n"
                f"Your role: {prof['stance']}\n{PROFESSOR_RULES}"
            )
            user = (
                f'DEBATE TOPIC: "{topic}"\n\n'
                f"SHARED EVIDENCE BASE (the ONLY permitted source of facts):\n{evidence_block}\n\n"
                f"DEBATE SO FAR:\n{transcript_text()}\n\n"
                f"It is Round {round_no}. Give your statement now."
            )
            statement = _chat(client, system, user, temperature=DEBATE_TEMPERATURE)
            checks = fact_check(client, evidence, prof["name"], statement)
            entry = {"round": round_no, "speaker": prof["name"], "title": prof["title"],
                     "statement": statement, "checks": checks}
            transcript.append(entry)
            if on_event:
                on_event("statement", entry)

    # Moderator's verdict
    if on_event:
        on_event("phase", {"name": "verdict", "detail": "Moderator synthesizing verdict"})
    verdict = _chat(
        client,
        MODERATOR_PROMPT,
        f'TOPIC: "{topic}"\n\n'
        f"EVIDENCE BASE:\n{format_evidence(evidence, full_text=False)}\n\n"
        f"FULL TRANSCRIPT WITH FACT-CHECKS:\n{transcript_text()}\n\n"
        "Write the council's final verdict in markdown:\n"
        "## Verdict\n"
        "### Points of consensus  (only fact-checked 'supported' claims, with [E#] citations)\n"
        "### Open disagreements  (where professors still differ and why)\n"
        "### Claims that did not survive fact-checking  (list flagged claims, if any)\n"
        "### Confidence  (High/Medium/Low for the overall conclusion, one-line justification)",
        temperature=0.2,
    )
    if on_event:
        on_event("verdict", {"text": verdict})

    return {"topic": topic, "evidence": evidence, "transcript": transcript, "verdict": verdict}


# ============================================================
# Report rendering + CLI
# ============================================================

def render_markdown(result: dict) -> str:
    lines = [f"# Council Debate — {result['topic']}", ""]
    lines.append(f"*{datetime.now().strftime('%Y-%m-%d %H:%M')} · "
                 f"{len(result['evidence'])} evidence sources · "
                 f"{len([t for t in result['transcript'] if t['speaker'] != 'Moderator'])} statements*")
    lines.append("\n## Transcript\n")
    for t in result["transcript"]:
        lines.append(f"### Round {t['round']} — {t['speaker']}")
        lines.append(t["statement"])
        flags = summarize_flags(t["checks"])
        if flags:
            lines.append(f"\n> **Fact-checker flags:**\n> " + flags.replace("\n", "\n> "))
        lines.append("")
    lines.append(result["verdict"])
    lines.append("\n## Evidence Base\n")
    for e in result["evidence"]:
        lines.append(f"- **[{e['id']}]** [{e['title']}]({e['url']})")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a fact-grounded AI professor council debate")
    parser.add_argument("topic", nargs="*", help="Topic or proposition to debate")
    parser.add_argument("--rounds", type=int, default=2, help="Debate rounds (default 2)")
    args = parser.parse_args()

    topic = " ".join(args.topic) if args.topic else input("What should the council debate? ")

    def printer(event, payload):
        if event == "phase":
            print(f"\n== {payload['detail']} ==")
        elif event == "search":
            print(f"  searching: {payload['query']}")
        elif event == "evidence":
            print(f"  [{payload['id']}] {payload['title'][:70]}")
        elif event == "statement":
            print(f"\n--- Round {payload['round']} — {payload['speaker']} ---")
            print(payload["statement"])
            flags = summarize_flags(payload["checks"])
            if flags:
                print(f"\n!! FACT-CHECKER FLAGS:\n{flags}")
        elif event == "verdict":
            print(f"\n{'=' * 60}\n{payload['text']}")
        elif event == "error":
            print(f"!! {payload['message']}")

    result = run_council(topic, rounds=args.rounds, on_event=printer)

    filename = f"council_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(render_markdown(result))
    print(f"\n** Saved to {filename}")
