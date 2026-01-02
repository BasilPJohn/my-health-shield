import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- 1. SYSTEM CONFIG & STYLING ---
st.set_page_config(page_title="Shield OS v3", page_icon="🛡️", layout="wide")

# Custom UI Styling
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    [data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
    </style>
""", unsafe_allow_value=True)

# 5-second neural sync
st_autorefresh(interval=5000, key="global_sync")

# --- 2. FAILOVER INTELLIGENCE ---
def run_brain_task(prompt, system_instr):
    """Failover logic: 3 Flash -> 2.5 Flash -> 2.5 Flash-Lite"""
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    # Ordered by capability/rate-limit priority
    models = ["gemini-3-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
    
    for model_id in models:
        try:
            resp = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=system_instr)
            )
            return resp.text, model_id
        except Exception:
            continue # Try next model if rate limited or down
    return "🛡️ Error: All neural pathways saturated. Please try in 60s.", "None"

# --- 3. DATA PERSISTENCE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_all():
    try:
        return conn.read(worksheet="Log", ttl=0), conn.read(worksheet="Profile", ttl=0), conn.read(worksheet="WeightLog", ttl=0)
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 4. AUTHENTICATION FLOW ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.title("🛡️ Shield OS Login")
        with st.container(border=True):
            e = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.button("Initialize System", use_container_width=True):
                profiles_df = conn.read(worksheet="Profile", ttl=0)
                user = profiles_df[(profiles_df['Email'] == e) & (profiles_df['Password'] == p)]
                if not user.empty:
                    st.session_state.logged_in = True
                    st.session_state.user_email = e
                    st.rerun()
                else: st.error("Invalid neural signature (Login Failed).")
    st.stop()

# --- 5. LOGGED-IN HUB ---
log_df, profiles_df, weight_df = load_all()
u_p = profiles_df[profiles_df['Email'] == st.session_state.user_email].iloc[0].to_dict()

# Sidebar Navigation
with st.sidebar:
    st.title("🛡️ Operations")
    nav = st.radio("Access Level", ["📊 Visual Analytics", "🧠 Shield Brain", "👤 Profile Info"])
    st.divider()
    if st.button("Deactivate System"):
        st.session_state.logged_in = False
        st.rerun()

# --- 6. PAGE: ANALYTICS ---
if nav == "📊 Visual Analytics":
    st.title("Neural Health Monitoring")
    
    # ROW 1: MACRO RINGS
    st.subheader("Daily Intake vs. AI Targets")
    today_log = log_df[pd.to_datetime(log_df['Date']).dt.date == datetime.now().date()]
    m_cols = st.columns(3)
    # Target Data from Profile (Brains Logic)
    targets = [('Protein', 'Goal_Protein', '#FF2D55'), ('Carbs', 'Goal_Carbs', '#007AFF'), ('Fat', 'Goal_Fat', '#FFCC00')]
    
    for i, (name, key, color) in enumerate(targets):
        actual = today_log[name].sum() if not today_log.empty else 0
        goal = u_p.get(key, 100)
        progress = min(actual/goal, 1.0) if goal > 0 else 0
        
        fig = go.Figure(go.Pie(values=[progress, 1-progress], hole=0.8, marker=dict(colors=[color, '#1c1c1e']), textinfo='none'))
        fig.update_layout(showlegend=False, height=200, margin=dict(t=0,b=0,l=10,r=10),
                          annotations=[dict(text=f"<b>{int(actual)}g</b><br>{name}", x=0.5, y=0.5, showarrow=False, font_size=14)])
        m_cols[i].plotly_chart(fig, use_container_width=True)

    # ROW 2: WEIGHT PATHWAY
    st.subheader("Weight Trajectory: Actual vs. Planned")
    if not weight_df.empty:
        weight_df['Date'] = pd.to_datetime(weight_df['Date'])
        fig_w = go.Figure()
        # Actual Line
        fig_w.add_trace(go.Scatter(x=weight_df['Date'], y=weight_df['Weight'], name="Actual Weight", line=dict(color='#007AFF', width=4)))
        # Brain's Planned Path
        start_date = weight_df['Date'].min()
        goal_date = pd.to_datetime(u_p.get('Goal_Date', datetime.now()))
        fig_w.add_trace(go.Scatter(x=[start_date, goal_date], y=[u_p.get('Starting_Weight', u_p['Weight']), u_p['Target_Weight']], 
                                   name="AI Target Path", line=dict(dash='dash', color='#86868B')))
        st.plotly_chart(fig_w, use_container_width=True)

# --- 7. PAGE: BRAIN (FAILOVER ENABLED) ---
elif nav == "🧠 Shield Brain":
    st.title("Neural Interface")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Sync goals or log meal..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.spinner("AI Thinking..."):
            sys_instr = f"You are Shield OS. User: {u_p['Name']}, Weight: {u_p['Weight']}kg. Update targets if asked."
            response, used_model = run_brain_task(prompt, sys_instr)
            
            # Logic for updating Sheet if 'sync' or 'goal' mentioned
            if "sync" in prompt.lower():
                # Neural math for targets
                cal_goal = int((10 * u_p['Weight'] + 6.25 * u_p['Height'] - 5 * u_p['Age']) * 1.3)
                profiles_df.loc[profiles_df['Email'] == u_p['Email'], ['Goal_Calories', 'Goal_Protein', 'Goal_Date']] = [cal_goal, int(cal_goal*0.3/4), (datetime.now()+timedelta(days=90)).date()]
                conn.update(worksheet="Profile", data=profiles_df)
                response += f" (Processed by {used_model})"

            st.session_state.chat_history.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"): st.markdown(response)

elif nav == "👤 Profile Info":
    st.title("User Biometrics")
    st.table(pd.DataFrame([u_p]).T.rename(columns={0: "Neural Value"}))
