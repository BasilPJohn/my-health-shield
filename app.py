import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- 1. UI ARCHITECTURE (Slate Grey Aesthetic) ---
st.set_page_config(page_title="Shield OS v18", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #1c1c1e; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #121212; border-right: 1px solid #3a3a3c; }
    .apple-card { background-color: #2c2c2e; border-radius: 20px; padding: 25px; border: 1px solid #3a3a3c; margin-bottom: 20px; }
    .stButton > button { width: 100%; border-radius: 12px; background-color: #2c2c2e; color: white; border: 1px solid #3a3a3c; padding: 14px; font-weight: 700; }
    .stButton > button:hover { background-color: #007aff; border-color: #007aff; }
    h1, h2, h3, label { color: #ffffff !important; }
    [data-testid="stChatMessage"] { background-color: #2c2c2e; border-radius: 15px; border: 1px solid #3a3a3c; }
    </style>
""", unsafe_allow_html=True)

# UI Heartbeat (Refresh visuals every 15s)
st_autorefresh(interval=15000, key="ui_refresh")

# --- 2. DATA ENGINE (Cached to prevent 429 Sheets Errors) ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def get_shield_data_cached():
    try:
        log = conn.read(worksheet="Log", ttl=0)
        prof = conn.read(worksheet="Profile", ttl=0)
        weight = conn.read(worksheet="WeightLog", ttl=0)
        for df in [log, prof, weight]:
            df.columns = [str(c).strip().lower() for c in df.columns]
        return log, prof, weight, "Success"
    except Exception as e:
        return None, None, None, str(e)

# --- 3. 2026 NEURAL FAILOVER ENGINE ---
def run_brain_task(prompt, user_context):
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return "❌ API Key Missing.", "None"
    
    client = genai.Client(api_key=api_key)
    
    # 2026 Model Failover Sequence
    models = ["gemini-3-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
    
    for model_id in models:
        try:
            resp = client.models.generate_content(
                model=model_id,
                contents=f"Context: {user_context}\nUser: {prompt}"
            )
            return resp.text, model_id
        except Exception as e:
            # If rate limited (429), try the next model in the list
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                continue 
            return f"🛡️ Neural Core Error: `{str(e)}`", "Error"
            
    return "🛡️ All Neural Links Saturated. Please wait 30 seconds for quota reset.", "None"

# --- 4. SESSION & AUTH ---
if "page" not in st.session_state: st.session_state.page = "Dashboard"
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "chat_history" not in st.session_state: st.session_state.chat_history = []

log_df, prof_df, weight_df, status_msg = get_shield_data_cached()

if not st.session_state.logged_in:
    if log_df is None:
        st.error(f"Sync Failure: {status_msg}")
        st.stop()
    cols = st.columns([1, 1.5, 1])
    with cols[1]:
        st.title("🛡️ Shield OS")
        with st.container(border=True):
            e_in = st.text_input("Neural ID").strip().lower()
            p_in = st.text_input("Key", type="password")
            if st.button("Unlock"):
                user = prof_df[prof_df['email'] == e_in]
                if not user.empty and str(user.iloc[0]['password']) == p_in:
                    st.session_state.logged_in, st.session_state.user_email = True, e_in
                    st.rerun()
    st.stop()

u_p = prof_df[prof_df['email'] == st.session_state.user_email].iloc[0].to_dict()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color:#007aff;'>SHIELD OPS</h2>", unsafe_allow_html=True)
    if st.button("📊 Analytics"): st.session_state.page = "Dashboard"
    if st.button("🧠 Shield Brain"): st.session_state.page = "Brain"
    st.divider()
    if st.button("🔄 Sync Live Data"): 
        st.cache_data.clear()
        st.rerun()
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- 6. PAGE: DASHBOARD ---
if st.session_state.page == "Dashboard":
    st.title(f"Status: {u_p.get('name', 'Operator')}")
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.subheader("Nutrient Adherence")
    t_log = log_df[pd.to_datetime(log_df['date']).dt.date == datetime.now().date()]
    r_cols = st.columns(3)
    rings = [('Protein', 'goal_protein', '#ff2d55', '#3d0f1a'), 
             ('Carbs', 'goal_carbs', '#007aff', '#0a1d33'), 
             ('Fat', 'goal_fat', '#ffcc00', '#332b00')]
    for i, (name, key, color, bg) in enumerate(rings):
        act = t_log[name.lower()].sum() if not t_log.empty else 0
        tar = u_p.get(key, 100)
        pct = min(act/tar, 1.0) if tar > 0 else 0
        fig = go.Figure(go.Pie(values=[pct, 1-pct], hole=0.82, marker=dict(colors=[color, bg]), textinfo='none', sort=False))
        fig.update_layout(showlegend=False, height=220, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)',
                          annotations=[dict(text=f"<b style='color:white; font-size:24px;'>{int(act)}g</b>", x=0.5, y=0.5, showarrow=False)])
        r_cols[i].plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- 7. PAGE: BRAIN (Model Failover Active) ---
elif st.session_state.page == "Brain":
    st.title("Neural Core")
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Input command..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.spinner("Cycling Neural Models..."):
            context = f"User: {u_p['name']}, Weight: {u_p['weight']}kg."
            ai_msg, model_used = run_brain_task(prompt, context)
            
        st.session_state.chat_history.append({"role": "assistant", "content": f"{ai_msg}\n\n*Relay: {model_used}*"})
        st.rerun()
