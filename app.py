import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(page_title="Shield OS v4", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] { 
        background-color: #161b22; border-radius: 12px; 
        padding: 20px; border: 1px solid #30363d; 
    }
    .neural-card { 
        background-color: #1c2128; border-radius: 12px; 
        padding: 20px; border: 1px solid #388bfd; margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# 5-second automatic refresh for live tracking
st_autorefresh(interval=5000, key="global_sync")

# --- 2. MULTI-MODEL FAILOVER ENGINE ---
def run_brain_task(prompt, system_instr="You are Shield OS."):
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    # Cycle through models to handle rate limits
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
            continue 
    return "🛡️ Error: Neural pathways saturated.", "None"

# --- 3. DATA PERSISTENCE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        return conn.read(worksheet="Log", ttl=0), conn.read(worksheet="Profile", ttl=0), conn.read(worksheet="WeightLog", ttl=0)
    except:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 4. AUTHENTICATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.title("🛡️ Shield OS Access")
        with st.container(border=True):
            e = st.text_input("Neural ID (Email)")
            p = st.text_input("Access Key", type="password")
            if st.button("Initialize System", use_container_width=True):
                _, profiles_df, _ = load_data()
                user = profiles_df[(profiles_df['Email'] == e) & (profiles_df['Password'] == p)]
                if not user.empty:
                    st.session_state.logged_in = True
                    st.session_state.user_email = e
                    st.rerun()
                else: st.error("Invalid neural signature.")
    st.stop()

# Load active data context
log_df, profiles_df, weight_df = load_data()
u_p = profiles_df[profiles_df['Email'] == st.session_state.user_email].iloc[0].to_dict()

# --- 5. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("🛡️ Operations")
    nav = st.radio("Access Level", ["📊 Visual Analytics", "🧠 Shield Brain", "👤 Profile Info"])
    st.divider()
    if st.button("Exit System"):
        st.session_state.logged_in = False
        st.rerun()

# --- 6. TAB 1: ANALYTICS ---
if nav == "📊 Visual Analytics":
    st.title("Neural Health Monitoring")
    
    # Neural Summary Logic
    st.markdown('<div class="neural-card">', unsafe_allow_html=True)
    st.subheader("🧠 Neural Health Summary")
    if st.button("Generate Tactical Insight"):
        summary_prompt = f"Target: {u_p['Target_Weight']}kg. Latest Weight: {weight_df.tail(1).to_string()}. Give a 2-sentence summary."
        insight, model = run_brain_task(summary_prompt, "You are a concise Health Strategist.")
        st.write(f"{insight} (Analysis by {model})")
    st.markdown('</div>', unsafe_allow_html=True)

    # Macro Rings
    st.subheader("Daily Macros: Actual vs. Target")
    m_cols = st.columns(3)
    today_log = log_df[pd.to_datetime(log_df['Date']).dt.date == datetime.now().date()]
    macros = [('Protein', 'Goal_Protein', '#FF2D55'), ('Carbs', 'Goal_Carbs', '#007AFF'), ('Fat', 'Goal_Fat', '#FFCC00')]
    
    for i, (name, key, color) in enumerate(macros):
        act = today_log[name].sum() if not today_log.empty else 0
        tar = u_p.get(key, 100)
        pct = min(act/tar, 1.0) if tar > 0 else 0
        fig = go.Figure(go.Pie(values=[pct, 1-pct], hole=0.8, marker=dict(colors=[color, '#1c1c1e']), textinfo='none'))
        fig.update_layout(showlegend=False, height=180, margin=dict(t=0,b=0,l=0,r=0),
                          annotations=[dict(text=f"<b>{int(act)}g</b>", x=0.5, y=0.5, showarrow=False, font_size=18)])
        m_cols[i].plotly_chart(fig, use_container_width=True)

    # Weight Trajectory
    st.subheader("Weight Path: Actual vs. AI Planned")
    if not weight_df.empty:
        weight_df['Date'] = pd.to_datetime(weight_df['Date'])
        fig_w = go.Figure()
        fig_w.add_trace(go.Scatter(x=weight_df['Date'], y=weight_df['Weight'], name="Actual", line=dict(color='#007AFF', width=4)))
        goal_date = pd.to_datetime(u_p.get('Goal_Date', datetime.now()))
        fig_w.add_trace(go.Scatter(x=[weight_df['Date'].min(), goal_date], 
                                   y=[u_p.get('Starting_Weight', u_p['Weight']), u_p['Target_Weight']], 
                                   name="AI Planned Path", line=dict(dash='dash', color='#86868B')))
        st.plotly_chart(fig_w, use_container_width=True)

# --- 7. TAB 2: BRAIN ---
elif nav == "🧠 Shield Brain":
    st.title("Neural Interface")
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    
    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Sync goals or log progress..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.spinner("AI Processing..."):
            response, model = run_brain_task(prompt)
            # Add goal sync logic if "sync" is in prompt
            if "sync" in prompt.lower():
                cal_goal = int((10 * u_p['Weight'] + 6.25 * u_p['Height'] - 5 * u_p['Age']) * 1.3)
                profiles_df.loc[profiles_df['Email'] == u_p['Email'], ['Goal_Calories', 'Goal_Protein', 'Goal_Date']] = [cal_goal, int(cal_goal*0.3/4), (datetime.now()+timedelta(days=90)).date()]
                conn.update(worksheet="Profile", data=profiles_df)
                response += f" (Synced via {model})"
            
            st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()

elif nav == "👤 Profile Info":
    st.title("Neural Profile Data")
    st.dataframe(pd.DataFrame([u_p]).T, use_container_width=True)
