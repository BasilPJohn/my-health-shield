import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import time

# --- 1. SYSTEM CONFIG ---
st.set_page_config(page_title="Health Shield OS", page_icon="🛡️", layout="wide")
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 2. APPLE LIGHT THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.cdnfonts.com/css/sf-pro-display-all');
    .stApp { background-color: #FFFFFF; color: #1D1D1F; font-family: 'SF Pro Display', sans-serif; }
    .stChatMessage { border-radius: 20px; margin-bottom: 10px; background-color: #F5F5F7 !important; color: #1D1D1F !important; border: none !important; }
    .apple-card {
        background: #F2F2F7; padding: 20px; border-radius: 24px;
        border: 1px solid rgba(0,0,0,0.05); margin-bottom: 15px;
    }
    [data-testid="stMetricValue"] { color: #007AFF !important; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# --- 3. STABLE AI BRAIN ---
def shield_agent(user_input):
    system_prompt = f"""
    Act as Health Shield OS. Analyze input for: Meal Logging, Profile Updates, or Weight.
    Return ONLY a JSON object. No prose.
    Format:
    - Meal: {{"intent": "meal", "food": "name", "calories": 0, "protein": 0, "carbs": 0, "fat": 0, "type": "Breakfast/Lunch/Dinner/Snack", "note": "str"}}
    - Profile: {{"intent": "profile", "name": "str", "age": 0, "height": 0, "target_weight": 0.0}}
    - Weight: {{"intent": "weight", "weight": 0.0}}
    
    User Input: "{user_input}"
    """
    for model_name in ["gemini-2.0-flash", "gemini-1.5-flash"]:
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=system_prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
            )
            return json.loads(resp.text)
        except: continue
    return None

# --- 4. DATA LOADING ---
def get_data():
    try:
        prof = conn.read(worksheet="Profile").iloc[0].to_dict()
        logs = conn.read(worksheet="Log")
        w_history = conn.read(worksheet="WeightLog")
        w_history['Date'] = pd.to_datetime(w_history['Date'])
        return prof, logs, w_history
    except:
        return {"Name": "User", "Weight": 70, "Height": 170, "Age": 25, "Target_Weight": 65}, pd.DataFrame(), pd.DataFrame(columns=['Date', 'Weight'])

p, log_df, weight_df = get_data()

# Logic for Targets
bmr = (10 * p['Weight']) + (6.25 * p['Height']) - (5 * p['Age']) + 5
cal_goal = int(bmr * 1.2)
prot_goal, carb_goal = int((cal_goal*0.3)/4), int((cal_goal*0.4)/4)

# --- 5. UI: TOP DASHBOARD (RINGS & CHART) ---
st.title("🛡️ Health Shield OS")

col_left, col_right = st.columns([1, 1.5])

with col_left:
    # --- Activity Rings ---
    if not log_df.empty:
        log_df['Date'] = pd.to_datetime(log_df['Date'])
        today_df = log_df[log_df['Date'].dt.date == datetime.now().date()]
        c_cal, c_prot, c_carb = today_df['Calories'].sum(), today_df['Protein'].sum(), today_df['Carbs'].sum()
    else:
        c_cal, c_prot, c_carb = 0, 0, 0

    fig_ring = go.Figure()
    fig_ring.add_trace(go.Pie(values=[c_cal, max(0, cal_goal-c_cal)], hole=0.85, marker=dict(colors=['#007AFF', '#E5E5EA']), textinfo='none', sort=False))
    fig_ring.add_trace(go.Pie(values=[c_prot, max(0, prot_goal-c_prot)], hole=0.72, marker=dict(colors=['#34C759', '#E5E5EA']), textinfo='none', sort=False, domain={'x': [0.15, 0.85], 'y': [0.15, 0.85]}))
    fig_ring.add_trace(go.Pie(values=[c_carb, max(0, carb_goal-c_carb)], hole=0.58, marker=dict(colors=['#FF9500', '#E5E5EA']), textinfo='none', sort=False, domain={'x': [0.3, 0.7], 'y': [0.3, 0.7]}))
    fig_ring.update_layout(showlegend=False, height=350, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)',
                      annotations=[dict(text=f'<b>{c_cal}</b><br>KCAL', x=0.5, y=0.5, font=dict(size=20), showarrow=False)])
    st.plotly_chart(fig_ring, use_container_width=True)

    # --- Monthly Weight Chart ---
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.subheader("Monthly Weight Trend")
    if not weight_df.empty:
        # Filter last 30 days
        last_month = weight_df[weight_df['Date'] > (datetime.now() - timedelta(days=30))]
        fig_weight = px.line(last_month, x='Date', y='Weight', markers=True)
        fig_weight.update_traces(line_color='#007AFF', marker=dict(size=8, color='#007AFF'))
        fig_weight.update_layout(height=200, margin=dict(t=10,b=10,l=10,r=10), xaxis_title=None, yaxis_title=None, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_weight, use_container_width=True)
        
        diff = round(p['Weight'] - p['Target_Weight'], 1)
        st.metric("Away from Target", f"{diff} kg", delta=-diff if diff > 0 else abs(diff), delta_color="inverse")
    else:
        st.info("Log your weight to see trends.")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. VOICE & TEXT CHAT ---
with col_right:
    chat_container = st.container(height=500)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

    audio_val = st.audio_input("Voice Input")
    text_val = st.chat_input("Log meal, weight, or update profile...")

    raw_input = text_val if text_val else ("Voice Command" if audio_val else None)

    if raw_input:
        st.session_state.chat_history.append({"role": "user", "content": raw_input})
        with st.chat_message("user"): st.markdown(raw_input)

        with st.chat_message("assistant"):
            res = shield_agent(raw_input if text_val else "User logged a meal/weight via voice.")
            if res:
                if res['intent'] == "meal":
                    new_row = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d %H:%M"), "Type": res['type'], "Meal": res['food'], "Calories": res['calories'], "Protein": res['protein'], "Carbs": res['carbs'], "Fat": res['fat'], "Note": res['note']}])
                    conn.update(worksheet="Log", data=pd.concat([log_df, new_row], ignore_index=True))
                    ans = f"✅ Logged **{res['food']}** ({res['calories']} kcal)."
                elif res['intent'] == "weight":
                    w_row = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Weight": res['weight']}])
                    conn.update(worksheet="WeightLog", data=pd.concat([weight_df, w_row], ignore_index=True).drop_duplicates(subset=['Date'], keep='last'))
                    # Update profile weight
                    new_p = pd.DataFrame([{"Name": p['Name'], "Age": p['Age'], "Height": p['Height'], "Weight": res['weight'], "Target_Weight": p['Target_Weight']}])
                    conn.update(worksheet="Profile", data=new_p)
                    ans = f"⚖️ Weight recorded: **{res['weight']} kg**. Target updated."
                elif res['intent'] == "profile":
                    new_p = pd.DataFrame([{"Name": res['name'], "Age": res['age'], "Height": res['height'], "Weight": p['Weight'], "Target_Weight": res['target_weight']}])
                    conn.update(worksheet="Profile", data=new_p)
                    ans = f"👤 Profile for **{res['name']}** is now live."
            else:
                ans = "🛡️ Connectivity hiccup. Try again?"
            
            st.markdown(ans)
            st.session_state.chat_history.append({"role": "assistant", "content": ans})
            time.sleep(1); st.rerun()
