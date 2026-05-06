"""
Deep Research Agent — Groq Edition
-------------------------------------
A production-grade AI research agent powered by Groq (free tier).

Architecture: ReAct loop (Reason + Act) with 3 tools
  - search_web: finds relevant sources
  - read_page: extracts content from a URL
  - take_notes: structured note-taking for synthesis

Pattern: Plan → Act → Observe → Reflect → Repeat → Synthesize
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()  # loads GROQ_API_KEY from .env file
from groq import Groq
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup

MODEL_NAME = "llama-3.3-70b-versatile"  # Best free model on Groq


# ============================================================
# TOOLS
# ============================================================

def search_web(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        formatted = [
            {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
            for r in results
        ]
        return json.dumps(formatted, indent=2)
    except Exception as e:
        return json.dumps([{"error": f"Search failed: {str(e)}"}])


def read_page(url: str, max_chars: int = 1500) -> str:
    """Fetch and extract text content from a webpage."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchAgent/1.0)"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        clean_text = "\n".join(lines)
        return clean_text[:max_chars] + ("..." if len(clean_text) > max_chars else "")
    except Exception as e:
        return f"Failed to read page: {str(e)}"


notes_storage = []


def take_notes(source: str, key_facts: list, relevance: str) -> str:
    """Store structured notes from a source for the final report."""
    notes_storage.append({
        "source": source,
        "key_facts": list(key_facts),
        "relevance": relevance,
        "timestamp": datetime.now().isoformat()
    })
    return f"Stored {len(key_facts)} facts from {source}. Total notes: {len(notes_storage)}"


# ============================================================
# TOOL DECLARATIONS — OpenAI-compatible schema (Groq uses this)
# ============================================================

TOOL_DECLARATIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for information. Returns top results with title, URL, and snippet. Use first to find relevant sources.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query - be specific"},
                    "max_results": {"type": "integer", "description": "Number of results (default 5)"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_page",
            "description": "Read full content of a URL. Use after search_web to get details from a promising source.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to read"},
                    "max_chars": {"type": "integer", "description": "Max characters to return"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_notes",
            "description": "Store structured notes from a source you read. Use this to capture key facts before moving on.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source URL or title"},
                    "key_facts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of important facts from this source"
                    },
                    "relevance": {"type": "string", "description": "Why this source matters"}
                },
                "required": ["source", "key_facts", "relevance"]
            }
        }
    }
]

TOOL_FUNCTIONS = {
    "search_web": search_web,
    "read_page": read_page,
    "take_notes": take_notes,
}


SYSTEM_PROMPT = """You are a deep research agent. Your job: thoroughly research a topic and produce a comprehensive, accurate report.

YOUR PROCESS:
1. PLAN: Think about what aspects of the topic to investigate
2. SEARCH: Use search_web to find relevant sources
3. READ: Use read_page on the most promising URLs (aim for 4-6 sources)
4. NOTE: Use take_notes to capture key facts from each source
5. REFLECT: After 3-4 sources, ask yourself - what's missing? What angles haven't I covered?
6. SEARCH MORE: Fill gaps with additional searches
7. SYNTHESIZE: When you have 5+ sources of notes, write the final report

GUIDELINES:
- Always take notes after reading a page
- Be skeptical: if sources contradict, search more
- Prioritize recent sources for time-sensitive topics
- Mix source types: news, official sites, expert blogs

Stop researching and write the final report when you have at least 5 sources noted.

Final report format:
# [Topic] - Research Report

## Executive Summary
[2-3 sentences]

## Key Findings
- Bullet points

## Detailed Analysis
[Multi-paragraph synthesis]

## Sources
1. [Title] - URL
"""


def run_research_agent(topic: str, max_iterations: int = 15) -> str:
    """Run the agent loop. Returns the final research report."""
    global notes_storage
    notes_storage = []

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Research this topic deeply: {topic}"}
    ]

    print(f"\n🔍 Starting research on: {topic}\n" + "=" * 60)

    for iteration in range(max_iterations):
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOL_DECLARATIONS,
            tool_choice="auto",
            max_tokens=4096,
            temperature=0.7,
        )

        message = response.choices[0].message
        tool_calls = message.tool_calls or []

        if message.content:
            print(f"\n💭 Agent: {message.content[:200]}")

        # Add assistant response to history
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                }
                for tc in tool_calls
            ] if tool_calls else None
        })

        # No tool calls → agent is done
        if not tool_calls:
            final_text = message.content or ""
            print(f"\n✅ Research complete after {iteration + 1} iterations")
            print(f"📝 Notes collected: {len(notes_storage)}")
            return final_text

        # Execute tool calls
        for tc in tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments or "{}")
            # Cap max_chars to stay within Groq free tier token limits
            if "max_chars" in fn_args:
                fn_args["max_chars"] = min(fn_args["max_chars"], 1500)
            if "max_results" in fn_args:
                fn_args["max_results"] = min(fn_args["max_results"], 5)
            print(f"\n🔧 Tool: {fn_name}({json.dumps({k: str(v)[:50] for k, v in fn_args.items()})})")

            if fn_name in TOOL_FUNCTIONS:
                try:
                    result = TOOL_FUNCTIONS[fn_name](**fn_args)
                    result_str = str(result)[:3000]
                except Exception as e:
                    result_str = f"Tool error: {str(e)}"
            else:
                result_str = f"Unknown tool: {fn_name}"

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str
            })

    return f"Research incomplete - hit iteration limit. Notes collected: {len(notes_storage)}"


if __name__ == "__main__":
    import sys
    if not os.getenv("GROQ_API_KEY"):
        print("❌ Set GROQ_API_KEY environment variable first")
        print("   Get a FREE key at: https://console.groq.com/")
        sys.exit(1)

    if len(sys.argv) < 2:
        topic = input("What should I research? ")
    else:
        topic = " ".join(sys.argv[1:])

    report = run_research_agent(topic)

    print("\n" + "=" * 60)
    print("FINAL REPORT")
    print("=" * 60)
    print(report)

    filename = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, "w") as f:
        f.write(report)
    print(f"\n💾 Saved to {filename}")
