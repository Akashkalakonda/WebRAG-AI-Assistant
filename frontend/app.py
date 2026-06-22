import streamlit as st
import requests
import json
from datetime import datetime
from urllib.parse import urlparse

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="WebRAG — Web-grounded AI",
    page_icon="🪐",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "WebRAG — Real-time answers grounded in the web."},
)

BACKEND_URL = "http://localhost:5001"

SUGGESTIONS = [
    "What is retrieval-augmented generation?",
    "Latest breakthroughs in AI research",
    "Explain transformer architecture",
    "How do large language models reason?",
]

TECH_STACK = [
    "Flask", "SerpAPI", "BeautifulSoup",
    "ChromaDB", "sentence-transformers",
    "Groq LLaMA 3.3 70B", "LangChain",
]

STAGE_LABELS = {
    "searching":  "🔍  Searching the web…",
    "processing": "🌐  Processing source pages…",
    "embedding":  "🧠  Chunking and embedding content…",
    "retrieving": "📚  Retrieving relevant context…",
    "generating": "🤖  Generating answer…",
}

# ── CSS + Animations ──────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Base ── */
html, body, [data-testid="stApp"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    background-color: #0B1020 !important;
    color: #F8FAFC !important;
}

/* Radial glow + grid */
.stApp {
    background-color: #0B1020 !important;
    background-image:
        radial-gradient(ellipse 90% 45% at 50% -5%, rgba(124,58,237,0.18) 0%, transparent 65%),
        radial-gradient(rgba(255,255,255,0.028) 1px, transparent 1px) !important;
    background-size: 100% 100%, 54px 54px !important;
    background-attachment: fixed !important;
}

/* ── Keyframe animations ── */
@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50%       { transform: translateY(-10px); }
}
@keyframes float-sm {
    0%, 100% { transform: translateY(0px); }
    50%       { transform: translateY(-5px); }
}
@keyframes pulse-dot {
    0%, 100% { opacity: 1;   transform: scale(1);   }
    50%       { opacity: 0.3; transform: scale(0.55); }
}
@keyframes twinkle {
    0%, 100% { opacity: 0.04; }
    50%       { opacity: 0.52; }
}
@keyframes fade-in {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0);   }
}

.planet-float    { animation: float    4s ease-in-out infinite; display: inline-block; }
.planet-float-sm { animation: float-sm 5s ease-in-out infinite; display: inline-block; }
.fade-in         { animation: fade-in  0.35s ease both; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(11,15,30,0.98) !important;
    border-right: 1px solid rgba(255,255,255,0.10) !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.4rem !important;
}

/* Sidebar expand button (shown when sidebar is collapsed) */
[data-testid="stSidebarCollapsedControl"] {
    background: rgba(124,58,237,0.12) !important;
    border-right: 1px solid rgba(124,58,237,0.35) !important;
    border-bottom: 1px solid rgba(124,58,237,0.2) !important;
    border-radius: 0 10px 10px 0 !important;
    transition: background 0.18s !important;
}
[data-testid="stSidebarCollapsedControl"]:hover {
    background: rgba(124,58,237,0.26) !important;
}
[data-testid="stSidebarCollapsedControl"] svg {
    color: #A78BFA !important;
    fill: #A78BFA !important;
}

/* Sidebar collapse button (the < arrow) */
[data-testid="stSidebarCollapseButton"] button {
    color: #334155 !important;
    transition: color 0.15s !important;
}
[data-testid="stSidebarCollapseButton"] button:hover {
    color: #A78BFA !important;
}

/* ── Main content column ── */
.main .block-container {
    max-width: 800px !important;
    padding: 1.8rem 1.2rem 5rem 1.2rem !important;
    margin: 0 auto !important;
}

