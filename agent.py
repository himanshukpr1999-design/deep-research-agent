"""
Deep Research Agent — NVIDIA NIM Edition
-----------------------------------------
Uses NVIDIA's free hosted NIM endpoint with Llama 3.3 70B.
OpenAI-compatible API — same tool-calling structure as before.

Architecture: ReAct loop (Reason + Act) with 3 tools
  - search_web: finds relevant sources (DuckDuckGo)
  - read_page: extracts content from a URL (BeautifulSoup)
  - take_notes: structured note-taking for synthesis
"""

# Force IPv4 to avoid Windows DNS quirks
import socket
old_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET]
socket.getaddrinfo = new_getaddrinfo

import os
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup

# NVIDIA NIM — OpenAI-compatible endpoint
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL_NAME = "meta/llama-3.3-70b-instruct"


# ============================================================
# TOOLS
# ============================================================

def search_web(query: str, max_results: int = 5) -> str:
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
    notes_storage.append({
        "source": source,
        "key_facts": list(key_facts),
        "relevance": relevance,
        "timestamp": datetime.now().isoformat()
    })
    return f"Stored {len(key_facts)} facts from {source}. Total notes: {len(notes_storage)}"


# ============================================================
# TOOL DECLARATIONS — OpenAI/NVIDIA NIM schema
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


def run_research_agent(topic: str, max_iterations: int = 15, on_event=None) -> str:
    """
    Run the agent loop. Returns the final research report.

    on_event: optional callback(event_type, payload) for streaming progress.
              Event types: 'tool_call', 'tool_result', 'note', 'thought', 'final', 'error'
    """
    global notes_storage
    notes_storage = []

    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set NVIDIA_API_KEY in .env. Get a free key at https://build.nvidia.com/"
        )

    client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Research this topic deeply: {topic}"}
    ]

    print(f"\n>> Starting research on: {topic}\n" + "=" * 60)

    for iteration in range(max_iterations):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=TOOL_DECLARATIONS,
                tool_choice="auto",
                max_tokens=4096,
                temperature=0.7,
            )
        except Exception as e:
            err_str = str(e)
            print(f"\n!! API error: {err_str[:200]}")
            if on_event:
                on_event("error", {"message": err_str[:300]})

            # Recovery: if it's a tool-format error, ask the model to retry without tools
            if "tool_use_failed" in err_str or "400" in err_str or "Tool use" in err_str:
                messages.append({
                    "role": "user",
                    "content": "The last call failed. Please continue, or write the final report if you have enough notes."
                })
                try:
                    response = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=messages,
                        tools=TOOL_DECLARATIONS,
                        tool_choice="auto",
                        max_tokens=4096,
                        temperature=0.7,
                    )
                except Exception:
                    return f"Research failed: {err_str}"
            else:
                return f"Research failed: {err_str}"

        message = response.choices[0].message
        tool_calls = message.tool_calls or []

        if message.content:
            print(f"\n>> Agent: {message.content[:200]}")
            if on_event:
                on_event("thought", {"text": message.content})

        # Add assistant turn to history
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

        # No tool calls = done
        if not tool_calls:
            final_text = message.content or ""
            print(f"\n** Research complete after {iteration + 1} iterations")
            print(f"** Notes collected: {len(notes_storage)}")
            if on_event:
                on_event("final", {"text": final_text})
            return final_text

        # Execute tools
        for tc in tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                fn_args = {}

            # Cap args
            if "max_chars" in fn_args:
                fn_args["max_chars"] = min(int(fn_args.get("max_chars") or 1500), 1500)
            if "max_results" in fn_args:
                fn_args["max_results"] = min(int(fn_args.get("max_results") or 5), 5)

            print(f"\n>> Tool: {fn_name}({json.dumps({k: str(v)[:50] for k, v in fn_args.items()})})")
            if on_event:
                on_event("tool_call", {"name": fn_name, "args": fn_args})

            if fn_name in TOOL_FUNCTIONS:
                try:
                    result = TOOL_FUNCTIONS[fn_name](**fn_args)
                    result_str = str(result)[:3000]
                except Exception as e:
                    result_str = f"Tool error: {str(e)}"
            else:
                result_str = f"Unknown tool: {fn_name}"

            if fn_name == "take_notes" and on_event:
                on_event("note", {
                    "source": fn_args.get("source", ""),
                    "key_facts": fn_args.get("key_facts", []),
                    "relevance": fn_args.get("relevance", ""),
                })

            if on_event:
                on_event("tool_result", {"name": fn_name, "result": result_str[:300]})

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str
            })

    msg = f"Research incomplete - hit iteration limit. Notes collected: {len(notes_storage)}"
    if on_event:
        on_event("final", {"text": msg})
    return msg


if __name__ == "__main__":
    import sys
    if not os.getenv("NVIDIA_API_KEY"):
        print("ERROR: Set NVIDIA_API_KEY environment variable first")
        print("       Get a FREE key at: https://build.nvidia.com/")
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
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n** Saved to {filename}")
