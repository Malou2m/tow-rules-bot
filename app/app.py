"""
Streamlit chat UI for the Warhammer: The Old World rules chatbot.

Run with:
    uv run streamlit run app/app.py

Design decisions:
- st.chat_message / st.chat_input gives a native chat feel with no custom CSS.
- Chat history lives in st.session_state so the conversation persists across
  reruns but resets on page refresh (stateless server — no DB needed for MVP).
- On each user message we: embed → Pinecone query (top 8) → GPT-4o with context.
- Sources are shown in a collapsible expander so the UI stays clean.
- Army filter in the sidebar lets users narrow retrieval to a specific faction.
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
from yaml.loader import SafeLoader

load_dotenv()

AUTH_CONFIG_PATH = Path(__file__).parent.parent / "auth_config.yaml"

# ── Constants ─────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o"
TOP_K = 8
INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "tow-rules")

SYSTEM_PROMPT = """You are a rules assistant exclusively for Warhammer: The Old World (TOW), \
a tabletop wargame by Games Workshop.

SCOPE RESTRICTION: You ONLY answer questions about Warhammer: The Old World. \
If the user asks about anything unrelated — other games, general history, coding, \
personal advice, or any other topic — politely decline and remind them that you \
are a TOW rules assistant.

ANSWERING RULES:
1. Use ONLY the context passages provided below. Do not use outside knowledge.
2. Always be precise — accuracy matters for rules disputes.
3. For every factual claim you make, cite the source URL from the context passage \
it came from, formatted as a markdown link, e.g. [Combat Phase](https://tow.whfb.app/the-combat-phase). \
Place the citation inline, right after the sentence it supports.
4. If the context doesn't contain enough information to answer confidently, say so \
clearly — do not guess or invent rules.
5. If multiple context passages contradict each other, flag the discrepancy.

Context:
{context}"""

ARMIES = [
    "All armies",
    "Beastmen Brayherds", "Chaos Dwarfs", "Daemons of Chaos", "Dark Elves",
    "Dwarfen Mountain Holds", "Empire of Man", "Grand Cathay", "High Elf Realms",
    "Kingdom of Bretonnia", "Lizardmen", "Ogre Kingdoms", "Orc & Goblin Tribes",
    "Realms of Men", "Regiments of Renown", "Skaven", "Tomb Kings of Khemri",
    "Vampire Counts", "Warriors of Chaos", "Wood Elf Realms",
]


# ── Cached clients (initialised once per session) ────────────────────────────

@st.cache_resource
def get_clients():
    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(INDEX_NAME)
    return openai_client, index


# ── Core RAG functions ────────────────────────────────────────────────────────

def embed_query(client: OpenAI, text: str) -> list[float]:
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=[text])
    return resp.data[0].embedding


def retrieve(index, query_vector: list[float], army_filter: str | None, top_k: int = TOP_K):
    """Query Pinecone, optionally filtering by army name."""
    kwargs = dict(vector=query_vector, top_k=top_k, include_metadata=True)
    if army_filter:
        kwargs["filter"] = {"army": {"$eq": army_filter}}
    return index.query(**kwargs)


def build_context(matches) -> tuple[str, list[dict]]:
    """Turn Pinecone matches into a context string and a list of source dicts.

    Each passage is prefixed with its title and URL so the model can cite them
    inline in its answer without needing to guess the links.
    """
    sources = []
    parts = []
    for match in matches:
        meta = match.metadata or {}
        text = meta.get("text", "")
        if not text:
            continue

        title = meta.get("title") or meta.get("section") or "Rule"
        url = meta.get("url", "")
        army = meta.get("army", "")

        # Header line the model can read and quote from
        header_parts = [f"[{title}]({url})" if url else title]
        if army:
            header_parts.append(f"Army: {army}")
        parts.append(f"Source: {' | '.join(header_parts)}\n{text}")

        sources.append({
            "title": title,
            "section": meta.get("section", ""),
            "url": url,
            "source": meta.get("source", ""),
            "army": army,
            "score": round(match.score, 3),
        })
    return "\n\n---\n\n".join(parts), sources


def answer(client: OpenAI, question: str, context: str, history: list[dict]) -> str:
    """Call GPT-4o with the retrieved context and chat history."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(context=context)}]
    # Include last 6 turns of history for conversational follow-ups
    messages.extend(history[-12:])
    messages.append({"role": "user", "content": question})

    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.2,    # low temperature = more factual, less hallucination
        max_tokens=1024,
    )
    return resp.choices[0].message.content


