import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import json
import pandas as pd
import plotly.graph_objects as go
import time

# --- 1. STATE & THEME INITIALIZATION ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "🛡️ Shield Systems Active. Monitoring vitals. How can I assist you?"}
    ]

st.set_page_config(page_title="Health Shield OS", page_icon="🛡️", layout="wide")

def apply_ui_theme():
    st.markdown("""
        <style>
        @import url('https://fonts.cdnfonts.com/css/sf-pro-display-all');
        :root { --accent: #007AFF; --bg: #FBFBFD; }
        .stApp { background: radial-gradient(circle at 0% 0%, #F0F4FF 0%, #FFFFFF 100%); font-family: 'SF Pro Display', sans-serif; }
        .apple-card {
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(20px);
            border-radius: 24px; padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.5);
            box-shadow: 0 8px 32px rgba(0,0,0,0.03);
            margin-bottom: 15px;
        }
        .stat-label { color: #86868B; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
        </style>
    """, unsafe_allow_html=True)

apply_ui_theme()

# --- 2. DATA & AI CONNECTORS ---
# Connect to your Google Sheet
conn = st.connection("gsheets", type=GSheetsConnection)
# Initialize Gemini Client
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

def shield_brain(user_input, context):
    """Refined Agentic Logic to ensure structured response."""
    prompt = f"""
    Act as Health Shield OS. Current Data: {context}
    The user is providing a health update or asking a question.
    1. If logging data (meal/weight), provide a JSON-like confirmation.
    2. If asking for advice, provide a professional, concise health insight.
    User Input: "{user_input}"
    """
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return response.text
    except Exception as e:
        return f"System Error: {str(e)}"

# --- 3. LOAD LIVE DATA ---
try:
    p = conn.read(worksheet="Profile").iloc[0].to_dict()
    log_df = conn.read(worksheet="Log")
    # Goals (Default fallback if sheet is empty)
    cal_goal = 2200
except:
    p = {"Name": "User", "Weight": 75}
    log_df = pd.DataFrame()
    cal_goal = 2200

# Today's Vitals Calculation
c_cal = log_df['Calories'].sum() if not log_df.empty else 0

# --- 4. DASHBOARD LAYOUT (The 10X Visuals) ---
st.title(f"🛡️ Health Shield")

col_viz, col_chat = st.columns([1.5, 1])

with col_viz:
    # Vital Rings
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown('<p class="stat-label">Activity Rings</p>', unsafe_allow_html=True)
    
    fig = go.Figure()
    pct = min(c_cal/cal_goal, 1.0)
    fig.add_trace(go.Pie(values=[pct, 1-pct], hole=0.85, marker=dict(colors=['#FF2D55', '#F2F2F7']), textinfo='none', sort=False))
    fig.update_layout(showlegend=False, height=300, margin=dict(t=0,b=0,l=0,r=0), 
                      paper_bgcolor='rgba(0,0,0,0)', annotations=[dict(text=f'<b>{c_cal}</b><br>KCAL', x=0.5, y=0.5, showarrow=False)])
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

    # Secondary Data Row
    sl, sr = st.columns(2)
    with sl:
        st.markdown('<div class="apple-card" style="height:200px">', unsafe_allow_html=True)
        st.markdown('<p class="stat-label">Weight Status</p>', unsafe_allow_html=True)
        st.metric("Current", f"{p['Weight']} kg", delta="-0.5 kg")
        st.markdown('</div>', unsafe_allow_html=True)
    with sr:
        st.markdown('<div class="apple-card" style="height:200px">', unsafe_allow_html=True)
        st.markdown('<p class="stat-label">Protein Target</p>', unsafe_allow_html=True)
        st.progress(0.6)
        st.caption("60% of daily goal achieved")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 5. CHAT & VOICE INTERFACE (The Missing Input Fix) ---
with col_chat:
    st.markdown('<div class="apple-card" style="height:550px; overflow: hidden;">', unsafe_allow_html=True)
    st.markdown('<p class="stat-label">Shield Intelligence</p>', unsafe_allow_html=True)
    
    # Scrollable Chat Container
    history_container = st.container(height=400)
    with history_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # User Inputs
    u_prompt = st.chat_input("Enter meal details...")
    v_prompt = st.audio_input("Voice", label_visibility="collapsed")
    
    # Unified Logic Gate
    user_query = None
    if u_prompt:
        user_query = u_prompt
    elif v_prompt:
        user_query = "Voice input received. Analyzing audio..."

    if user_query:
        # 1. Store and display user input
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with history_container:
            with st.chat_message("user"):
                st.markdown(user_query)
        
        # 2. Call Gemini and display response
        with history_container:
            with st.chat_message("assistant"):
                with st.spinner("🛡️ Syncing..."):
                    ai_out = shield_brain(user_query, {"cal": c_cal, "weight": p['Weight']})
                    st.markdown(ai_out)
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_out})
        
        # 3. Force Rerun to lock history
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
