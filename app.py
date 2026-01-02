import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import json
import pandas as pd
import plotly.graph_objects as go
import time

# --- 1. CORE INITIALIZATION ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": "🛡️ Shield Online. I'm monitoring your vitals. How can I help?"}]

st.set_page_config(page_title="Health Shield OS", page_icon="🛡️", layout="wide")

# --- 2. 10X GLASSMORPHISM UI ---
st.markdown("""
    <style>
    @import url('https://fonts.cdnfonts.com/css/sf-pro-display-all');
    :root {
        --bg: #FBFBFD;
        --accent: #007AFF;
        --warning: #FF9500;
        --glass: rgba(255, 255, 255, 0.85);
    }
    .stApp { background: radial-gradient(at 0% 0%, #F0F4FF 0%, #FFFFFF 100%); font-family: 'SF Pro Display', sans-serif; }
    .apple-card {
        background: var(--glass);
        backdrop-filter: blur(30px);
        border-radius: 28px;
        padding: 24px;
        border: 1px solid rgba(255, 255, 255, 0.6);
        box-shadow: 0 10px 40px rgba(0,0,0,0.03);
        margin-bottom: 20px;
    }
    .notification-pill {
        background: rgba(255, 149, 0, 0.1);
        border-left: 5px solid var(--warning);
        padding: 15px; border-radius: 15px; margin-bottom: 20px;
        color: #1D1D1F; font-weight: 500; backdrop-filter: blur(10px);
    }
    .stat-header { font-size: 0.75rem; font-weight: 700; color: #86868B; text-transform: uppercase; letter-spacing: 0.05em; }
    </style>
""", unsafe_allow_html=True)

# --- 3. AI AGENT & DATA ENGINE ---
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

def shield_agent(user_input, stats):
    prompt = f"""Act as Health Shield OS. Current Stats: {stats}. 
    Analyze input and return ONLY JSON for intent: meal, weight, profile, recommend, or grocery.
    Example Meal: {{"intent": "meal", "food": "apple", "calories": 95, "protein": 1, "carbs": 25, "fat": 0, "type": "Snack", "note": "Healthy choice"}}"""
    try:
        resp = client.models.generate_content(
            model="gemini-2.0-flash", contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(resp.text)
    except: return None

# Load Data
try:
    p = conn.read(worksheet="Profile").iloc[0].to_dict()
    log_df = conn.read(worksheet="Log")
    weight_df = conn.read(worksheet="WeightLog")
except:
    p = {"Name": "User", "Weight": 75, "Height": 175, "Age": 30, "Target_Weight": 70}
    log_df, weight_df = pd.DataFrame(), pd.DataFrame()

# Goals Calculation
bmr = (10 * p['Weight']) + (6.25 * p['Height']) - (5 * p['Age']) + 5
cal_goal = int(bmr * 1.3)
prot_goal, carb_goal = int((cal_goal*0.3)/4), int((cal_goal*0.4)/4)

# Today's Vitals
if not log_df.empty:
    log_df['Date'] = pd.to_datetime(log_df['Date'])
    today_data = log_df[log_df['Date'].dt.date == datetime.now().date()]
    c_cal, c_prot, c_carb = today_data['Calories'].sum(), today_data['Protein'].sum(), today_data['Carbs'].sum()
else:
    c_cal, c_prot, c_carb = 0, 0, 0
    today_data = pd.DataFrame()

# --- 4. TOP NOTIFICATIONS (Proactive Insights) ---
if c_cal > (cal_goal * 0.7) and c_prot < (prot_goal * 0.4):
    st.markdown('<div class="notification-pill">⚠️ **Insight**: Your protein ratio is low relative to calories today. Suggesting lean protein for next meal.</div>', unsafe_allow_html=True)

# --- 5. THE DASHBOARD ---
st.title(f"🛡️ Health Shield OS")
col_vis, col_chat = st.columns([1.5, 1])

with col_vis:
    # Row 1: Triple Rings
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown('<p class="stat-header">Activity & Macros</p>', unsafe_allow_html=True)
    fig = go.Figure()
    rings = [(c_cal/cal_goal, '#FF2D55', 0.9), (c_prot/prot_goal, '#34C759', 0.72), (c_carb/carb_goal, '#007AFF', 0.54)]
    for v, c, r in rings:
        fig.add_trace(go.Pie(values=[min(v, 1.0), max(0, 1-v)], hole=r, marker=dict(colors=[c, '#F2F2F7']), textinfo='none', sort=False))
    fig.update_layout(showlegend=False, height=350, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)',
                      annotations=[dict(text=f'<b>{c_cal}</b><br>KCAL', x=0.5, y=0.5, font_size=20, showarrow=False)])
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Row 2: Weight & Ledger
    sub_l, sub_r = st.columns(2)
    with sub_l:
        st.markdown('<div class="apple-card" style="height:280px">', unsafe_allow_html=True)
        st.markdown('<p class="stat-header">Weight Journey</p>', unsafe_allow_html=True)
        if not weight_df.empty:
            st.line_chart(weight_df.set_index('Date')['Weight'], height=180)
        st.markdown('</div>', unsafe_allow_html=True)
    with sub_r:
        st.markdown('<div class="apple-card" style="height:280px; overflow-y:auto">', unsafe_allow_html=True)
        st.markdown('<p class="stat-header">Today\'s Ledger</p>', unsafe_allow_html=True)
        for _, row in today_data.iterrows():
            st.markdown(f"**{row['Meal']}** • {row['Calories']} kcal")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 6. CHAT & VOICE INTERFACE ---
with col_chat:
    st.markdown('<div class="apple-card" style="height:550px; overflow-y:auto">', unsafe_allow_html=True)
    st.markdown('<p class="stat-header">Secure Communication</p>', unsafe_allow_html=True)
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.write(msg["content"])
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Dual Input Logic
    u_prompt = st.chat_input("Tell Shield your lunch or weight...")
    v_prompt = st.audio_input("Voice Input", label_visibility="collapsed")
    
    input_to_process = u_prompt if u_prompt else ("Process voice entry" if v_prompt else None)
    
    if input_to_process:
        st.session_state.chat_history.append({"role": "user", "content": input_to_process})
        with st.spinner("Shielding..."):
            res = shield_agent(input_to_process, {"cal": c_cal, "prot": c_prot})
            if res:
                # Handle Logic (Same as before)
                st.session_state.chat_history.append({"role": "assistant", "content": f"Processed {res['intent']}."})
                time.sleep(1)
                st.rerun()
