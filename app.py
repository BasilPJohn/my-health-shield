import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import json
import pandas as pd
from PIL import Image

# --- 1. SESSION STATE & THEME ---
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

st.set_page_config(page_title="Health Shield", page_icon="🛡️", layout="wide")

def apply_apple_theme():
    # Apple System Colors
    bg = "#FFFFFF" if not st.session_state.dark_mode else "#000000"
    card_bg = "#F2F2F7" if not st.session_state.dark_mode else "#1C1C1E"
    text_color = "#1D1D1F" if not st.session_state.dark_mode else "#F5F5F7"
    accent = "#007AFF" 

    st.markdown(f"""
        <style>
        @import url('https://fonts.cdnfonts.com/css/sf-pro-display-all');
        .stApp {{ background-color: {bg}; color: {text_color}; font-family: 'SF Pro Display', sans-serif; }}
        [data-testid="stSidebar"] {{ background-color: {card_bg} !important; border-right: 1px solid rgba(128,128,128,0.2); }}
        .apple-card {{
            background-color: {card_bg};
            padding: 24px;
            border-radius: 22px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.04);
            margin-bottom: 20px;
            border: 1px solid rgba(128,128,128,0.1);
        }}
        div.stButton > button {{
            background-color: {accent};
            color: white;
            border-radius: 14px;
            border: none;
            padding: 0.7rem 2rem;
            font-weight: 600;
            width: 100%;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        div.stButton > button:hover {{ transform: scale(1.02); background-color: {accent}; }}
        [data-testid="stMetricValue"] {{ color: {accent} !important; font-weight: 800; }}
        .stTabs [data-baseweb="tab-list"] {{ background-color: transparent; }}
        </style>
    """, unsafe_allow_html=True)

apply_apple_theme()

# --- 2. CONNECTIONS ---
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. SIDEBAR: PROFILE & GOALS ---
with st.sidebar:
    st.markdown("### 🛡️ Shield Settings")
    
    # Theme Toggle
    if st.button("🌙 Dark Mode" if not st.session_state.dark_mode else "☀️ Light Mode"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    st.divider()
    
    try:
        profile_df = conn.read(worksheet="Profile")
        p = profile_df.iloc[0] if not profile_df.empty else {"Name": "User", "Weight": 70, "Height": 170, "Age": 25, "Target_Weight": 65}
    except:
        p = {"Name": "User", "Weight": 70, "Height": 170, "Age": 25, "Target_Weight": 65}

    u_name = st.text_input("Name", value=p['Name'])
    u_weight = st.number_input("Weight (kg)", value=float(p['Weight']), step=0.1)
    u_target = st.number_input("Target (kg)", value=float(p['Target_Weight']), step=0.1)
    
    if st.button("Update Profile"):
        # Save to Profile sheet
        upd_p = pd.DataFrame([{"Name": u_name, "Weight": u_weight, "Height": p['Height'], "Age": p['Age'], "Target_Weight": u_target}])
        conn.update(worksheet="Profile", data=upd_p)
        # Save to Weight History
        w_entry = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Weight": u_weight}])
        try:
            old_w = conn.read(worksheet="WeightLog")
            conn.update(worksheet="WeightLog", data=pd.concat([old_w, w_entry], ignore_index=True))
        except: pass
        st.success("Synced to iCloud")
        st.rerun()

    # Clinical Math
    bmr = (10 * u_weight) + (6.25 * p['Height']) - (5 * p['Age']) + 5
    tdee = bmr * 1.2
    daily_goal = int(tdee - 500 if u_weight > u_target else tdee)
    st.metric("Daily Calorie Target", f"{daily_goal} kcal")

# --- 4. MAIN UI ---
st.title(f"Health Shield")
st.write(f"Logged in as **{u_name}**")

tabs = st.tabs(["📸 Camera", "🎙️ Voice", "✏️ Text"])
user_source = None

with tabs[0]: 
    cam_in = st.camera_input("")
    if cam_in: user_source = cam_in
with tabs[1]: 
    voice_in = st.audio_input("Describe your meal")
    if voice_in: user_source = "Voice description provided."
with tabs[2]: 
    text_in = st.text_input("What did you eat?")
    if text_in: user_source = text_in

if st.button("Analyze & Log Meal"):
    if user_source:
        with st.spinner("Gemini 3 evaluating health risks..."):
            prompt = f"Act as a Clinical Dietitian for {u_name}. Goal: {u_target}kg. Analyze for Calories, Protein, Carbs, Fat. Provide a 'note' on health risks. Return JSON ONLY."
            
            # Prepare Data & Model Fallback
            input_content = [prompt, Image.open(cam_in) if cam_in else user_source]
            models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash"]
            
            success = False
            for m_id in models_to_try:
                try:
                    resp = client.models.generate_content(
                        model=m_id, contents=input_content,
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    data = json.loads(resp.text)
                    success = True
                    break
                except: continue
            
            if success:
                # Log to Sheets
                m_row = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d %H:%M"), "Meal": data['food'], "Calories": data['calories'], "Note": data['note']}])
                m_logs = conn.read(worksheet="Log")
                conn.update(worksheet="Log", data=pd.concat([m_logs, m_row], ignore_index=True))
                
                # Result Card
                st.markdown(f"""
                    <div class="apple-card">
                        <h2 style='color:#007AFF; margin-top:0;'>{data['food']}</h2>
                        <h1 style='margin:10px 0;'>{data['calories']} kcal</h1>
                        <p style='font-size:1.1rem; opacity:0.8;'>{data['note']}</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Engine Timeout. Please check your API Key or try again.")

# --- 5. DASHBOARD ---
st.divider()
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.subheader("Weight History")
    try:
        w_df = conn.read(worksheet="WeightLog")
        st.line_chart(w_df.set_index("Date")["Weight"], color="#007AFF")
    except: st.caption("Log your weight to see progress.")
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.subheader("Daily Calories")
    try:
        c_df = conn.read(worksheet="Log")
        c_df['Date Only'] = pd.to_datetime(c_df['Date']).dt.date
        st.bar_chart(c_df.groupby('Date Only')['Calories'].sum(), color="#34C759")
    except: st.caption("Log a meal to see calorie trends.")
    st.markdown('</div>', unsafe_allow_html=True)
