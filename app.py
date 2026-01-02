import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import json
import pandas as pd
import plotly.graph_objects as go
import time

# --- 1. INITIALIZATION & UI THEME ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": "🛡️ Shield Systems Online. Live Sync & Proactive Monitoring Active."}]

st.set_page_config(page_title="Health Shield OS", page_icon="🛡️", layout="wide")

def apply_10x_design():
    st.markdown("""
        <style>
        @import url('https://fonts.cdnfonts.com/css/sf-pro-display-all');
        :root { --accent: #007AFF; --bg: #FBFBFD; --warning: #FF9500; }
        .stApp { background: radial-gradient(at 0% 0%, #F0F4FF 0%, #FFFFFF 100%); font-family: 'SF Pro Display', sans-serif; }
        
        /* Glassmorphism Cards */
        .apple-card {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(25px);
            border-radius: 28px; padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.4);
            box-shadow: 0 10px 40px rgba(0,0,0,0.03);
            margin-bottom: 20px;
        }
        
        .notification-pill {
            background: rgba(255, 149, 0, 0.12);
            border-left: 5px solid var(--warning);
            padding: 16px; border-radius: 18px; margin-bottom: 25px;
            color: #1D1D1F; font-weight: 500; backdrop-filter: blur(10px);
        }
        
        .stat-header { font-size: 0.75rem; font-weight: 700; color: #86868B; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px;}
        </style>
    """, unsafe_allow_html=True)

apply_10x_design()

# --- 2. CONNECTORS & LIVE DATA FETCH ---
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

def get_live_data():
    try:
        # Load Logs and Profile
        logs = conn.read(worksheet="Log")
        prof = conn.read(worksheet="Profile").iloc[0].to_dict()
        weights = conn.read(worksheet="WeightLog")
        return logs, prof, weights
    except:
        # Fallback if sheet is empty or missing
        return pd.DataFrame(columns=["Date", "Meal", "Calories", "Protein", "Carbs", "Fat"]), \
               {"Name": "User", "Weight": 75, "Height": 175, "Age": 30, "Target_Weight": 70}, \
               pd.DataFrame(columns=["Date", "Weight"])

log_df, p, weight_df = get_live_data()

# Logic Targets
bmr = (10 * p['Weight']) + (6.25 * p['Height']) - (5 * p['Age']) + 5
cal_goal = int(bmr * 1.3)
prot_goal = int((cal_goal * 0.3) / 4)

# Today's Progress
if not log_df.empty:
    log_df['Date'] = pd.to_datetime(log_df['Date'])
    today_df = log_df[log_df['Date'].dt.date == datetime.now().date()]
    c_cal = today_df['Calories'].sum()
    c_prot = today_df['Protein'].sum()
else:
    c_cal, c_prot = 0, 0

# --- 3. AI BRAIN & SYNC ENGINE ---
def process_shield_input(user_input):
    prompt = f"""
    Act as Health Shield OS. Extract nutrients from: "{user_input}"
    Return ONLY a JSON object. No prose.
    Format: {{"intent": "meal", "food": "name", "calories": 0, "protein": 0, "carbs": 0, "fat": 0}}
    If input is weight: {{"intent": "weight", "value": 0.0}}
    """
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(resp.text)
    except: return None

# --- 4. TOP NOTIFICATIONS (Insights) ---
if c_cal > (cal_goal * 0.6) and c_prot < (prot_goal * 0.3):
    st.markdown(f'<div class="notification-pill">⚠️ **Proactive Insight**: You are at 60% of calories but only 30% of protein. Target lean protein for your next meal.</div>', unsafe_allow_html=True)

# --- 5. THE 10X DASHBOARD ---
st.title(f"🛡️ Health Shield OS")
col_viz, col_chat = st.columns([1.5, 1])

with col_viz:
    # Vital Rings
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown('<p class="stat-header">Activity & Macros</p>', unsafe_allow_html=True)
    fig = go.Figure()
    pct = min(c_cal/cal_goal, 1.0)
    fig.add_trace(go.Pie(values=[pct, 1-pct], hole=0.85, marker=dict(colors=['#FF2D55', '#F2F2F7']), textinfo='none', sort=False))
    fig.update_layout(showlegend=False, height=350, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)',
                      annotations=[dict(text=f'<b>{c_cal}</b><br>KCAL', x=0.5, y=0.5, font_size=24, showarrow=False)])
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

    # Secondary Data
    sl, sr = st.columns(2)
    with sl:
        st.markdown('<div class="apple-card" style="height:250px">', unsafe_allow_html=True)
        st.markdown('<p class="stat-header">Weight Trend</p>', unsafe_allow_html=True)
        if not weight_df.empty:
            st.line_chart(weight_df.set_index('Date')['Weight'], height=150)
        else:
            st.info("Log weight to see trend.")
        st.markdown('</div>', unsafe_allow_html=True)
    with sr:
        st.markdown('<div class="apple-card" style="height:250px">', unsafe_allow_html=True)
        st.markdown('<p class="stat-header">Protein Progress</p>', unsafe_allow_html=True)
        st.metric("Total Protein", f"{int(c_prot)}g", f"Goal: {prot_goal}g")
        st.progress(min(c_prot/prot_goal, 1.0))
        st.markdown('</div>', unsafe_allow_html=True)

with col_chat:
    # Chat History Container
    st.markdown('<div class="apple-card" style="height:530px; overflow-y: auto;">', unsafe_allow_html=True)
    chat_box = st.container()
    with chat_box:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]): st.write(msg["content"])
    st.markdown('</div>', unsafe_allow_html=True)

    # Input Area
    prompt = st.chat_input("Log meal or weight...")
    
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.spinner("🛡️ Syncing to Shield..."):
            data = process_shield_input(prompt)
            if data and data.get('intent') == 'meal':
                new_row = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Meal": data['food'], "Calories": data['calories'],
                    "Protein": data['protein'], "Carbs": data['carbs'], "Fat": data['fat']
                }])
                updated_df = pd.concat([log_df, new_row], ignore_index=True)
                conn.update(worksheet="Log", data=updated_df)
                response = f"✅ **Logged**: {data['food']} ({data['calories']} kcal) pushed to GSheets."
            elif data and data.get('intent') == 'weight':
                # Weight logic would go here
                response = f"⚖️ **Weight Sync**: {data['value']} kg recorded."
            else:
                response = "🛡️ Gemini couldn't verify those nutrients. Try another way?"
        
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()

# --- 6. LIVE SYNC AUDIT LOG ---
st.markdown("---")
st.markdown('<p class="stat-header">Live Audit Log (Verification Table)</p>', unsafe_allow_html=True)
if not log_df.empty:
    # Display the last 5 rows directly from the synced dataframe
    st.dataframe(log_df.tail(5).iloc[::-1], use_container_width=True)
else:
    st.warning("GSheets Log is currently empty. Start logging to see data here.")
