import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import json
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- 1. 10X SYSTEM INITIALIZATION ---
st.set_page_config(page_title="Health Shield OS", page_icon="🛡️", layout="wide")

# High-Frequency Auto-Refresh: Triggers every 5000ms (5 seconds)
# This ensures rings and tables update without manual refresh
st_autorefresh(interval=5000, key="shield_refresh")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": "🛡️ Shield Online. 5s Auto-sync active. Failover redundancy enabled."}]

# --- 2. CONNECTORS & FAILOVER BRAIN ---
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

def shield_brain_with_failover(user_input):
    """Primary: gemini-2.5-flash-lite | Secondary: Gemini 2.5 Flash"""
    models = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
    prompt = f"""
    Extract data from: "{user_input}"
    Return ONLY JSON. Intents:
    1. "meal": {{"intent": "meal", "food": "name", "calories": 0, "protein": 0, "carbs": 0, "fat": 0}}
    2. "weight": {{"intent": "weight", "value": 0.0}}
    3. "profile": {{"intent": "profile", "field": "Name/Weight/Height/Age/Target_Weight", "value": "val"}}
    """
    for model_name in models:
        try:
            resp = client.models.generate_content(
                model=model_name, contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(resp.text), model_name
        except: continue
    return None, None

# --- 3. LIVE DATA FETCH ---
try:
    log_df = conn.read(worksheet="Log", ttl=0) # ttl=0 forces fresh data
    p_df = conn.read(worksheet="Profile", ttl=0)
    w_df = conn.read(worksheet="WeightLog", ttl=0)
    p = p_df.iloc[0].to_dict()
except:
    log_df = pd.DataFrame(columns=["Date", "Meal", "Calories", "Protein", "Carbs", "Fat"])
    p = {"Weight": 75, "Target_Weight": 70, "Height": 175, "Age": 30}
    w_df = pd.DataFrame(columns=["Date", "Weight"])

# Dynamic Goals Logic
bmr = (10 * p['Weight']) + (6.25 * p['Height']) - (5 * p['Age']) + 5
cal_goal = int(bmr * 1.3)
today_cals = log_df[pd.to_datetime(log_df['Date']).dt.date == datetime.now().date()]['Calories'].sum() if not log_df.empty else 0

# --- 4. DASHBOARD UI ---
st.title("🛡️ Health Shield OS")
col_viz, col_chat = st.columns([1.5, 1])

with col_viz:
    st.markdown('<div style="background:white; p:20px; border-radius:20px; border:1px solid #eee">', unsafe_allow_html=True)
    # Calorie Progress Ring
    pct = min(today_cals/cal_goal, 1.0)
    fig = go.Figure(go.Pie(values=[pct, 1-pct], hole=0.8, marker=dict(colors=['#FF2D55', '#F2F2F7']), textinfo='none', sort=False))
    fig.update_layout(showlegend=False, height=350, margin=dict(t=0,b=0,l=0,r=0), 
                      annotations=[dict(text=f'<b>{today_cals}</b><br>KCAL', x=0.5, y=0.5, font_size=24, showarrow=False)])
    st.plotly_chart(fig, use_container_width=True)
    
    # Weight Tracker: Actual vs Planned
    st.markdown("### ⚖️ Weight Tracker: Actual vs Planned")
    weight_fig = go.Figure()
    weight_fig.add_trace(go.Scatter(x=w_df['Date'], y=w_df['Weight'], name="Actual", line=dict(color='#007AFF', width=4)))
    weight_fig.add_trace(go.Scatter(x=w_df['Date'], y=[p['Target_Weight']]*len(w_df), name="Target", line=dict(dash='dash', color='#86868B')))
    st.plotly_chart(weight_fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_chat:
    chat_container = st.container(height=450)
    for msg in st.session_state.chat_history:
        chat_container.chat_message(msg["role"]).write(msg["content"])

    u_input = st.chat_input("Update weight, log meal, or change profile...")
    if u_input:
        st.session_state.chat_history.append({"role": "user", "content": u_input})
        with st.spinner("Syncing..."):
            data, model = shield_brain_with_failover(u_input)
            if data:
                if data['intent'] == 'meal':
                    new_row = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d %H:%M"), "Meal": data['food'], "Calories": data['calories'], "Protein": data['protein'], "Carbs": data['carbs'], "Fat": data['fat']}])
                    conn.update(worksheet="Log", data=pd.concat([log_df, new_row], ignore_index=True))
                elif data['intent'] == 'weight':
                    new_w = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Weight": data['value']}])
                    conn.update(worksheet="WeightLog", data=pd.concat([w_df, new_w], ignore_index=True))
                elif data['intent'] == 'profile':
                    p_df.at[0, data['field']] = data['value']
                    conn.update(worksheet="Profile", data=p_df)
                st.session_state.chat_history.append({"role": "assistant", "content": f"✅ {data['intent'].capitalize()} sync complete via {model}."})
        st.rerun()

# --- 5. LIVE SYSTEM AUDIT ---
st.markdown("---")
st.markdown("### 📊 Live Audit Log")
st.dataframe(log_df.tail(5), use_container_width=True)
