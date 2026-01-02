import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- 1. UI ARCHITECTURE (Slate Grey & High Visibility) ---
st.set_page_config(page_title="Shield OS v12", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    /* Premium Slate Grey Background */
    .stApp { background-color: #1c1c1e; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #121212; border-right: 1px solid #3a3a3c; }
    
    /* Apple-Style Navigation Buttons */
    .stButton > button {
        width: 100%; border-radius: 12px; background-color: #2c2c2e;
        color: #ffffff; border: 1px solid #3a3a3c; padding: 14px;
        font-weight: 700; font-size: 16px; transition: 0.3s;
    }
    .stButton > button:hover { background-color: #007aff; border-color: #007aff; }
    
    /* Content Cards */
    .apple-card {
        background-color: #2c2c2e; border-radius: 20px; padding: 25px;
        border: 1px solid #3a3a3c; margin-bottom: 20px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.4);
    }
    
    /* Typography Fixes */
    h1, h2, h3, label { color: #ffffff !important; font-weight: 700 !important; }
    p, .stMarkdown { color: #f2f2f7 !important; }
    </style>
""", unsafe_allow_html=True)

# UI Refresh only (every 10 seconds to save quota)
st_autorefresh(interval=10000, key="ui_refresh")

# --- 2. QUOTA-SAFE DATA ENGINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)  # Caches data for 60 seconds to avoid 429 Errors
def get_shield_data_cached():
    try:
        log = conn.read(worksheet="Log", ttl=0)
        prof = conn.read(worksheet="Profile", ttl=0)
        weight = conn.read(worksheet="WeightLog", ttl=0)
        
        # Scrub Headers: Standardize to lowercase and remove spaces (Prevents KeyError)
        for df in [log, prof, weight]:
            df.columns = [str(c).strip().lower() for c in df.columns]
            
        return log, prof, weight
    except Exception as e:
        return None, None, None

# --- 3. FAILOVER NEURAL BRAIN ---
def run_brain_task(prompt):
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    models = ["gemini-2.0-flash", "gemini-1.5-flash"]
    for m in models:
        try:
            resp = client.models.generate_content(model=m, contents=prompt)
            return resp.text, m
        except: continue
    return "Neural links saturated.", "None"

# --- 4. SESSION & BOOT ---
if "page" not in st.session_state: st.session_state.page = "Dashboard"
if "logged_in" not in st.session_state: st.session_state.logged_in = False

log_df, prof_df, weight_df = get_shield_data_cached()

# Check for API block
if log_df is None:
    st.error("🛡️ Shield Offline: Google API Quota Exceeded. System cooling down... (Wait 60s)")
    st.stop()

# Check for Header Health
if 'email' not in prof_df.columns:
    st.error("DATABASE SCHEMA ERROR: 'email' column missing.")
    st.info(f"Detected Headers: {list(prof_df.columns)}")
    st.stop()

# --- 5. AUTHENTICATION GATE ---
if not st.session_state.logged_in:
    cols = st.columns([1, 1.5, 1])
    with cols[1]:
        st.markdown("<h1 style='text-align: center; margin-top:50px;'>🛡️ Shield OS</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            e_in = st.text_input("Neural ID (Email)").strip().lower()
            p_in = st.text_input("Access Key", type="password")
            if st.button("Unlock System"):
                user = prof_df[prof_df['email'] == e_in]
                if not user.empty and str(user.iloc[0]['password']) == p_in:
                    st.session_state.logged_in = True
                    st.session_state.user_email = e_in
                    st.rerun()
                else: st.error("Access Denied: Invalid Signature")
    st.stop()

# --- 6. COMMAND CENTER (Sidebar) ---
u_p = prof_df[prof_df['email'] == st.session_state.user_email].iloc[0].to_dict()

with st.sidebar:
    st.markdown("<h2 style='color:#007aff; margin-bottom:20px;'>SHIELD OPS</h2>", unsafe_allow_html=True)
    if st.button("📊 Health Analytics"): st.session_state.page = "Dashboard"
    if st.button("🧠 Shield Brain"): st.session_state.page = "Brain"
    st.divider()
    if st.button("🔄 Sync Live Data"): 
        st.cache_data.clear()
        st.rerun()
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- 7. PAGE: DASHBOARD ---
if st.session_state.page == "Dashboard":
    st.title(f"Operator: {u_p.get('name', 'User')}")
    
    # APPLE HEALTH RINGS
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
        fig.update_layout(showlegend=False, height=230, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)',
                          annotations=[dict(text=f"<b style='color:white; font-size:24px;'>{int(act)}g</b><br><span style='color:#a1a1a6;'>{name}</span>", 
                                            x=0.5, y=0.5, showarrow=False)])
        r_cols[i].plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # WEIGHT PATHWAY
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.subheader("Biometric Pathway")
    if not weight_df.empty:
        weight_df['date'] = pd.to_datetime(weight_df['date'])
        fig_w = go.Figure()
        fig_w.add_trace(go.Scatter(x=weight_df['date'], y=weight_df['weight'], line=dict(color='#30d158', width=5), name="Actual"))
        fig_w.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color="#ffffff"), xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#3a3a3c"))
        st.plotly_chart(fig_w, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- 8. PAGE: BRAIN ---
elif st.session_state.page == "Brain":
    st.title("Neural Interface")
    if prompt := st.chat_input("Log meal or weight update..."):
        with st.spinner("AI Thinking..."):
            res, m = run_brain_task(prompt)
            st.write(f"**Shield OS:** {res}")
            st.caption(f"Processed via {m}")
