from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from .incidents import STATE as INCIDENT_STATE
from .tracing import observe

CORPUS_PATH = Path(__file__).parent.parent / "data" / "study_corpus.json"
_corpus: list[dict] | None = None

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "algorithm": ["algorithm", "sorting", "search", "complexity", "big o", "recursion", "dynamic programming", "quicksort", "mergesort", "fibonacci", "bfs", "dfs", "traversal"],
    "data_structure": ["array", "list", "tree", "graph", "hash", "stack", "queue", "linked list", "bst", "binary search tree", "heap", "deque"],
    "os": ["process", "thread", "memory", "deadlock", "scheduling", "operating system", "semaphore", "cpu", "virtual memory", "page", "context switch"],
    "network": ["tcp", "http", "dns", "ip", "network", "protocol", "socket", "bandwidth", "udp", "rest", "api", "url"],
    "ml": ["machine learning", "neural", "model", "training", "gradient", "classification", "regression", "overfitting", "loss", "optimizer", "deep learning"],
    "database": ["sql", "database", "query", "index", "transaction", "nosql", "join", "acid", "table", "schema"],
}


class StudyState(TypedDict):
    question: str
    topic: str
    docs: list[str]
    explanation: str
    quiz: str
    tokens_in: int
    tokens_out: int


def _load_corpus() -> list[dict]:
    global _corpus
    if _corpus is None:
        with CORPUS_PATH.open(encoding="utf-8") as f:
            _corpus = json.load(f)
    return _corpus


@observe(name="classify_topic")
def classify_topic(state: StudyState) -> dict:
    question = state["question"].lower()
    topic = "general"
    for t, keywords in TOPIC_KEYWORDS.items():
        if any(kw in question for kw in keywords):
            topic = t
            break
    return {"topic": topic}


@observe(name="search_docs")
def search_docs(state: StudyState) -> dict:
    if INCIDENT_STATE["tool_fail"]:
        raise RuntimeError("Vector store timeout — tool_fail incident active")
    if INCIDENT_STATE["rag_slow"]:
        time.sleep(2.5)

    corpus = _load_corpus()
    question_words = set(state["question"].lower().split())
    topic = state["topic"]

    scored: list[tuple[int, str]] = []
    for doc in corpus:
        score = 0
        if doc.get("topic") == topic:
            score += 3
        content_words = set(doc["content"].lower().split())
        score += len(question_words & content_words)
        if score > 0:
            scored.append((score, doc["content"]))

    scored.sort(reverse=True)
    docs = [content for _, content in scored[:3]]
    return {"docs": docs}


@observe(name="explain")
def explain(state: StudyState) -> dict:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    context = "\n\n".join(state["docs"]) if state["docs"] else "No specific documents found. Answer from general knowledge."
    word_limit = "800 words" if INCIDENT_STATE["cost_spike"] else "300 words"
    messages = [
        SystemMessage(content=f"You are a helpful CS tutor for university students. Explain concepts clearly and concisely. Use examples when helpful. Keep your response under {word_limit}."),
        HumanMessage(content=f"Reference material:\n{context}\n\nStudent question: {state['question']}\n\nProvide a clear explanation."),
    ]
    response = llm.invoke(messages)
    usage = response.usage_metadata or {}
    return {
        "explanation": response.content,
        "tokens_in": state["tokens_in"] + usage.get("input_tokens", 0),
        "tokens_out": state["tokens_out"] + usage.get("output_tokens", 0),
    }


@observe(name="generate_quiz")
def generate_quiz(state: StudyState) -> dict:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)
    messages = [
        SystemMessage(content="You are a CS tutor. Create one concise multiple-choice quiz question to test understanding. Format: Question, then A/B/C/D options, then 'Answer: X'."),
        HumanMessage(content=f"Based on this explanation:\n{state['explanation'][:600]}\n\nGenerate one multiple-choice question with 4 options."),
    ]
    response = llm.invoke(messages)
    usage = response.usage_metadata or {}
    return {
        "quiz": response.content,
        "tokens_in": state["tokens_in"] + usage.get("input_tokens", 0),
        "tokens_out": state["tokens_out"] + usage.get("output_tokens", 0),
    }


@observe(name="format_response")
def format_response(state: StudyState) -> dict:
    combined = f"{state['explanation']}\n\n---\n**Practice Quiz:**\n{state['quiz']}"
    return {"explanation": combined}


def build_graph() -> object:
    graph: StateGraph = StateGraph(StudyState)

    graph.add_node("classify_topic", classify_topic)
    graph.add_node("search_docs", search_docs)
    graph.add_node("explain", explain)
    graph.add_node("generate_quiz", generate_quiz)
    graph.add_node("format_response", format_response)

    graph.set_entry_point("classify_topic")
    graph.add_edge("classify_topic", "search_docs")
    graph.add_edge("search_docs", "explain")
    graph.add_edge("explain", "generate_quiz")
    graph.add_edge("generate_quiz", "format_response")
    graph.add_edge("format_response", END)

    return graph.compile()
