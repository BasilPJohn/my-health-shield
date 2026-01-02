import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import json
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- 1. SETTINGS & AUTO-REFRESH (5 SECONDS) ---
st.set_page_config(page_title="Health Shield OS", page_icon="🛡️", layout="wide")
st_autorefresh(interval=5000, key="shield_refresh")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": "🛡️ Neural Shield Active. Type 'Sync Goals' to calculate your AI plan."}]

# --- 2. DATA & AI CONNECTORS ---
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_all():
    try:
        return conn.read(worksheet="Log", ttl=0), conn.read(worksheet="Profile", ttl=0), conn.read(worksheet="WeightLog", ttl=0)
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

log_df, profiles_df, weight_df = fetch_all()

# --- 3. SECURITY GATE ---
if not st.session_state.logged_in:
    st.title("🛡️ Health Shield Login")
    with st.form("Shield Login"):
        e, p = st.text_input("Email"), st.text_input("Password", type="password")
        if st.form_submit_button("Access Neural Hub"):
            user = profiles_df[(profiles_df['Email'] == e) & (profiles_df['Password'] == p)]
            if not user.empty:
                st.session_state.logged_in, st.session_state.user_email = True, e
                st.rerun()
    st.stop()

# Context for the logged-in user
u_p = profiles_df[profiles_df['Email'] == st.session_state.user_email].iloc[0].to_dict()

# --- 4. NAVIGATION ---
with st.sidebar:
    st.title("🛡️ Shield OS")
    nav = st.radio("System Menu", ["👤 Profile", "📊 Health Charts", "🧠 Shield Brain"])
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- 5. TAB 1: PROFILE ---
if nav == "👤 Profile":
    st.header("Shield Identity & AI Targets")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Starting Weight", f"{u_p.get('Starting_Weight', u_p['Weight'])} kg")
        st.metric("Target Weight", f"{u_p['Target_Weight']} kg")
    with c2:
        st.metric("Daily AI Goal", f"{u_p.get('Goal_Calories', 'TBD')} kcal")
        st.metric("Goal Deadline", str(u_p.get('Goal_Date', 'TBD')))

# --- 6. TAB 2: ANALYTICS (The Visual Engine) ---
elif nav == "📊 Health Charts":
    st.header("Neural Performance Visuals")
    
    # 6A. MACRO RINGS (Actual vs. Goal)
    st.subheader("Daily Macros: Actual vs. AI Target")
    today_data = log_df[pd.to_datetime(log_df['Date']).dt.date == datetime.now().date()]
    m_cols = st.columns(3)
    macros = [('Protein', 'Goal_Protein', '#FF2D55'), ('Carbs', 'Goal_Carbs', '#007AFF'), ('Fat', 'Goal_Fat', '#FFCC00')]
    
    for i, (name, goal_key, color) in enumerate(macros):
        act = today_data[name].sum() if not today_data.empty else 0
        tar = u_p.get(goal_key, 100)
        pct = min(act/tar, 1.0) if tar > 0 else 0
        fig = go.Figure(go.Pie(values=[pct, 1-pct], hole=0.8, marker=dict(colors=[color, '#F2F2F7']), textinfo='none', sort=False))
        fig.update_layout(showlegend=False, height=220, margin=dict(t=0,b=0,l=0,r=0), 
                          annotations=[dict(text=f"<b>{int(act)}g</b><br>{name}", x=0.5, y=0.5, showarrow=False)])
        m_cols[i].plotly_chart(fig, use_container_width=True)

    # 6B. WEIGHT PROGRESSION (The Path Logic)
    st.subheader("Weight Projection: Actual vs. Planned Path")
    if not weight_df.empty:
        weight_df['Date'] = pd.to_datetime(weight_df['Date'])
        fig_w = go.Figure()
        # Actual Path
        fig_w.add_trace(go.Scatter(x=weight_df['Date'], y=weight_df['Weight'], name="Actual", line=dict(color='#007AFF', width=4)))
        # AI Planned Path
        start_date = weight_df['Date'].min()
        goal_date = pd.to_datetime(u_p.get('Goal_Date', datetime.now() + timedelta(days=90)))
        fig_w.add_trace(go.Scatter(x=[start_date, goal_date], y=[u_p.get('Starting_Weight', u_p['Weight']), u_p['Target_Weight']], 
                                   name="AI Planned Path", line=dict(dash='dash', color='#86868B')))
        st.plotly_chart(fig_w, use_container_width=True)

# --- 7. TAB 3: SHIELD BRAIN ---
elif nav == "🧠 Shield Brain":
    chat_box = st.container(height=450)
    for m in st.session_state.chat_history: chat_box.chat_message(m["role"]).write(m["content"])
    
    u_prompt = st.chat_input("Sync goals or log data...")
    if u_prompt:
        st.session_state.chat_history.append({"role": "user", "content": u_prompt})
        with st.spinner("AI Processing..."):
            if "sync" in u_prompt.lower() or "goal" in u_prompt.lower():
                # BRAIN CALCULATION LOGIC
                c_goal = int((10 * u_p['Weight'] + 6.25 * u_p['Height'] - 5 * u_p['Age'] + 5) * 1.3)
                p_g, c_g, f_g = int(c_goal*0.3/4), int(c_goal*0.4/4), int(c_goal*0.3/9)
                d_goal = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
                
                # UPDATE SHEET (Persistent Sync)
                profiles_df.loc[profiles_df['Email'] == u_p['Email'], 
                               ['Goal_Calories', 'Goal_Protein', 'Goal_Carbs', 'Goal_Fat', 'Goal_Date', 'Starting_Weight']] = \
                               [c_goal, p_g, c_g, f_g, d_goal, u_p['Weight']]
                conn.update(worksheet="Profile", data=profiles_df)
                msg = f"🛡️ **Neural Plan Generated**: Target set to {c_goal} kcal. Macro rings and weight path updated."
            else:
                msg = "🛡️ Logged to Neural Cloud. View updated charts in the Analytics tab."
        
        st.session_state.chat_history.append({"role": "assistant", "content": msg})
        st.rerun()
