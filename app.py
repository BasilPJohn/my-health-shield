import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import json
import pandas as pd
from PIL import Image

# --- 1. INITIALIZE THEME STATE ---
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# --- 2. APPLE DESIGN SYSTEM (CSS) ---
def apply_theme():
    # Apple Color Palette
    bg = "#FFFFFF" if not st.session_state.dark_mode else "#000000"
    card_bg = "#F2F2F7" if not st.session_state.dark_mode else "#1C1C1E"
    text_color = "#1D1D1F" if not st.session_state.dark_mode else "#F5F5F7"
    accent = "#007AFF" # Apple Blue

    st.markdown(f"""
        <style>
        @import url('https://fonts.cdnfonts.com/css/sf-pro-display-all');
        
        .stApp {{
            background-color: {bg};
            color: {text_color};
            font-family: 'SF Pro Display', sans-serif;
        }}

        /* Glassmorphism sidebar */
        [data-testid="stSidebar"] {{
            background-color: {card_bg} !important;
            border-right: 1px solid rgba(128,128,128,0.2);
        }}

        /* iOS-style Rounded Cards */
        .apple-card {{
            background-color: {card_bg};
            padding: 20px;
            border-radius: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }}

        /* Apple Blue Buttons */
        div.stButton > button {{
            background-color: {accent};
            color: white;
            border-radius: 12px;
            border: none;
            padding: 0.6rem 2rem;
            font-weight: 600;
            width: 100%;
        }}

        /* Metrics Styling */
        [data-testid="stMetricLabel"] {{ color: {text_color} !important; opacity: 0.7; }}
        [data-testid="stMetricValue"] {{ color: {accent} !important; }}
        
        /* Tab Styling */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 10px;
            background-color: {card_bg};
            padding: 5px;
            border-radius: 15px;
        }}
        </style>
    """, unsafe_allow_html=True)

st.set_page_config(page_title="Shield", page_icon="🛡️", layout="wide")
apply_theme()

# --- 3. CONNECTIONS & DATA ---
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 4. SIDEBAR: PROFILE & THEME TOGGLE ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg" if not st.session_state.dark_mode else "https://upload.wikimedia.org/wikipedia/commons/a/ab/Apple-logo.png", width=30)
    
    # Theme Toggle
    toggle_label = "🌙 Dark Mode" if not st.session_state.dark_mode else "☀️ Light Mode"
    if st.button(toggle_label):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
    
    st.divider()
    
    try:
        profile_df = conn.read(worksheet="Profile")
        p_data = profile_df.iloc[0] if not profile_df.empty else {"Name": "User", "Weight": 70.0, "Height": 170.0, "Age": 25, "Target_Weight": 70.0}
    except:
        p_data = {"Name": "User", "Weight": 70.0, "Height": 170.0, "Age": 25, "Target_Weight": 70.0}

    user_name = st.text_input("Name", value=p_data['Name'])
    new_weight = st.number_input("Current Weight (kg)", value=float(p_data['Weight']))
    target_weight = st.number_input("Goal Weight (kg)", value=float(p_data['Target_Weight']))
    
    if st.button("Save Daily Update"):
        upd = pd.DataFrame([{"Name": user_name, "Weight": new_weight, "Height": p_data['Height'], "Age": p_data['Age'], "Target_Weight": target_weight}])
        conn.update(worksheet="Profile", data=upd)
        
        weight_log = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Weight": new_weight}])
        try:
            old_w = conn.read(worksheet="WeightLog")
            conn.update(worksheet="WeightLog", data=pd.concat([old_w, weight_log], ignore_index=True))
        except: pass
        st.success("Cloud Synced")

    # Target Math
    bmr = (10 * new_weight) + (6.25 * p_data['Height']) - (5 * p_data['Age']) + 5
    daily_cal = int(bmr * 1.2) - (500 if new_weight > target_weight else 0)
    st.metric("Daily Target", f"{daily_cal} kcal")

# --- 5. MAIN CONTENT ---
st.title(f"Health Shield")
st.write(f"Good {'Evening' if datetime.now().hour > 17 else 'Day'}, {user_name}")

# Capture Interface
tabs = st.tabs(["📸 Camera", "🎙️ Voice", "✏️ Manual"])

user_input = None
with tabs[0]: img = st.camera_input("")
with tabs[1]: audio = st.audio_input("Describe your meal")
with tabs[2]: text = st.text_input("Enter meal details")

if st.button("Analyze Nutrition"):
    source = img if img else (text if text else "Voice update")
    if source:
        with st.spinner("Clinical AI Processing..."):
            prompt = f"Clinical Dietitian Mode. User Goal: {target_weight}kg. Analyze for Calories and health risks. Return JSON."
            response = client.models.generate_content(
                model="gemini-3-flash",
                contents=[prompt, source],
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            data = json.loads(response.text)
            
            # Save Log
            meal_row = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d %H:%M"), "Meal": data['food'], "Calories": data['calories'], "Note": data['note']}])
            logs = conn.read(worksheet="Log")
            conn.update(worksheet="Log", data=pd.concat([logs, meal_row], ignore_index=True))
            
            st.markdown(f"""<div class="apple-card"><h3>{data['food']}</h3><p>{data['calories']} kcal</p><p style='color:#007AFF'>{data['note']}</p></div>""", unsafe_allow_html=True)

# --- 6. HISTORY DASHBOARD ---
st.divider()
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.subheader("Weight Tracking")
    try:
        w_df = conn.read(worksheet="WeightLog")
        st.line_chart(w_df.set_index("Date")["Weight"])
    except: st.write("No weight data found.")
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.subheader("Calorie Trends")
    try:
        c_df = conn.read(worksheet="Log")
        c_df['Date Only'] = pd.to_datetime(c_df['Date']).dt.date
        st.bar_chart(c_df.groupby('Date Only')['Calories'].sum())
    except: st.write("No meal data found.")
    st.markdown('</div>', unsafe_allow_html=True)