# ── Streamlit UI ──────────────────────────────────────────────────────────────

def get_authenticator() -> stauth.Authenticate:
    with open(AUTH_CONFIG_PATH) as f:
        config = yaml.load(f, Loader=SafeLoader)
    authenticator = stauth.Authenticate(
        credentials=config["credentials"],
        cookie_name=config["cookie"]["name"],
        cookie_key=config["cookie"]["key"],
        cookie_expiry_days=config["cookie"]["expiry_days"],
        auto_hash=True,
    )
    # Persist auto-hashed passwords back to the config file on first run
    with open(AUTH_CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    return authenticator


def main():
    st.set_page_config(
        page_title="Warhammer: The Old World — Rules Bot",
        page_icon="⚔️",
        layout="centered",
    )

    # ── Authentication ────────────────────────────────────────────────────────
    authenticator = get_authenticator()
    authenticator.login(location="main", max_login_attempts=5)

    if st.session_state.get("authentication_status") is False:
        st.error("Incorrect username or password.")
        st.stop()
    if st.session_state.get("authentication_status") is None:
        st.stop()

    # ── Authenticated content below ───────────────────────────────────────────
    st.title("⚔️ Warhammer: The Old World — Rules Bot")
    st.caption("Ask me anything about TOW rules, army compositions, units, magic, and more.")

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        authenticator.logout(button_name="Logout", location="sidebar")
        st.header("Settings")
        army_choice = st.selectbox("Filter by army", ARMIES)
        army_filter = None if army_choice == "All armies" else army_choice

        st.divider()
        if st.button("Clear chat history"):
            st.session_state.messages = []
            st.session_state.sources_history = []
            st.rerun()

        st.divider()
        st.markdown("**Data sources**")
        st.markdown("- [TOW Rules Index](https://tow.whfb.app)")
        st.markdown("- [Old World Builder](https://old-world-builder.com)")

    # ── Session state ─────────────────────────────────────────────────────────
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "sources_history" not in st.session_state:
        st.session_state.sources_history = []

    # ── Render existing chat ──────────────────────────────────────────────────
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # Show sources beneath assistant messages
            if msg["role"] == "assistant" and i < len(st.session_state.sources_history):
                sources = st.session_state.sources_history[i // 2]
                if sources:
                    with st.expander("Sources", expanded=False):
                        for s in sources:
                            label = s["title"] or s["section"] or "Rule"
                            url = s.get("url", "")
                            army = s.get("army", "")
                            score = s.get("score", "")
                            line = f"**{label}**"
                            if army:
                                line += f" · {army}"
                            if url:
                                line += f" · [link]({url})"
                            line += f" _(similarity: {score})_"
                            st.markdown(line)

    # ── Chat input ────────────────────────────────────────────────────────────
    if prompt := st.chat_input("Ask a rules question…"):
        # Show user message immediately
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate answer
        with st.chat_message("assistant"):
            with st.spinner("Searching rules…"):
                try:
                    client, index = get_clients()
                    query_vec = embed_query(client, prompt)
                    results = retrieve(index, query_vec, army_filter)
                    context, sources = build_context(results.matches)
                    response = answer(client, prompt, context, st.session_state.messages[:-1])
                except Exception as e:
                    response = f"⚠️ Error: {e}"
                    sources = []

            st.markdown(response)

            if sources:
                with st.expander("Sources", expanded=False):
                    for s in sources:
                        label = s["title"] or s["section"] or "Rule"
                        url = s.get("url", "")
                        army = s.get("army", "")
                        score = s.get("score", "")
                        line = f"**{label}**"
                        if army:
                            line += f" · {army}"
                        if url:
                            line += f" · [link]({url})"
                        line += f" _(similarity: {score})_"
                        st.markdown(line)

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.sources_history.append(sources)


if __name__ == "__main__":
    main()
