import streamlit as st
import pandas as pd
import json, os, re, html
from datetime import datetime, timedelta
from collections import Counter
import plotly.express as px
import random

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="💌 Our Chat Memories", page_icon="💌",
                   layout="wide", initial_sidebar_state="expanded")

# ── CONFIG ─────────────────────────────────────────────────────────────────────
CHAT_FILE = "chat.txt"
DATA_FILE = "memories_data.json"
APP_PASS  = "Guggu"

PIN_TAGS  = ["💖 Sweet", "😂 Funny", "🔥 Important", "🌟 Milestone", "😭 Emotional", "📌 General"]
REACTIONS = ["❤️", "😂", "😍", "😢", "🔥", "👏", "💯", "🥺"]

# ── CSS (unchanged, works) ────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
#MainMenu,footer{visibility:hidden;}
.app-header{
  background:linear-gradient(135deg,#667eea,#f093fb);
  padding:22px 30px;border-radius:16px;margin-bottom:20px;
  text-align:center;color:white;box-shadow:0 8px 32px rgba(102,126,234,.3);
}
.app-header h1{margin:0;font-size:2rem;font-weight:700;}
.app-header p{margin:6px 0 0;opacity:.88;font-size:.93rem;}
.chat-area{background:#e5ddd5;border-radius:16px;padding:20px;min-height:200px;}
.bubble-row{display:flex;margin:8px 0;align-items:flex-start;position:relative;}
.bubble-row.right{justify-content:flex-end;}
.bubble-row.left{justify-content:flex-start;}
.bubble{
  max-width:70%;padding:8px 12px;border-radius:16px;
  font-size:.88rem;line-height:1.5;word-wrap:break-word;
  background:#ffffff;color:#111;border:1px solid #e2e8f0;
  box-shadow:0 1px 2px rgba(0,0,0,.05);
}
.bubble.right{border-bottom-right-radius:3px;}
.bubble.left{border-bottom-left-radius:3px;}
.bubble .sender{font-weight:600;font-size:.75rem;color:#667eea;margin-bottom:4px;}
.bubble .ts{font-size:.65rem;color:#94a3b8;margin-top:4px;display:inline-block;}
.bubble.is-pin{outline:2px solid gold;}
.bubble.is-fav{outline:2px solid #ff6b9d;}
.action-menu-btn{opacity:0;transition:opacity 0.2s;margin-left:6px;cursor:pointer;background:none;border:none;font-size:1rem;color:#94a3b8;padding:0 4px;}
.bubble-row:hover .action-menu-btn{opacity:1;}
.avatar{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.85rem;font-weight:700;color:white;flex-shrink:0;}
.avatar.left{background:linear-gradient(135deg,#f093fb,#f5576c);margin-right:8px;}
.avatar.right{background:linear-gradient(135deg,#4facfe,#00f2fe);margin-left:8px;}
.date-sep{text-align:center;margin:12px 0 6px;position:relative;}
.date-sep::before{content:"";position:absolute;left:0;right:0;top:50%;height:1px;background:#cbd5e1;}
.date-sep span{background:#e5ddd5;padding:0 10px;position:relative;font-size:.72rem;color:#64748b;}
.stat-box{background:white;border-radius:14px;padding:16px;text-align:center;box-shadow:0 2px 12px rgba(0,0,0,.06);}
.stat-box .num{font-size:2rem;font-weight:700;color:#667eea;}
.stat-box .lbl{font-size:.78rem;color:#888;margin-top:2px;}
.memory-card{background:white;border-radius:12px;padding:12px 16px;margin:6px 0;box-shadow:0 2px 10px rgba(0,0,0,.06);border-left:4px solid #667eea;}
.note-box{background:#fffde7;border-radius:10px;padding:8px 12px;font-size:.82rem;color:#555;margin-top:6px;border-left:3px solid #ffd54f;}
.highlight{background:#fff176;border-radius:2px;padding:0 2px;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#1a1a2e,#16213e)!important;}
[data-testid="stSidebar"] *{color:#ddd!important;}
</style>
""", unsafe_allow_html=True)

# ── PERSISTENCE ────────────────────────────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            d = json.load(f)
    else:
        d = {}
    d.setdefault("pins", {})
    d.setdefault("favorites", [])
    d.setdefault("notes", {})
    d.setdefault("reactions", {})
    d.setdefault("anniversary", "")
    d.setdefault("names", ["", ""])
    d.setdefault("couple_note", "")
    return d

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)

# ── ROBUST WHATSAPP PARSER (fixes timestamp issue) ────────────────────────────
def parse_whatsapp_datetime(date_str, time_str):
    date_str = date_str.strip()
    time_str = time_str.strip().upper()
    time_str = re.sub(r'\.', '', time_str)
    if 'AM' not in time_str and 'PM' not in time_str:
        # assume 24h format, nothing to change
        pass
    else:
        # ensure space before AM/PM
        time_str = re.sub(r'([0-9])(AM|PM)', r'\1 \2', time_str)
    date_formats = ["%d/%m/%Y","%d/%m/%y","%m/%d/%Y","%m/%d/%y","%Y-%m-%d","%d-%m-%Y","%d-%m-%y"]
    time_formats = ["%H:%M","%H:%M:%S","%I:%M %p","%I:%M:%S %p","%I:%M%p","%I:%M:%S%p"]
    for df in date_formats:
        for tf in time_formats:
            combined = f"{date_str} {time_str}"
            try:
                return datetime.strptime(combined, f"{df} {tf}")
            except:
                continue
    return None

@st.cache_data(show_spinner="Reading your chat... 💌")
def load_chat_from_file():
    if not os.path.exists(CHAT_FILE):
        return None
    with open(CHAT_FILE, encoding="utf-8", errors="ignore") as f:
        text = f.read()
    patterns = [
        r'(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}(?::\d{2})?\s*(?:[AaPp][Mm])?)\s*[-–]\s*([^:]+):\s*(.*)',
        r'\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}(?::\d{2})?)\]\s*([^:]+):\s*(.*)',
        r'(\d{4}-\d{2}-\d{2}),\s*(\d{2}:\d{2}(?::\d{2})?)\s*[-–]\s*([^:]+):\s*(.*)',
        r'(\d{1,2}/\d{1,2}/\d{2,4})\s+(\d{1,2}:\d{2}(?::\d{2})?\s*(?:[AaPp][Mm])?)\s*[-–]\s*([^:]+):\s*(.*)',
    ]
    SKIP = {"<Media omitted>","image omitted","video omitted","audio omitted","sticker omitted","GIF omitted","document omitted","This message was deleted","You deleted this message","null",""}
    messages = []
    current = None
    lines = text.splitlines()
    for line in lines:
        matched = False
        for pat in patterns:
            m = re.match(pat, line)
            if m:
                if current:
                    messages.append(current)
                date_str, time_str = m.group(1), m.group(2)
                sender = m.group(3).strip()
                msg_text = m.group(4).strip()
                dt = parse_whatsapp_datetime(date_str, time_str)
                if dt is None:
                    dt = datetime(2000,1,1)
                current = {"id":str(len(messages)), "datetime":dt, "sender":sender, "text":msg_text}
                matched = True
                break
        if not matched and current and line.strip():
            current["text"] += "\n" + line.strip()
    if current:
        messages.append(current)
    return [m for m in messages if m["text"] not in SKIP]

# ── FIXED BUBBLE RENDERER (single-line HTML, guaranteed rendering) ───────────
def render_bubble(msg, right, app_data, search_q=""):
    mid = msg["id"]
    is_pin = mid in app_data["pins"]
    is_fav = mid in app_data["favorites"]
    side = "right" if right else "left"
    note = app_data["notes"].get(mid, "")
    reacts = app_data["reactions"].get(mid, [])
    
    # Escape and highlight
    escaped_text = html.escape(msg["text"])
    if search_q:
        escaped_q = html.escape(search_q)
        text = re.sub(f"({re.escape(escaped_q)})", r'<span class="highlight">\1</span>', escaped_text, flags=re.IGNORECASE)
    else:
        text = escaped_text
    
    badges = ('📌 ' if is_pin else '') + ('❤️' if is_fav else '')
    extra = ("is-pin " if is_pin else "") + ("is-fav" if is_fav else "")
    ts = msg["datetime"].strftime("%I:%M %p") if msg["datetime"].year != 2000 else "Unknown time"
    sender_html = f'<div class="sender">{msg["sender"]}</div>' if not right else ""
    react_html = (" " + " ".join(reacts)) if reacts else ""
    timestamp_html = f'<div class="ts">{ts}{badges}{react_html}</div>'
    note_html = f'<div class="note-box">📝 {note}</div>' if note else ""
    av_letter = msg["sender"][0].upper()
    
    # Build avatar and bubble in one single-line HTML string
    left_avatar = f'<div class="avatar left">{av_letter}</div>' if not right else ''
    right_avatar = f'<div class="avatar right">{av_letter}</div>' if right else ''
    
    bubble_html = f'''<div class="bubble-row {side}">
{left_avatar}
<div class="bubble {side} {extra}" style="white-space:pre-wrap">
{sender_html}
{text}
{timestamp_html}
{note_html}
</div>
{right_avatar}
</div>'''
    
    # Use st.markdown with unsafe_allow_html=True
    st.markdown(bubble_html, unsafe_allow_html=True)
    
    # Action menu (popover) - placed after bubble using columns
    col1, col2 = st.columns([0.9, 0.1])
    with col2:
        with st.popover("⋮", help="Message actions"):
            st.markdown(f"**{msg['sender']}** · {ts}")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("📌 Pin" if not is_pin else "📌 Unpin", key=f"pin_{mid}"):
                    if is_pin:
                        del app_data["pins"][mid]
                    else:
                        app_data["pins"][mid] = {"tag": PIN_TAGS[5]}
                    save_data(app_data)
                    st.rerun()
            with col_b:
                if st.button("❤️ Fav" if not is_fav else "💔 Unfav", key=f"fav_{mid}"):
                    if is_fav:
                        app_data["favorites"].remove(mid)
                    else:
                        app_data["favorites"].append(mid)
                    save_data(app_data)
                    st.rerun()
            with col_c:
                if st.button("📝 Note", key=f"note_btn_{mid}"):
                    st.session_state[f"edit_note_{mid}"] = not st.session_state.get(f"edit_note_{mid}", False)
            if st.session_state.get(f"edit_note_{mid}", False):
                new_note = st.text_area("Your note:", value=note, key=f"note_area_{mid}")
                if st.button("💾 Save note", key=f"save_note_{mid}"):
                    app_data["notes"][mid] = new_note
                    save_data(app_data)
                    st.session_state[f"edit_note_{mid}"] = False
                    st.rerun()
                if note and st.button("🗑️ Delete note", key=f"del_note_{mid}"):
                    app_data["notes"].pop(mid, None)
                    save_data(app_data)
                    st.session_state[f"edit_note_{mid}"] = False
                    st.rerun()
            if is_pin:
                cur_tag = app_data["pins"][mid].get("tag", PIN_TAGS[5])
                new_tag = st.selectbox("Pin tag", PIN_TAGS, index=PIN_TAGS.index(cur_tag), key=f"tag_{mid}")
                if new_tag != cur_tag:
                    app_data["pins"][mid]["tag"] = new_tag
                    save_data(app_data)
                    st.rerun()
            st.markdown("**Reactions**")
            rcols = st.columns(len(REACTIONS))
            for i, em in enumerate(REACTIONS):
                with rcols[i]:
                    if st.button(em, key=f"react_{mid}_{i}"):
                        rlist = app_data["reactions"].setdefault(mid, [])
                        if em in rlist:
                            rlist.remove(em)
                        else:
                            rlist.append(em)
                        save_data(app_data)
                        st.rerun()
    with col1:
        st.empty()

def date_sep(dt):
    st.markdown(f'<div class="date-sep"><span>{dt.strftime("%B %d, %Y")}</span></div>', unsafe_allow_html=True)

# ── LOGIN ──────────────────────────────────────────────────────────────────────
def check_login():
    if st.session_state.get("logged_in"):
        return True
    st.markdown('<div class="app-header"><h1>💌 Our Chat Memories</h1><p>Just for the two of us 🌸</p></div>', unsafe_allow_html=True)
    _, col, _ = st.columns([1,2,1])
    with col:
        st.subheader("🔐 Enter password")
        pw = st.text_input("Password", type="password")
        if st.button("Enter 💌", use_container_width=True):
            if pw == APP_PASS:
                st.session_state["logged_in"] = True
                st.rerun()
            else:
                st.error("Wrong password 💔")
    return False

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    if not check_login():
        return
    app_data = load_data()
    messages = load_chat_from_file()
    if not messages:
        st.error(f"❌ `{CHAT_FILE}` not found in the repo!")
        st.markdown("""
### What to do:
1. Rename your WhatsApp export file to **`chat.txt`**
2. Put it in the **same folder as `app.py`** in your GitHub repo
3. Commit & push — Streamlit will reload automatically ✅
        """)
        return
    senders = list(dict.fromkeys(m["sender"] for m in messages))
    msg_by_id = {m["id"]: m for m in messages}
    with st.sidebar:
        st.markdown("## 💌 Our Chat")
        st.markdown("---")
        page = st.radio("Go to", ["💬 Chat Viewer","📌 Pinned","❤️ Favorites","🔍 Search","📊 Statistics","📝 Notes","🎲 Random Memory","⚙️ Settings"], label_visibility="collapsed")
        st.markdown("---")
        st.markdown(f"💬 **{len(messages):,}** messages")
        if messages[0]["datetime"].year != 2000:
            span = (messages[-1]["datetime"] - messages[0]["datetime"]).days
            st.markdown(f"📅 **{span:,}** days of chat")
        st.markdown(f"📌 **{len(app_data['pins'])}** pinned")
        st.markdown(f"❤️ **{len(app_data['favorites'])}** favorites")
        st.markdown("---")
        if st.button("🚪 Logout"):
            st.session_state["logged_in"] = False
            st.rerun()
    n1 = app_data["names"][0] or "You"
    n2 = app_data["names"][1] or "Them"
    anniv = app_data.get("anniversary", "")
    sub = ""
    if anniv:
        try:
            diff = (datetime.now() - datetime.strptime(anniv, "%Y-%m-%d")).days
            sub = f"{diff:,} days together 🌸"
        except:
            pass
    st.markdown(f'<div class="app-header"><h1>💌 {n1} & {n2}</h1><p>{sub or "Your private chat archive"}</p></div>', unsafe_allow_html=True)

    # PAGE: Chat Viewer
    if page == "💬 Chat Viewer":
        you = st.selectbox("👤 Which name is yours? (shows on right)", senders, key="you_cv")
        col1, col2, col3 = st.columns([2,2,1])
        with col1: sf = st.multiselect("Filter person", senders, default=senders)
        with col2:
            mn, mx = messages[0]["datetime"].date(), messages[-1]["datetime"].date()
            dr = st.date_input("Date range", value=(mn,mx), min_value=mn, max_value=mx)
        with col3: only = st.selectbox("Show", ["All","Pinned","Favorites"])
        per_page = st.select_slider("Messages per page", [50,100,200,500], value=100)
        filtered = [m for m in messages if m["sender"] in sf]
        if isinstance(dr, (list,tuple)) and len(dr)==2:
            filtered = [m for m in filtered if dr[0] <= m["datetime"].date() <= dr[1]]
        if only=="Pinned": filtered = [m for m in filtered if m["id"] in app_data["pins"]]
        if only=="Favorites": filtered = [m for m in filtered if m["id"] in app_data["favorites"]]
        total_pages = max(1, (len(filtered)-1)//per_page+1)
        _, pc, _ = st.columns([1,2,1])
        with pc: pn = st.number_input(f"Page (1–{total_pages})", 1, total_pages, value=1)-1
        chunk = filtered[pn*per_page:(pn+1)*per_page]
        st.caption(f"Showing {len(chunk)} of {len(filtered):,} messages")
        st.markdown('<div class="chat-area">', unsafe_allow_html=True)
        last_d = None
        for msg in chunk:
            d = msg["datetime"].date()
            if d != last_d:
                date_sep(msg["datetime"])
                last_d = d
            render_bubble(msg, msg["sender"]==you, app_data)
        st.markdown('</div>', unsafe_allow_html=True)

    # PAGE: Pinned (simplified, same pattern)
    elif page == "📌 Pinned":
        st.subheader("📌 Pinned Messages")
        if not app_data["pins"]:
            st.info("No pinned messages yet.")
        else:
            you = st.selectbox("Your name:", senders, key="you_pin")
            tag_f = st.multiselect("Filter tag", PIN_TAGS, default=PIN_TAGS)
            pins = [(mid, msg_by_id[mid], info) for mid, info in app_data["pins"].items() if mid in msg_by_id and info.get("tag", PIN_TAGS[5]) in tag_f]
            st.caption(f"{len(pins)} pinned message(s)")
            for mid, msg, info in pins:
                st.markdown(f'<div class="memory-card"><b>{info.get("tag","📌")}</b> — {msg["datetime"].strftime("%b %d, %Y")}</div>', unsafe_allow_html=True)
                render_bubble(msg, msg["sender"]==you, app_data)
                st.markdown("---")

    # PAGE: Favorites
    elif page == "❤️ Favorites":
        st.subheader("❤️ Favorite Messages")
        if not app_data["favorites"]:
            st.info("No favorites yet.")
        else:
            you = st.selectbox("Your name:", senders, key="you_fav")
            favs = [msg_by_id[mid] for mid in app_data["favorites"] if mid in msg_by_id]
            st.caption(f"{len(favs)} favorite(s)")
            for msg in favs:
                st.markdown(f'<div class="memory-card">❤️ — {msg["datetime"].strftime("%b %d, %Y %I:%M %p")}</div>', unsafe_allow_html=True)
                render_bubble(msg, msg["sender"]==you, app_data)
                st.markdown("---")

    # PAGE: Search
    elif page == "🔍 Search":
        st.subheader("🔍 Search Messages")
        q = st.text_input("Search anything...")
        col1, col2 = st.columns(2)
        with col1: sf2 = st.multiselect("From", senders, default=senders)
        with col2: ci = st.checkbox("Case sensitive")
        if q:
            you = st.selectbox("Your name:", senders, key="you_s")
            flags = 0 if ci else re.IGNORECASE
            res = [m for m in messages if re.search(re.escape(q), m["text"], flags) and m["sender"] in sf2]
            st.success(f"**{len(res)}** result(s)")
            for msg in res[:200]:
                st.markdown(f'<div class="memory-card">{msg["datetime"].strftime("%b %d, %Y")} — {msg["sender"]}</div>', unsafe_allow_html=True)
                render_bubble(msg, msg["sender"]==you, app_data, search_q=q)
                st.markdown("---")
            if len(res)>200: st.info("Showing first 200 results.")
        else:
            st.markdown("#### 💡 Try searching for: love, miss, sorry, birthday")

    # PAGE: Statistics (unchanged – already works)
    elif page == "📊 Statistics":
        st.subheader("📊 Your Chat Stats")
        by_sender = Counter(m["sender"] for m in messages)
        total_words = sum(len(m["text"].split()) for m in messages)
        cols = st.columns(4)
        for col, (num,lbl) in zip(cols, [(f"{len(messages):,}","Messages"),(f"{total_words:,}","Words"),(f"{len(by_sender)}","People"),(f"{(messages[-1]['datetime']-messages[0]['datetime']).days:,}","Days")]):
            with col: st.markdown(f'<div class="stat-box"><div class="num">{num}</div><div class="lbl">{lbl}</div></div>', unsafe_allow_html=True)
        st.markdown("---")
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("#### 💬 Messages by Person")
            fig = px.pie(values=list(by_sender.values()), names=list(by_sender.keys()), color_discrete_sequence=["#667eea","#f093fb","#4facfe","#ffd166"], hole=.4)
            fig.update_layout(margin=dict(t=0,b=0,l=0,r=0), height=260)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("#### 📅 Messages Over Time")
            df = pd.DataFrame(messages)
            df["date"] = df["datetime"].dt.date
            daily = df.groupby("date").size().reset_index(name="count")
            fig2 = px.area(daily, x="date", y="count", color_discrete_sequence=["#667eea"])
            fig2.update_layout(margin=dict(t=0,b=0,l=0,r=0), height=260, xaxis_title="", yaxis_title="")
            st.plotly_chart(fig2, use_container_width=True)
        c3,c4 = st.columns(2)
        with c3:
            st.markdown("#### 🕐 Busiest Hours")
            hours = Counter(m["datetime"].hour for m in messages)
            hdf = pd.DataFrame({"hour":range(24), "count":[hours.get(h,0) for h in range(24)]})
            fig3 = px.bar(hdf, x="hour", y="count", color_discrete_sequence=["#f093fb"])
            fig3.update_layout(margin=dict(t=0,b=0,l=0,r=0), height=260)
            st.plotly_chart(fig3, use_container_width=True)
        with c4:
            st.markdown("#### 📆 Most Active Days")
            top_days = df.groupby("date").size().nlargest(10).reset_index(name="count")
            top_days["date"] = top_days["date"].astype(str)
            fig4 = px.bar(top_days, x="count", y="date", orientation="h", color_discrete_sequence=["#4facfe"])
            fig4.update_layout(margin=dict(t=0,b=0,l=0,r=0), height=260)
            st.plotly_chart(fig4, use_container_width=True)
        st.markdown("---")
        st.markdown("#### 🔤 Most Used Words")
        STOP = {"i","you","the","a","to","and","is","it","in","of","that","me","my","your","for","on","are","this","was","but","be","have","he","she","we","they","with","at","or","an","so","do","not","just","ok","okay","yes","no","oh","yeah","ha","haha","lol","hey","hi","hello","na","bhi","ka","ki","ko","ke","kya","hai","hoon","mera","tera","aur","se","ne","koi","ab","tum","hm","will","can","its","our","im"}
        words = [w for m in messages for w in re.findall(r"[a-zA-Z]{3,}", m["text"].lower()) if w not in STOP]
        top_w = Counter(words).most_common(25)
        if top_w:
            wdf = pd.DataFrame(top_w, columns=["word","count"])
            fig5 = px.bar(wdf, x="count", y="word", orientation="h", color="count", color_continuous_scale="Purples")
            fig5.update_layout(height=450, margin=dict(t=0,b=0,l=0,r=0))
            fig5.update_coloraxes(showscale=False)
            st.plotly_chart(fig5, use_container_width=True)
        st.markdown("#### 😄 Top Emojis")
        ep = re.compile("[\U0001F300-\U0001FFFF\U00002600-\U000027BF]+", flags=re.UNICODE)
        emojis = [c for m in messages for grp in ep.findall(m["text"]) for c in grp]
        top_e = Counter(emojis).most_common(10)
        if top_e:
            ecols = st.columns(len(top_e))
            for col, (e,cnt) in zip(ecols, top_e):
                with col: st.markdown(f'<div class="stat-box"><div class="num">{e}</div><div class="lbl">{cnt:,}×</div></div>', unsafe_allow_html=True)

    # PAGE: Notes
    elif page == "📝 Notes":
        st.subheader("📝 Notes")
        st.markdown("#### 💑 Shared Note")
        cn = st.text_area("Write something to each other...", value=app_data.get("couple_note",""), height=130)
        if st.button("💾 Save"):
            app_data["couple_note"] = cn
            save_data(app_data)
            st.success("Saved! 💖")
        st.markdown("---")
        st.markdown("#### 📌 Notes on Messages")
        noted = [(mid, msg_by_id[mid], note) for mid, note in app_data["notes"].items() if mid in msg_by_id and note.strip()]
        if not noted:
            st.info("No notes yet. Click ⋮ → 📝 Note on any message.")
        else:
            you = st.selectbox("Your name:", senders, key="you_notes")
            for mid, msg, note in noted:
                st.markdown(f'<div class="memory-card">{msg["datetime"].strftime("%b %d, %Y")} — {msg["sender"]}</div>', unsafe_allow_html=True)
                render_bubble(msg, msg["sender"]==you, app_data)
                st.markdown("---")

    # PAGE: Random Memory
    elif page == "🎲 Random Memory":
        st.subheader("🎲 Random Memory")
        you = st.selectbox("Your name:", senders, key="you_rand")
        mode = st.selectbox("Memory type", ["🎲 Any message","❤️ From favorites","📌 From pinned","😂 Funny","🌅 Early days","💖 Love messages"])
        if st.button("✨ Show me a memory!", use_container_width=True):
            pool = messages
            if "favorites" in mode: pool = [msg_by_id[mid] for mid in app_data["favorites"] if mid in msg_by_id]
            elif "pinned" in mode: pool = [msg_by_id[mid] for mid in app_data["pins"] if mid in msg_by_id]
            elif "Funny" in mode: pool = [m for m in messages if re.search(r'haha|lol|😂|🤣', m["text"], re.I)]
            elif "Early" in mode: pool = messages[:100]
            elif "Love" in mode: pool = [m for m in messages if re.search(r'love|miss|❤️|💕|💖', m["text"], re.I)]
            st.session_state["rand_msg"] = random.choice(pool) if pool else None
        if st.session_state.get("rand_msg"):
            msg = st.session_state["rand_msg"]
            st.markdown(f"---\n**📅 {msg['datetime'].strftime('%B %d, %Y — %I:%M %p')}**")
            render_bubble(msg, msg["sender"]==you, app_data)
        st.markdown("---")
        st.markdown("#### 📆 On This Day")
        today = datetime.now()
        otd = [m for m in messages if m["datetime"].month==today.month and m["datetime"].day==today.day and m["datetime"].year!=today.year]
        if otd:
            st.success(f"**{len(otd)}** message(s) on {today.strftime('%B %d')} in past years!")
            for msg in otd[:5]:
                st.markdown(f"**{msg['datetime'].year}**")
                render_bubble(msg, msg["sender"]==you, app_data)
        else:
            st.info(f"No messages found on {today.strftime('%B %d')} in previous years.")

    # PAGE: Settings
    elif page == "⚙️ Settings":
        st.subheader("⚙️ Settings")
        st.markdown("#### 👥 Your Names")
        c1, c2 = st.columns(2)
        with c1: n1 = st.text_input("Your name", value=app_data["names"][0])
        with c2: n2 = st.text_input("Their name", value=app_data["names"][1])
        if st.button("💾 Save names"):
            app_data["names"] = [n1, n2]; save_data(app_data); st.success("Saved! 💖")
        st.markdown("#### 💍 Anniversary")
        av = app_data.get("anniversary","")
        ai = st.date_input("When did you get together?", value=datetime.strptime(av,"%Y-%m-%d").date() if av else None)
        if st.button("💾 Save anniversary"):
            app_data["anniversary"] = str(ai) if ai else ""; save_data(app_data)
            if ai: st.balloons(); st.success(f"🎉 {(datetime.now().date()-ai).days:,} days together!")
        st.markdown("#### 📥 Export Pinned Messages")
        if st.button("📥 Export as .txt"):
            lines = []
            for mid, info in app_data["pins"].items():
                if mid in msg_by_id:
                    m = msg_by_id[mid]
                    lines.append(f"[{m['datetime'].strftime('%Y-%m-%d %H:%M')}] {m['sender']}: {m['text']}")
                    if app_data["notes"].get(mid): lines.append(f"  📝 {app_data['notes'][mid]}")
                    lines.append("")
            if lines: st.download_button("⬇️ Download", "\n".join(lines), "pinned.txt", "text/plain")
            else: st.info("No pinned messages yet.")
        st.markdown("#### 🗑️ Clear Data")
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("Clear all pins"): app_data["pins"]={}; save_data(app_data); st.success("Pins cleared.")
        with cc2:
            if st.button("Clear all favorites"): app_data["favorites"]=[]; save_data(app_data); st.success("Favorites cleared.")
        st.markdown("---")
        st.info(f"🔑 Password is set to: **{APP_PASS}**\nChange `APP_PASS` in `app.py` to update it.")

if __name__ == "__main__":
    main()