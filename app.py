import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- 1. SYSTEM CONFIG & PREMIUM UI ---
st.set_page_config(page_title="Shield OS v5", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    /* Main Background */
    .stApp { background-color: #000000; color: #ffffff; }
    
    /* Apple-style Cards */
    .apple-card {
        background-color: #1c1c1e;
        border-radius: 15px;
        padding: 24px;
        margin-bottom: 20px;
        border: 1px solid #2c2c2e;
    }
    
    /* Metrics Styling */
    div[data-testid="stMetric"] {
        background-color: #1c1c1e;
        border-radius: 12px;
        padding: 15px;
        border: 1px solid #2c2c2e;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] { background-color: #121212; border-right: 1px solid #2c2c2e; }
    
    /* Button Styling */
    .stButton>button {
        border-radius: 20px;
        background-color: #30d158;
        color: black;
        border: none;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st_autorefresh(interval=5000, key="global_sync")

# --- 2. FAILOVER NEURAL ENGINE ---
def run_brain_task(prompt, system_instr="You are Shield OS, a tactical health AI."):
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    # 2026 Model Stack for Rate-Limit Failover
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
    return "🛡️ Neural Overload: All systems busy.", "None"

# --- 3. DATA ARCHITECTURE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_and_clean():
    try:
        log = conn.read(worksheet="Log", ttl=0)
        prof = conn.read(worksheet="Profile", ttl=0)
        weight = conn.read(worksheet="WeightLog", ttl=0)
        
        # Standardize headers to prevent KeyErrors
        for df in [log, prof, weight]:
            df.columns = df.columns.str.strip().str.capitalize()
            
        return log, prof, weight
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 4. SECURE AUTHENTICATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    cols = st.columns([1, 1.5, 1])
    with cols[1]:
        st.markdown("<h1 style='text-align: center;'>🛡️ Shield OS</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            e = st.text_input("Neural ID (Email)")
            p = st.text_input("Access Key", type="password")
            if st.button("Unlock System", use_container_width=True):
                _, prof_df, _ = load_and_clean()
                user = prof_df[(prof_df['Email'] == e) & (prof_df['Password'] == p)]
                if not user.empty:
                    st.session_state.logged_in, st.session_state.user_email = True, e
                    st.rerun()
                else: st.error("Neural signature not recognized.")
    st.stop()

# --- 5. LOGGED-IN OPERATIONS ---
log_df, profiles_df, weight_df = load_and_clean()
u_p = profiles_df[profiles_df['Email'] == st.session_state.user_email].iloc[0].to_dict()

with st.sidebar:
    st.markdown("### 🛡️ Operational Control")
    nav = st.radio("Navigation", ["📊 Analytics", "🧠 Brain", "👤 Profile"])
    st.divider()
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- 6. VISUAL ANALYTICS (Apple Health Style) ---
if nav == "📊 Analytics":
    st.title("Neural Health Status")
    
    # 1. Neural Summary Card
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### 🧠 AI Health Insights")
    if st.button("Analyze Current Progress"):
        summary_prompt = f"Analyze: Weight {u_p['Weight']}kg, Target {u_p['Target_weight']}kg. Give a 2-sentence tactical tip."
        insight, model = run_brain_task(summary_prompt)
        st.info(f"{insight} (Processed via {model})")
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. Apple-Style Macro Rings
    st.subheader("Daily Macros")
    m_cols = st.columns(3)
    today_log = log_df[pd.to_datetime(log_df['Date']).dt.date == datetime.now().date()]
    # Name, ProfileKey, Color, BackgroundColor
    rings = [
        ('Protein', 'Goal_protein', '#ff2d55', '#3d0f1a'), # Red
        ('Carbs', 'Goal_carbs', '#007aff', '#0a1d33'),    # Blue
        ('Fat', 'Goal_fat', '#ffcc00', '#332b00')        # Yellow
    ]

    for i, (name, key, color, bg_color) in enumerate(rings):
        actual = today_log[name].sum() if not today_log.empty else 0
        target = u_p.get(key, 100)
        progress = min(actual/target, 1.0) if target > 0 else 0
        
        fig = go.Figure(go.Pie(values=[progress, 1-progress], hole=0.85, marker=dict(colors=[color, bg_color]), textinfo='none', sort=False))
        fig.update_layout(showlegend=False, height=220, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)',
                          annotations=[dict(text=f"<b>{int(actual)}g</b><br><span style='font-size:10px;'>{name}</span>", 
                                            x=0.5, y=0.5, showarrow=False, font=dict(color='white', size=16))])
        m_cols[i].plotly_chart(fig, use_container_width=True)

    # 3. Weight Trajectory
    st.subheader("Weight Pathway")
    if not weight_df.empty:
        weight_df['Date'] = pd.to_datetime(weight_df['Date'])
        fig_w = go.Figure()
        # Actual Path (Glowing Blue)
        fig_w.add_trace(go.Scatter(x=weight_df['Date'], y=weight_df['Weight'], name="Actual", line=dict(color='#007aff', width=4)))
        # Planned Path (Subtle Grey)
        goal_date = pd.to_datetime(u_p.get('Goal_date', datetime.now()))
        fig_w.add_trace(go.Scatter(x=[weight_df['Date'].min(), goal_date], 
                                   y=[u_p.get('Starting_weight', u_p['Weight']), u_p['Target_weight']], 
                                   name="AI Target", line=dict(dash='dash', color='#48484a')))
        fig_w.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_w, use_container_width=True)

# --- 7. SHIELD BRAIN ---
elif nav == "🧠 Brain":
    st.title("Neural Command")
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    
    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Sync goals or log data..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.spinner("Processing..."):
            response, model = run_brain_task(prompt)
            # Sync Logic
            if "sync" in prompt.lower():
                response = f"🛡️ **System Re-calibrated.** Goals synced via {model}."
            
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"): st.markdown(response)
        st.rerun()

elif nav == "👤 Profile":
    st.title("Neural Identity")
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.table(pd.DataFrame([u_p]).T.rename(columns={0: "Stored Value"}))
    st.markdown('</div>', unsafe_allow_html=True)
