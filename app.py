import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import json
import pandas as pd
import time

# --- 1. SESSION STATE & UI THEME ---
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "meal_input" not in st.session_state:
    st.session_state.meal_input = None

st.set_page_config(page_title="Health Shield", page_icon="🛡️", layout="wide")

def apply_apple_theme():
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
            background-color: {card_bg}; padding: 24px; border-radius: 22px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.04); margin-bottom: 20px;
            border: 1px solid rgba(128,128,128,0.1);
        }}
        div.stButton > button {{
            background-color: {accent}; color: white; border-radius: 14px;
            padding: 0.7rem 2rem; font-weight: 600; width: 100%; border: none;
        }}
        [data-testid="stMetricValue"] {{ color: {accent} !important; font-weight: 800; }}
        </style>
    """, unsafe_allow_html=True)

apply_apple_theme()

# --- 2. CONNECTIONS ---
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. SIDEBAR: PROFILE ---
with st.sidebar:
    st.markdown("### 🛡️ Shield Settings")
    if st.button("🌙 Dark Mode" if not st.session_state.dark_mode else "☀️ Light Mode"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    st.divider()
    
    try:
        profile_df = conn.read(worksheet="Profile")
        p = profile_df.iloc[0].to_dict() if not profile_df.empty else {"Name": "User", "Weight": 70.0, "Height": 170.0, "Age": 25, "Target_Weight": 65.0}
    except:
        p = {"Name": "User", "Weight": 70.0, "Height": 170.0, "Age": 25, "Target_Weight": 65.0}

    u_name = st.text_input("Name", value=p.get('Name', 'User'))
    u_age = st.number_input("Age", value=int(p.get('Age', 25)))
    u_height = st.number_input("Height (cm)", value=float(p.get('Height', 170.0)))
    u_weight = st.number_input("Weight (kg)", value=float(p.get('Weight', 70.0)))
    u_target = st.number_input("Target Weight (kg)", value=float(p.get('Target_Weight', 65.0)))
    
    if st.button("Update Profile & Log Weight"):
        new_p_df = pd.DataFrame([{"Name": u_name, "Age": u_age, "Height": u_height, "Weight": u_weight, "Target_Weight": u_target}])
        conn.update(worksheet="Profile", data=new_p_df)
        
        w_entry = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Weight": u_weight}])
        try:
            old_w = conn.read(worksheet="WeightLog")
            combined_w = pd.concat([old_w, w_entry], ignore_index=True).drop_duplicates(subset=['Date'], keep='last')
            conn.update(worksheet="WeightLog", data=combined_w)
        except:
            conn.update(worksheet="WeightLog", data=w_entry)
        st.success("Profile Updated")
        st.rerun()

    # Mifflin-St Jeor Calculation
    bmr = (10 * u_weight) + (6.25 * u_height) - (5 * u_age) + 5
    daily_goal = int((bmr * 1.2) - (500 if u_weight > u_target else 0))
    st.metric("Daily Target", f"{daily_goal} kcal")

# --- 4. MAIN INTERFACE ---
st.title("Health Shield")
# FIXED LINE BELOW
st.write(f"Hello, **{u_name}**")

tabs = st.tabs(["🎙️ Voice Command", "✏️ Text Entry"])

with tabs[0]:
    audio = st.audio_input("Describe your meal")
    if audio: 
        st.session_state.meal_input = "User provided audio description of a meal."
with tabs[1]:
    txt = st.text_input("What did you eat?")
    if txt: 
        st.session_state.meal_input = txt

if st.button("🚀 Analyze & Log"):
    if st.session_state.meal_input:
        with st.spinner("AI Analysis..."):
            prompt = f"Dietitian Mode for {u_name}. Analyze meal. Return JSON ONLY: {{'food': str, 'calories': int, 'protein': int, 'carbs': int, 'fat': int, 'note': str}}"
            
            success = False
            for model_id in ["gemini-2.0-flash", "gemini-1.5-flash"]:
                try:
                    resp = client.models.generate_content(
                        model=model_id, 
                        contents=[prompt, st.session_state.meal_input],
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    data = json.loads(resp.text)
                    success = True
                    break
                except Exception as e:
                    if "429" in str(e):
                        time.sleep(1)
                        continue
                    else:
                        st.error(f"Error: {e}")
                        break
            
            if success:
                new_meal = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Meal": data['food'], "Calories": data['calories'],
                    "Protein": data['protein'], "Carbs": data['carbs'],
                    "Fat": data['fat'], "Note": data['note']
                }])
                history = conn.read(worksheet="Log")
                conn.update(worksheet="Log", data=pd.concat([history, new_meal], ignore_index=True))
                st.markdown(f"""<div class="apple-card"><h2 style='color:#007AFF'>{data['food']}</h2><h1>{data['calories']} kcal</h1><p>{data['note']}</p></div>""", unsafe_allow_html=True)
                st.session_state.meal_input = None
            else:
                st.error("Engines busy. Try again in 1 min.")
    else:
        st.warning("Please enter a meal description.")

# --- 5. DASHBOARD & JOURNAL ---
st.divider()
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.subheader("Weight History")
    try:
        w_df = conn.read(worksheet="WeightLog")
        st.line_chart(w_df.set_index("Date")["Weight"], color="#007AFF")
    except: st.info("No weight logs.")
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.subheader("Calorie Trends")
    try:
        l_df = conn.read(worksheet="Log")
        l_df['Day'] = pd.to_datetime(l_df['Date']).dt.date
        st.bar_chart(l_df.groupby('Day')['Calories'].sum(), color="#34C759")
    except: st.info("No meal logs.")
    st.markdown('</div>', unsafe_allow_html=True)

st.subheader("📝 Recent Logs")
try:
    log_data = conn.read(worksheet="Log")
    if not log_data.empty:
        st.dataframe(log_data.tail(5), use_container_width=True, hide_index=True)
except: pass
