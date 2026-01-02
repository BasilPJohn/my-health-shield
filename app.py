import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- 1. PREMIUM SLATE GREY & BUTTON STYLING ---
st.set_page_config(page_title="Shield OS v7", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    /* Slate Grey Theme */
    .stApp { background-color: #2c2c2e; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #1c1c1e; border-right: 1px solid #3a3a3c; }
    
    /* Custom Sidebar Nav Buttons */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        background-color: #3a3a3c;
        color: white;
        border: 1px solid #48484a;
        padding: 10px;
        margin-bottom: 5px;
        transition: 0.3s;
    }
    .stButton > button:hover { background-color: #007aff; border-color: #007aff; }
    
    /* Apple Cards */
    .apple-card {
        background-color: #3a3a3c;
        border-radius: 16px;
        padding: 24px;
        border: 1px solid #48484a;
        margin-bottom: 20px;
    }
    
    /* Label Visibility Fix */
    p, label, .stMarkdown { color: #ffffff !important; font-weight: 500; }
    </style>
""", unsafe_allow_html=True)

st_autorefresh(interval=5000, key="global_sync")

# --- 2. DATA ENGINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        log = conn.read(worksheet="Log", ttl=0)
        prof = conn.read(worksheet="Profile", ttl=0)
        weight = conn.read(worksheet="WeightLog", ttl=0)
        for df in [log, prof, weight]:
            df.columns = df.columns.str.strip().str.lower()
        return log, prof, weight
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 3. SESSION STATE NAVIGATION ---
if "page" not in st.session_state:
    st.session_state.page = "📊 Analytics"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# --- 4. AUTHENTICATION GATE ---
if not st.session_state.logged_in:
    cols = st.columns([1, 1.5, 1])
    with cols[1]:
        st.markdown("<h1 style='text-align: center; color: white;'>🛡️ Shield OS</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            e = st.text_input("Neural ID (Email)").lower()
            p = st.text_input("Access Key", type="password")
            if st.button("Unlock System", use_container_width=True):
                _, prof_df, _ = load_data()
                user = prof_df[(prof_df['email'] == e) & (prof_df['password'] == p)]
                if not user.empty:
                    st.session_state.logged_in, st.session_state.user_email = True, e
                    st.rerun()
    st.stop()

# --- 5. SIDEBAR BUTTON NAVIGATION ---
log_df, profiles_df, weight_df = load_data()
u_p = profiles_df[profiles_df['email'] == st.session_state.user_email].iloc[0].to_dict()

with st.sidebar:
    st.markdown("### 🛠️ Operations")
    if st.button("📊 Health Analytics"): st.session_state.page = "📊 Analytics"
    if st.button("🧠 Shield Brain"): st.session_state.page = "🧠 Brain"
    st.divider()
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- 6. PAGE: ANALYTICS ---
if st.session_state.page == "📊 Analytics":
    st.title("System Status: Active")
    
    # Macro Rings Section
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.subheader("Daily Adherence")
    today_log = log_df[pd.to_datetime(log_df['date']).dt.date == datetime.now().date()]
    
    m_cols = st.columns(3)
    # [Name, Key, Color, BgColor]
    rings = [
        ('Protein', 'goal_protein', '#ff2d55', '#4d0010'), 
        ('Carbs', 'goal_carbs', '#007aff', '#001a33'),    
        ('Fat', 'goal_fat', '#ffcc00', '#332b00')
    ]

    for i, (name, key, color, bg) in enumerate(rings):
        act = today_log[name.lower()].sum() if not today_log.empty else 0
        tar = u_p.get(key, 100)
        pct = min(act/tar, 1.0) if tar > 0 else 0
        
        fig = go.Figure(go.Pie(values=[pct, 1-pct], hole=0.82, marker=dict(colors=[color, bg]), textinfo='none', sort=False))
        fig.update_layout(showlegend=False, height=220, margin=dict(t=10,b=10,l=10,r=10), paper_bgcolor='rgba(0,0,0,0)',
                          annotations=[dict(text=f"<b style='color:white; font-size:22px;'>{int(act)}g</b><br><span style='color:#a1a1a6;'>{name}</span>", 
                                            x=0.5, y=0.5, showarrow=False)])
        m_cols[i].plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Weight Line Chart
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.subheader("Weight Path")
    if not weight_df.empty:
        weight_df['date'] = pd.to_datetime(weight_df['date'])
        fig_w = go.Figure()
        fig_w.add_trace(go.Scatter(x=weight_df['date'], y=weight_df['weight'], line=dict(color='#30d158', width=4), name="Actual"))
        fig_w.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color="white", size=14), xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#48484a"))
        st.plotly_chart(fig_w, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- 7. PAGE: BRAIN ---
elif st.session_state.page == "🧠 Brain":
    st.title("Neural Core")
    # (Brain logic as before...)
    st.info("Brain interface active. Use the chat below to sync biometric data.")
