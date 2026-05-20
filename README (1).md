# 💌 Our Chat Memories

## 🚀 Deploy in 5 minutes (FREE)

### Step 1 — Prepare your files
Put these 3 files in ONE folder:
```
app.py
requirements.txt
chat.txt        ← rename your WhatsApp export to exactly this
```

### Step 2 — Push to GitHub
1. Go to [github.com](https://github.com) → New repository → name it anything (e.g. `our-chat`)
2. Upload all 3 files

### Step 3 — Deploy on Streamlit
1. Go to [share.streamlit.io](https://share.streamlit.io) → sign in with GitHub
2. Click **New app** → pick your repo → main file = `app.py`
3. Hit **Deploy** → live in ~2 minutes ✅
4. Share the URL with her 💕

---

## 🔑 Change the password
Open `app.py`, find line 12:
```python
APP_PASS = "ourlove"   ← change this
```
Push to GitHub → Streamlit auto-redeploys.

---

## 📤 How to export WhatsApp chat

**Android:** Open chat → ⋮ → More → Export chat → **Without media** → save as `chat.txt`

**iPhone:** Open chat → tap contact name → Export Chat → **Without Media** → save as `chat.txt`

---

## ✨ Features
- 💬 Chat Viewer with WhatsApp-style bubbles
- 📌 Pin messages with categories (Sweet, Funny, Important, Milestone...)
- ❤️ Favorite messages
- 😄 React to messages (❤️ 😂 😍 🔥...)
- 📝 Add notes to any message + a shared couple note
- 🔍 Search with keyword highlighting
- 📊 Stats: charts, top words, emoji counts, busiest hours
- 🎲 Random Memory + "On This Day" from past years
- 🔐 Password protected
