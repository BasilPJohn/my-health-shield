import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import json
import pandas as pd
import plotly.graph_objects as go
import time

# --- 1. MANDATORY SESSION INITIALIZATION (Fixes your error) ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 2. 10X DESIGN SYSTEM ---
st.set_page_config(page_title="Health Shield OS", page_icon="🛡️", layout="wide")

def apply_pro_design():
    st.markdown("""
        <style>
        @import url('https://fonts.cdnfonts.com/css/sf-pro-display-all');
        :root {
            --bg: #FBFBFD;
            --accent: #007AFF;
            --warning: #FF9500;
            --glass: rgba(255, 255, 255, 0.8);
        }
        .stApp { background: radial-gradient(at 0% 0%, #F0F4FF 0%, #FFFFFF 100%); font-family: 'SF Pro Display', sans-serif; }
        .notification-pill {
            background: rgba(255, 149, 0, 0.12);
            border-left: 5px solid var(--warning);
            padding: 16px;
            border-radius: 18px;
            margin-bottom: 25px;
            color: #1D1D1F;
            font-weight: 500;
            backdrop-filter: blur(10px);
        }
        .apple-card {
            background: var(--glass);
            backdrop-filter: blur(25px);
            border-radius: 28px;
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.5);
            box-shadow: 0 10px 40px rgba(0,0,0,0.04);
            margin-bottom: 20px;
        }
        .stat-header { font-size: 0.75rem; font-weight: 700; color: #86868B; text-transform: uppercase; letter-spacing: 0.05em; }
        </style>
    """, unsafe_allow_html=True)

apply_pro_design()

# --- 3. PROACTIVE INSIGHTS LOGIC ---
def get_insights(df, goals):
    alerts = []
    if df.empty: return alerts
    total_cal = df['Calories'].sum()
    total_prot = df['Protein'].sum()
    
    if total_cal > (goals['cal'] * 0.5) and total_prot < (goals['prot'] * 0.3):
        alerts.append("⚠️ **Protein Deficit:** You've used half your calories but hit <30% protein. Try Greek yogurt or turkey for your next snack.")
    if datetime.now().hour < 12 and total_cal > (goals['cal'] * 0.6):
        alerts.append("⚖️ **Calorie Pace:** You've consumed 60% of your daily budget before noon. Aim for a high-fiber, low-cal lunch.")
    return alerts

# --- 4. BACKEND & DATA ---
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    p = conn.read(worksheet="Profile").iloc[0].to_dict()
    log_df = conn.read(worksheet="Log")
    weight_df = conn.read(worksheet="WeightLog")
except:
    p = {"Name": "User", "Weight": 80, "Height": 180, "Age": 30, "Target_Weight": 75}
    log_df, weight_df = pd.DataFrame(), pd.DataFrame()

# Dynamic Goals
bmr = (10 * p['Weight']) + (6.25 * p['Height']) - (5 * p['Age']) + 5
cal_goal = int(bmr * 1.25)
prot_goal, carb_goal = int((cal_goal * 0.3) / 4), int((cal_goal * 0.4) / 4)

# --- 5. TOP NOTIFICATION BAR ---
if not log_df.empty:
    log_df['Date'] = pd.to_datetime(log_df['Date'])
    today_data = log_df[log_df['Date'].dt.date == datetime.now().date()]
    for alert in get_insights(today_data, {'cal': cal_goal, 'prot': prot_goal}):
        st.markdown(f'<div class="notification-pill">{alert}</div>', unsafe_allow_html=True)
    c_cal, c_prot, c_carb = today_data['Calories'].sum(), today_data['Protein'].sum(), today_data['Carbs'].sum()
else:
    c_cal, c_prot, c_carb = 0, 0, 0

# --- 6. DASHBOARD LAYOUT ---
st.title(f"🛡️ Health Shield")
c_vis, c_chat = st.columns([1.4, 1])

with c_vis:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown('<p class="stat-header">Activity Rings</p>', unsafe_allow_html=True)
    fig = go.Figure()
    # High-end concentric rings
    colors = ['#FF2D55', '#34C759', '#007AFF']
    vals = [c_cal/cal_goal, c_prot/prot_goal, c_carb/carb_goal]
    radii = [0.9, 0.72, 0.54]
    
    for v, c, r in zip(vals, colors, radii):
        v_clip = min(v, 1.0)
        fig.add_trace(go.Pie(values=[v_clip, 1-v_clip], hole=r, marker=dict(colors=[c, '#F2F2F7']), 
                             textinfo='none', sort=False, direction='clockwise'))
    
    fig.update_layout(showlegend=False, height=350, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)',
                      annotations=[dict(text=f'<b>{c_cal}</b>', x=0.5, y=0.5, font_size=24, showarrow=False)])
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with c_chat:
    st.markdown('<div class="apple-card" style="height:530px; overflow-y: auto;">', unsafe_allow_html=True)
    st.markdown('<p class="stat-header">AI Assistant</p>', unsafe_allow_html=True)
    
    # Safe check for chat history
    for msg in st.session_state.chat_history[-6:]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Input Area
    prompt = st.chat_input("Log meal or ask for recommendations...")
    voice = st.audio_input("Voice Command", label_visibility="collapsed")
    
    raw_in = prompt if prompt else ("Voice Entry" if voice else None)
    
    if raw_in:
        st.session_state.chat_history.append({"role": "user", "content": raw_in})
        # AI logic would go here...
        st.rerun()