/* ── Hide Streamlit chrome (never hide the sidebar expand button) ── */
#MainMenu, footer { visibility: hidden !important; }
[data-testid="stToolbar"]   { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
/* Ensure sidebar collapsed control stays fully visible regardless of parent rules */
[data-testid="stSidebarCollapsedControl"] { visibility: visible !important; }

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 0.2rem 0 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: rgba(10,14,28,0.7) !important;
    border: 1px solid rgba(255,255,255,0.055) !important;
    border-radius: 10px !important;
    margin-top: 6px !important;
}
[data-testid="stExpander"] summary {
    color: #64748B !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}
[data-testid="stExpander"] summary:hover {
    color: #94A3B8 !important;
}

/* ── Buttons (New Conversation + suggestion chips) ── */
.stButton > button {
    background: rgba(124,58,237,0.11) !important;
    border: 1px solid rgba(124,58,237,0.24) !important;
    color: #C4B5FD !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 0.42rem 1rem !important;
    transition: background 0.17s ease, border-color 0.17s ease,
                color 0.17s ease, transform 0.17s ease, box-shadow 0.17s ease !important;
    width: 100% !important;
    cursor: pointer !important;
}
.stButton > button:hover {
    background: rgba(124,58,237,0.24) !important;
    border-color: rgba(124,58,237,0.52) !important;
    color: #DDD6FE !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 24px rgba(124,58,237,0.18) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
    background: rgba(124,58,237,0.36) !important;
    box-shadow: none !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] {
    border-radius: 13px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    background: rgba(13,18,35,0.9) !important;
    transition: border-color 0.18s, box-shadow 0.18s !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: rgba(124,58,237,0.42) !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.09) !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: #F8FAFC !important;
    -webkit-text-fill-color: #F8FAFC !important;
    caret-color: #A78BFA !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
}

/* ── Markdown text — force readable contrast inside chat messages ── */
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] td,
[data-testid="stMarkdownContainer"] th {
    color: #E2E8F0 !important;
}
[data-testid="stMarkdownContainer"] code {
    color: #C4B5FD !important;
    background: rgba(124,58,237,0.12) !important;
}
[data-testid="stMarkdownContainer"] a {
    color: #A78BFA !important;
}

/* ── Horizontal rule ── */
hr {
    border: none !important;
    border-top: 1px solid rgba(255,255,255,0.055) !important;
    margin: 10px 0 !important;
}
</style>

<script>
(function() {
    if (document.getElementById('wr-stars')) return;
    var layer = document.createElement('div');
    layer.id = 'wr-stars';
    layer.style.cssText = [
        'position:fixed', 'top:0', 'left:0', 'width:100%', 'height:100%',
        'pointer-events:none', 'z-index:9999', 'overflow:hidden'
    ].join(';');
    var style = document.createElement('style');
    style.textContent = '@keyframes twinkle{0%,100%{opacity:.06}50%{opacity:.55}}';
    document.head.appendChild(style);
    for (var i = 0; i < 65; i++) {
        var s = document.createElement('div');
        var big = Math.random() > 0.78;
        s.style.cssText = [
            'position:absolute',
            'width:' + (big ? '2' : '1') + 'px',
            'height:' + (big ? '2' : '1') + 'px',
            'background:white',
            'border-radius:50%',
            'left:' + (Math.random() * 100) + '%',
            'top:' + (Math.random() * 100) + '%',
            'animation:twinkle ' + (2 + Math.random() * 4) + 's ease-in-out '
                + (Math.random() * 6) + 's infinite'
        ].join(';');
        layer.appendChild(s);
    }
    document.body.appendChild(layer);
})();
</script>
"""

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return url


def now_ts() -> str:
    return datetime.now().strftime("%H:%M")


def render_sources(sources: list):
    if not sources:
        return
    label = f"Sources  ·  {len(sources)} reference{'s' if len(sources) != 1 else ''}"
    with st.expander(label, expanded=False):
        for i, src in enumerate(sources, 1):
            title  = src.get("title") or "Untitled"
            url    = src.get("url", "")
            domain = get_domain(url)
            st.markdown(
                f"""
                <div style="
                    background: rgba(124,58,237,0.06);
                    border: 1px solid rgba(124,58,237,0.14);
                    border-radius: 8px;
                    padding: 10px 14px;
                    margin: 4px 0;
                    transition: border-color 0.18s, background 0.18s;
                "
                onmouseover="this.style.borderColor='rgba(124,58,237,0.32)';this.style.background='rgba(124,58,237,0.1)'"
                onmouseout="this.style.borderColor='rgba(124,58,237,0.14)';this.style.background='rgba(124,58,237,0.06)'">
                    <div style="font-weight:600; font-size:13px; color:#E2E8F0; margin-bottom:3px;">
                        [{i}]&nbsp;&nbsp;{title}
                    </div>
                    <div style="font-size:11px; color:#475569; margin-bottom:4px;">{domain}</div>
                    <a href="{url}" target="_blank" rel="noopener" style="
                        font-size:11px; color:#7C3AED;
                        text-decoration:none; word-break:break-all;
                    " onmouseover="this.style.color='#A78BFA'"
                       onmouseout="this.style.color='#7C3AED'">
                        {url}
                    </a>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_timestamp(ts: str):
    st.markdown(
        f"<div style='font-size:10px; color:#1E293B; margin-top:3px;'>{ts}</div>",
        unsafe_allow_html=True,
    )


