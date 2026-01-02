import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Shield OS v4", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric, .neural-card { 
        background-color: #161b22; border-radius: 12px; 
        padding: 20px; border: 1px solid #30363d; margin-bottom: 10px;
    }
    .summary-text { color: #8b949e; font-size: 14px; line-height: 1.6; }
    .status-badge { background-color: #238636; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
    </style>
""", unsafe_allow_html=True)

st_autorefresh(interval=5000, key="global_sync")

# --- 2. MULTI-MODEL BRAIN ENGINE ---
def run_brain_task(prompt, system_instr="You are Shield OS."):
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    # 2026 Failover Stack
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
    return "🛡️ Error: All neural pathways saturated.", "None"

# --- 3. DATA PERSISTENCE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(worksheet="Log", ttl=0), conn.read(worksheet="Profile", ttl=0), conn.read(worksheet="WeightLog", ttl=0)

# --- 4. AUTH & CORE LOGIC ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    # ... [Login UI from previous code]
    st.stop()

log_df, profiles_df, weight_df = load_data()
u_p = profiles_df[profiles_df['Email'] == st.session_state.user_email].iloc[0].to_dict()

# --- 5. NEURAL HEALTH SUMMARY GENERATOR ---
def get_neural_summary():
    recent_weight = weight_df.tail(3).to_string()
    recent_meals = log_df.tail(5).to_string()
    prompt = f"Analyze this data: Target: {u_p['Target_Weight']}kg. Recent Weight: {recent_weight}. Recent Meals: {recent_meals}. Give a 2-sentence tactical health summary."
    summary, model = run_brain_task(prompt, "You are a concise Health Strategist.")
    return summary

# --- 6. DASHBOARD UI ---
with st.sidebar:
    st.title("🛡️ Operations")
    nav = st.radio("Access Level", ["📊 Visual Analytics", "🧠 Shield Brain"])

if nav == "📊 Visual Analytics":
    st.title("Neural Health Monitoring")

    # NEW: NEURAL SUMMARY CARD
    with st.container():
        st.markdown('<div class="neural-card">', unsafe_allow_html=True)
        st.markdown(f"**NEURAL STATUS** <span class='status-badge'>AI Active</span>", unsafe_allow_html=True)
        if st.button("Generate Fresh Insight"):
            summary = get_neural_summary()
            st.markdown(f"<p class='summary-text'>{summary}</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # MACRO RINGS
    m_cols = st.columns(3)
    today_log = log_df[pd.to_datetime(log_df['Date']).dt.date == datetime.now().date()]
    macros = [('Protein', 'Goal_Protein', '#FF2D55'), ('Carbs', 'Goal_Carbs', '#007AFF'), ('Fat', 'Goal_Fat', '#FFCC00')]
    
    for i, (name, key, color) in enumerate(macros):
        act = today_log[name].sum() if not today_log.empty else 0
        target = u_p.get(key, 100)
        pct = min(act/target, 1.0) if target > 0 else 0
        fig = go.Figure(go.Pie(values=[pct, 1-pct], hole=0.8, marker=dict(colors=[color, '#1c1c1e']), textinfo='none'))
        fig.update_layout(showlegend=False, height=180, margin=dict(t=0,b=0,l=0,r=0),
                          annotations=[dict(text=f"<b>{int(act)}g</b>", x=0.5, y=0.5, showarrow=False, font_size=18)])
        m_cols[i].plotly_chart(fig, use_container_width=True)

    # WEIGHT PATHWAY
    if not weight_df.empty:
        weight_df['Date'] = pd.to_datetime(weight_df['Date'])
        fig_w = go.Figure()
        fig_w.add_trace(go.Scatter(x=weight_df['Date'], y=weight_df['Weight'], name="Actual", line=dict(color='#007AFF', width=4)))
        fig_w.add_trace(go.Scatter(x=[weight_df['Date'].min(), pd.to_datetime(u_p['Goal_Date'])], 
                                   y=[u_p['Starting_Weight'], u_p['Target_Weight']], 
                                   name="AI Path", line=dict(dash='dash', color='#86868B')))
        st.plotly_chart(fig_w, use_container_width=True)
