import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import json
import pandas as pd
import plotly.graph_objects as go
import time

# --- 1. THE 10X DESIGN SYSTEM ---
st.set_page_config(page_title="Health Shield OS", page_icon="🛡️", layout="wide")

def apply_pro_design():
    st.markdown("""
        <style>
        @import url('https://fonts.cdnfonts.com/css/sf-pro-display-all');
        
        :root {
            --bg: #FBFBFD;
            --accent: #007AFF;
            --warning: #FF9500;
            --danger: #FF3B30;
            --glass: rgba(255, 255, 255, 0.75);
        }

        .stApp { background: radial-gradient(at 0% 0%, #F0F4FF 0%, #FFFFFF 100%); font-family: 'SF Pro Display', sans-serif; }

        .notification-pill {
            background: rgba(255, 149, 0, 0.1);
            border-left: 5px solid var(--warning);
            padding: 15px;
            border-radius: 15px;
            margin-bottom: 20px;
            color: #1D1D1F;
            font-size: 0.9rem;
            backdrop-filter: blur(10px);
        }

        .apple-card {
            background: var(--glass);
            backdrop-filter: blur(25px);
            border-radius: 24px;
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.4);
            box-shadow: 0 10px 30px rgba(0,0,0,0.03);
            margin-bottom: 20px;
        }

        .stat-header { font-size: 0.75rem; font-weight: 700; color: #86868B; text-transform: uppercase; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

apply_pro_design()

# --- 2. THE INSIGHTS ENGINE ---
def generate_proactive_insights(today_df, goals):
    insights = []
    if today_df.empty: return []
    
    total_cal = today_df['Calories'].sum()
    total_prot = today_df['Protein'].sum()
    
    # Logic 1: Protein Density
    if total_cal > (goals['cal'] * 0.5) and total_prot < (goals['prot'] * 0.3):
        insights.append("⚠️ **Low Protein Warning**: You've used 50% of your calories but only hit 30% of your protein goal. Prioritize lean protein for your next meal.")
    
    # Logic 2: Calorie Front-loading
    if datetime.now().hour < 12 and total_cal > (goals['cal'] * 0.6):
        insights.append("⚖️ **Calorie Surge**: You've consumed over 60% of your budget before noon. Consider lighter snacks for the afternoon.")
        
    return insights

# --- 3. DATA & BACKEND ---
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

# Mock/Fetch Data
try:
    p = conn.read(worksheet="Profile").iloc[0].to_dict()
    log_df = conn.read(worksheet="Log")
    weight_df = conn.read(worksheet="WeightLog")
except:
    p = {"Name": "Alex", "Weight": 80, "Height": 180, "Age": 30, "Target_Weight": 75}
    log_df = pd.DataFrame()
    weight_df = pd.DataFrame()

# Calculated Goals
bmr = (10 * p['Weight']) + (6.25 * p['Height']) - (5 * p['Age']) + 5
cal_goal = int(bmr * 1.25)
prot_goal = int((cal_goal * 0.3) / 4)
carb_goal = int((cal_goal * 0.4) / 4)

# --- 4. TOP NOTIFICATION CENTER ---
if not log_df.empty:
    log_df['Date'] = pd.to_datetime(log_df['Date'])
    today_data = log_df[log_df['Date'].dt.date == datetime.now().date()]
    active_insights = generate_proactive_insights(today_data, {'cal': cal_goal, 'prot': prot_goal})
    
    for alert in active_insights:
        st.markdown(f'<div class="notification-pill">{alert}</div>', unsafe_allow_html=True)

# --- 5. VISUAL DASHBOARD ---
c1, c2, c3 = st.columns([1, 1, 1.2])

with c1:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown('<p class="stat-header">Activity Rings</p>', unsafe_allow_html=True)
    # 
    # (Plotly Ring Code as per previous version)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown('<p class="stat-header">Weight Trend</p>', unsafe_allow_html=True)
    # (Plotly Line Code as per previous version)
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    st.markdown('<div class="apple-card" style="height:350px">', unsafe_allow_html=True)
    st.markdown('<p class="stat-header">Smart Assistant</p>', unsafe_allow_html=True)
    
    for msg in st.session_state.chat_history[-4:]: # Show last 4 messages for focus
        role = "👤" if msg["role"] == "user" else "🛡️"
        st.write(f"{role} {msg['content']}")
    
    text_input = st.chat_input("Log or ask anything...")
    voice_input = st.audio_input("Voice", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