def render_error(kind: str):
    msgs = {
        "connection": (
            "Cannot connect to the backend.",
            "Make sure the Flask server is running:\n```\ncd backend && python app.py\n```",
        ),
        "no_results": (
            "No relevant sources found.",
            "Try rephrasing your query or using more specific terms.",
        ),
        "generation": (
            "The answer could not be generated.",
            "Please try again.",
        ),
        "server": (
            "The server returned an error.",
            "Check the backend logs for details.",
        ),
    }
    title, body = msgs.get(kind, ("An unexpected error occurred.", "Please try again."))
    st.markdown(
        f"""
        <div style="
            background: rgba(239,68,68,0.07);
            border: 1px solid rgba(239,68,68,0.2);
            border-radius: 10px;
            padding: 14px 18px;
            margin: 4px 0;
        ">
            <div style="color:#FCA5A5; font-weight:600; font-size:14px; margin-bottom:4px;">
                {title}
            </div>
            <div style="color:#94A3B8; font-size:13px; line-height:1.5;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_row(label: str, value):
    st.markdown(
        f"""
        <div style="
            display:flex; justify-content:space-between; align-items:center;
            padding:5px 0;
            border-bottom:1px solid rgba(255,255,255,0.04);
            font-size:12px;
        ">
            <span style="color:#475569;">{label}</span>
            <span style="color:#C4B5FD; font-weight:500;">{value}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(text: str):
    st.markdown(
        f"""<div style="
            font-size:10px; font-weight:600; text-transform:uppercase;
            letter-spacing:0.09em; color:#334155; margin:18px 0 8px 0;
        ">{text}</div>""",
        unsafe_allow_html=True,
    )


# ── Session state ─────────────────────────────────────────────────────────────
for key, default in {
    "messages":      [],   # {role, content, sources, ts, error_kind}
    "stats":         None, # pipeline stats dict from backend
    "pending_query": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Inject CSS + stars ────────────────────────────────────────────────────────
st.markdown(CSS, unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding:4px 0 22px 0;
                    border-bottom:1px solid rgba(255,255,255,0.055);">
            <div class="planet-float-sm" style="font-size:32px; margin-bottom:6px;">🪐</div>
            <div style="
                font-size:22px; font-weight:700; letter-spacing:-0.3px;
                background: linear-gradient(135deg, #A78BFA 0%, #7C3AED 100%);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            ">WebRAG</div>
            <div style="font-size:11px; color:#334155; margin-top:5px; line-height:1.5;">
                Web-grounded AI assistant
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    if st.button("✦  New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.stats = None
        st.session_state.pending_query = None
        st.rerun()

    section_header("Pipeline Stats")
    if st.session_state.stats:
        s = st.session_state.stats
        stat_row("Sources searched", s.get("sources_searched", "—"))
        stat_row("Pages scraped",    s.get("pages_scraped",    "—"))
        stat_row("Chunks indexed",   s.get("chunks_created",   "—"))
        stat_row("Chunks retrieved", s.get("chunks_retrieved", "—"))
        stat_row("Model", s.get("model", "—"))
    else:
        st.markdown(
            "<div style='font-size:12px; color:#1E293B; font-style:italic; padding:6px 0;'>"
            "Stats appear after your first query."
            "</div>",
            unsafe_allow_html=True,
        )

    section_header("Tech Stack")
    badges = "".join(
        f'<span style="'
        f'display:inline-block; background:rgba(255,255,255,0.05); '
        f'border:1px solid rgba(255,255,255,0.08); border-radius:5px; '
        f'padding:3px 8px; font-size:11px; color:#64748B; '
        f'margin:2px 2px;">{t}</span>'
        for t in TECH_STACK
    )
    st.markdown(
        f"<div style='display:flex; flex-wrap:wrap; gap:1px; "
        f"padding-bottom:14px; border-bottom:1px solid rgba(255,255,255,0.055);'>"
        f"{badges}</div>",
        unsafe_allow_html=True,
    )

    section_header("About")
    st.markdown(
        "<div style='font-size:12px; color:#334155; line-height:1.65;'>"
        "Phase 1 RAG implementation. Searches the web, chunks and embeds "
        "content into ChromaDB, retrieves relevant passages, and generates "
        "grounded answers with source citations."
        "</div>",
        unsafe_allow_html=True,
    )

# ── Welcome state ─────────────────────────────────────────────────────────────
pending = st.session_state.get("pending_query")
if not st.session_state.messages and not pending:
    st.markdown(
        """
        <div style="text-align:center; padding:52px 0 36px 0;" class="fade-in">
            <div class="planet-float" style="font-size:48px; margin-bottom:10px;">🪐</div>
            <div style="
                font-size:34px; font-weight:700; letter-spacing:-0.5px;
                background: linear-gradient(135deg, #A78BFA 0%, #7C3AED 100%);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                margin-bottom:10px;
            ">WebRAG</div>
            <div style="font-size:15px; color:#475569; margin-bottom:48px;">
                Real-time answers grounded in the web.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg,
                rgba(124,58,237,0.08) 0%,
                rgba(13,18,35,0.6) 100%);
            border: 1px solid rgba(124,58,237,0.14);
            border-radius: 14px;
            padding: 22px 28px;
            max-width: 560px;
            margin: 0 auto 32px auto;
        " class="fade-in">
            <div style="
                font-size:10px; font-weight:600; text-transform:uppercase;
                letter-spacing:0.09em; color:#334155; margin-bottom:16px;
            ">How it works</div>
            <div style="display:flex; flex-direction:column; gap:13px;">
                <div style="display:flex; align-items:center; gap:14px;">
                    <span style="font-size:17px; width:24px; text-align:center;">🔍</span>
                    <span style="font-size:13px; color:#64748B;">Searches the web for your query via SerpAPI</span>
                </div>
                <div style="display:flex; align-items:center; gap:14px;">
                    <span style="font-size:17px; width:24px; text-align:center;">🌐</span>
                    <span style="font-size:13px; color:#64748B;">Scrapes and reads source pages</span>
                </div>
                <div style="display:flex; align-items:center; gap:14px;">
                    <span style="font-size:17px; width:24px; text-align:center;">🧠</span>
                    <span style="font-size:13px; color:#64748B;">Chunks text and builds a semantic vector index</span>
                </div>
                <div style="display:flex; align-items:center; gap:14px;">
                    <span style="font-size:17px; width:24px; text-align:center;">📚</span>
                    <span style="font-size:13px; color:#64748B;">Retrieves the most relevant passages</span>
                </div>
                <div style="display:flex; align-items:center; gap:14px;">
                    <span style="font-size:17px; width:24px; text-align:center;">🤖</span>
                    <span style="font-size:13px; color:#64748B;">Generates a cited answer with Groq LLaMA 3.3 70B</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='text-align:center; font-size:12px; color:#334155; "
        "margin-bottom:10px;'>Try asking</div>",
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)
    for i, sug in enumerate(SUGGESTIONS):
        col = col_a if i % 2 == 0 else col_b
        with col:
            if st.button(sug, key=f"sug_{i}", use_container_width=True):
                st.session_state.pending_query = sug
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

# ── Message history ───────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("error_kind"):
            render_error(msg["error_kind"])
        else:
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                render_sources(msg.get("sources", []))
        render_timestamp(msg.get("ts", ""))

# ── Chat input ────────────────────────────────────────────────────────────────
chat_input = st.chat_input("Ask anything…")

active_query = chat_input or st.session_state.get("pending_query")
if st.session_state.get("pending_query"):
    st.session_state.pending_query = None

# ── Process query (streaming) ─────────────────────────────────────────────────
if active_query:
    ts = now_ts()

    with st.chat_message("user"):
        st.markdown(active_query)
        render_timestamp(ts)
    st.session_state.messages.append({
        "role": "user",
        "content": active_query,
        "ts": ts,
    })

    with st.chat_message("assistant"):
        answer     = ""
        sources: list = []
        error_kind = None

        status_ph = st.empty()
        token_ph  = st.empty()

        def _status_html(label: str) -> str:
            return (
                f'<div style="background:rgba(14,18,36,0.85);'
                f'border:1px solid rgba(124,58,237,0.18);border-radius:10px;'
                f'padding:10px 16px;font-size:13px;color:#94A3B8;margin-bottom:10px;">'
                f'<span style="display:inline-block;width:6px;height:6px;'
                f'background:#7C3AED;border-radius:50%;margin-right:9px;'
                f'animation:pulse-dot 1.4s ease-in-out infinite;"></span>'
                f'{label}</div>'
            )

        def _complete_html(n: int) -> str:
            plural = "s" if n != 1 else ""
            return (
                f'<div style="background:rgba(14,18,36,0.85);'
                f'border:1px solid rgba(34,197,94,0.25);border-radius:10px;'
                f'padding:10px 16px;font-size:13px;color:#86EFAC;margin-bottom:10px;">'
                f'&#10003;&nbsp;&nbsp;Complete &middot; {n} source{plural} retrieved</div>'
            )

        def _error_status_html(msg: str = "Generation failed") -> str:
            return (
                f'<div style="background:rgba(14,18,36,0.85);'
                f'border:1px solid rgba(239,68,68,0.25);border-radius:10px;'
                f'padding:10px 16px;font-size:13px;color:#FCA5A5;margin-bottom:10px;">'
                f'&#10007;&nbsp;&nbsp;{msg}</div>'
            )

        status_ph.markdown(_status_html(STAGE_LABELS["searching"]), unsafe_allow_html=True)

        try:
            with requests.post(
                f"{BACKEND_URL}/query/stream",
                json={"query": active_query},
                stream=True,
                timeout=120,
            ) as resp:
                resp.raise_for_status()

                for raw in resp.iter_lines():
                    if not raw:
                        continue
                    event = json.loads(raw)
                    etype = event.get("type")

                    if etype == "status":
                        label = STAGE_LABELS.get(event.get("stage", ""), "Processing…")
                        status_ph.markdown(_status_html(label), unsafe_allow_html=True)

                    elif etype == "meta":
                        sources = event.get("sources", [])
                        stats   = event.get("stats", {})
                        if stats:
                            st.session_state.stats = stats

                    elif etype == "token":
                        answer += event["data"]
                        token_ph.markdown(answer + " ▌")

                    elif etype == "done":
                        status_ph.markdown(_complete_html(len(sources)), unsafe_allow_html=True)
                        token_ph.markdown(answer)

                    elif etype == "error":
                        error_kind = "generation"
                        msg_text = str(event.get("message", ""))[:80]
                        status_ph.markdown(_error_status_html(msg_text or "Generation failed"), unsafe_allow_html=True)

        except requests.exceptions.ConnectionError:
            error_kind = "connection"
            status_ph.markdown(_error_status_html("Cannot connect to backend"), unsafe_allow_html=True)

        except requests.exceptions.Timeout:
            error_kind = "server"
            status_ph.markdown(_error_status_html("Request timed out"), unsafe_allow_html=True)

        except requests.exceptions.HTTPError as e:
            error_kind = "server"
            status_ph.markdown(
                _error_status_html(f"Server error ({e.response.status_code})"),
                unsafe_allow_html=True,
            )

        except Exception:
            error_kind = "generation"
            status_ph.markdown(_error_status_html(), unsafe_allow_html=True)

        resp_ts = now_ts()
        if answer:
            render_sources(sources)
        elif error_kind:
            render_error(error_kind)
        render_timestamp(resp_ts)

        st.session_state.messages.append({
            "role":       "assistant",
            "content":    answer or "",
            "sources":    sources,
            "error_kind": error_kind,
            "ts":         resp_ts,
        })
