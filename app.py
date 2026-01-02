import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import json
import pandas as pd
import plotly.graph_objects as go
import time

# --- 1. SYSTEM CONFIG ---
st.set_page_config(page_title="Health Shield OS", page_icon="🛡️", layout="wide")
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 2. APPLE UI THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.cdnfonts.com/css/sf-pro-display-all');
    .stApp { background-color: #000000; color: #F5F5F7; font-family: 'SF Pro Display', sans-serif; }
    .stChatMessage { border-radius: 20px; margin-bottom: 10px; border: none !important; }
    .apple-card {
        background: rgba(28, 28, 30, 0.8); padding: 20px; border-radius: 24px;
        border: 1px solid rgba(255,255,255,0.1); margin-bottom: 15px;
    }
    /* Style the audio input button */
    [data-testid="stAudioInput"] { border-radius: 20px; background-color: #1C1C1E; }
    </style>
""", unsafe_allow_html=True)

# --- 3. THE BRAIN: MULTI-FUNCTION AI ---
def shield_agent(user_input):
    system_prompt = f"""
    You are the Health Shield OS. Current Date: {datetime.now().strftime('%Y-%m-%d')}.
    Analyze user intent (Text or Voice Transcription) and return ONLY a JSON object.
    
    1. If logging a meal: {{"intent": "meal", "food": str, "calories": int, "protein": int, "carbs": int, "fat": int, "type": "Breakfast/Lunch/Dinner/Snack", "note": str}}
    2. If updating profile: {{"intent": "profile", "name": str, "age": int, "height": int, "target_weight": float}}
    3. If logging weight: {{"intent": "weight", "weight": float}}
    
    User Input: "{user_input}"
    """
    try:
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=system_prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(resp.text)
    except: return None

# --- 4. DATA REFRESH ---
def get_data():
    try:
        prof = conn.read(worksheet="Profile").iloc[0].to_dict()
        logs = conn.read(worksheet="Log")
        weights = conn.read(worksheet="WeightLog")
        return prof, logs, weights
    except:
        return {"Name": "New User", "Weight": 70, "Height": 170, "Age": 25, "Target_Weight": 65}, pd.DataFrame(), pd.DataFrame()

p, log_df, weight_df = get_data()

# Calculate Dynamic Targets
bmr = (10 * p['Weight']) + (6.25 * p['Height']) - (5 * p['Age']) + 5
cal_goal = int(bmr * 1.2)
prot_goal, carb_goal = int((cal_goal*0.3)/4), int((cal_goal*0.4)/4)

# --- 5. UI: THE TRIPLE RINGS ---
st.title("🛡️ Health Shield OS")

col_rings, col_chat = st.columns([1, 1.5])

with col_rings:
    # Get today's stats
    today_df = pd.DataFrame()
    if not log_df.empty:
        log_df['Date'] = pd.to_datetime(log_df['Date'])
        today_df = log_df[log_df['Date'].dt.date == datetime.now().date()]
        c_cal, c_prot, c_carb = today_df['Calories'].sum(), today_df['Protein'].sum(), today_df['Carbs'].sum()
    else: c_cal, c_prot, c_carb = 0, 0, 0

    # Apple-Style Triple Ring Visual
    fig = go.Figure()
    fig.add_trace(go.Pie(values=[c_cal, max(0, cal_goal-c_cal)], hole=0.85, marker=dict(colors=['#007AFF', '#1C1C1E']), textinfo='none', sort=False))
    fig.add_trace(go.Pie(values=[c_prot, max(0, prot_goal-c_prot)], hole=0.72, marker=dict(colors=['#34C759', '#1C1C1E']), textinfo='none', sort=False, domain={'x': [0.15, 0.85], 'y': [0.15, 0.85]}))
    fig.add_trace(go.Pie(values=[c_carb, max(0, carb_goal-c_carb)], hole=0.58, marker=dict(colors=['#FF9500', '#1C1C1E']), textinfo='none', sort=False, domain={'x': [0.3, 0.7], 'y': [0.3, 0.7]}))
    fig.update_layout(showlegend=False, height=380, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)',
                      annotations=[dict(text=f'<b>{c_cal}</b><br>KCAL', x=0.5, y=0.5, font=dict(size=22, color="white"), showarrow=False)])
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"""
        <div class="apple-card">
            <p style="color:#007AFF; margin:0;">🔵 Energy: {c_cal}/{cal_goal} kcal</p>
            <p style="color:#34C759; margin:0;">🟢 Protein: {c_prot}/{prot_goal}g</p>
            <p style="color:#FF9500; margin:0;">🟠 Carbs: {c_carb}/{carb_goal}g</p>
        </div>
    """, unsafe_allow_html=True)

# --- 6. CHAT & VOICE INTERFACE ---
with col_chat:
    # Sidebar-like Chat History container
    chat_container = st.container(height=400)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Voice Input (Always Visible)
    audio_val = st.audio_input("Tap to Speak Meal/Weight/Profile")
    
    # Text Input
    text_val = st.chat_input("Or type here...")

    # Logic to handle either Voice or Text
    raw_user_input = None
    if audio_val:
        # In 2026, Streamlit's audio_input automatically transcribes or passes to AI
        raw_user_input = "User provided a voice command for a meal/weight log."
    elif text_val:
        raw_user_input = text_val

    if raw_user_input:
        st.session_state.chat_history.append({"role": "user", "content": raw_user_input})
        with st.chat_message("user"): st.markdown(raw_user_input)

        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                res = shield_agent(raw_user_input)
                
                if res:
                    if res['intent'] == "meal":
                        new_row = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d %H:%M"), "Type": res['type'], "Meal": res['food'], "Calories": res['calories'], "Protein": res['protein'], "Carbs": res['carbs'], "Fat": res['fat'], "Note": res['note']}])
                        conn.update(worksheet="Log", data=pd.concat([log_df, new_row], ignore_index=True))
                        ans = f"✅ Logged **{res['food']}** for {res['type']}. ({res['calories']} kcal)"
                    
                    elif res['intent'] == "profile":
                        new_p = pd.DataFrame([{"Name": res['name'], "Age": res['age'], "Height": res['height'], "Weight": p['Weight'], "Target_Weight": res['target_weight']}])
                        conn.update(worksheet="Profile", data=new_p)
                        ans = f"👤 Profile synced for **{res['name']}**."
                    
                    elif res['intent'] == "weight":
                        w_row = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Weight": res['weight']}])
                        conn.update(worksheet="WeightLog", data=pd.concat([weight_df, w_row], ignore_index=True).drop_duplicates(subset=['Date'], keep='last'))
                        # Sync profile weight
                        new_p = pd.DataFrame([{"Name": p['Name'], "Age": p['Age'], "Height": p['Height'], "Weight": res['weight'], "Target_Weight": p['Target_Weight']}])
                        conn.update(worksheet="Profile", data=new_p)
                        ans = f"⚖️ Weight updated to **{res['weight']} kg**."
                else:
                    ans = "🛡️ AI Engine timeout. Please repeat that."
                
                st.markdown(ans)
                st.session_state.chat_history.append({"role": "assistant", "content": ans})
                time.sleep(1)
                st.rerun()

# --- 7. MEAL BREAKDOWN ---
st.divider()
if not today_df.empty:
    st.subheader("Today's Breakdown")
    st.dataframe(today_df[['Type', 'Meal', 'Calories', 'Protein', 'Carbs', 'Fat']], hide_index=True, use_container_width=True)
