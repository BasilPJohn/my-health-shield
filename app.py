import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- 1. SLATE GREY & HIGH-VISUAL COLOR PALETTE ---
st.set_page_config(page_title="Shield OS v9", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    /* Background: Deep Slate Grey */
    .stApp { background-color: #1c1c1e; color: #ffffff; }
    
    /* Sidebar: Darker Charcoal */
    [data-testid="stSidebar"] { background-color: #121212; border-right: 1px solid #3a3a3c; }
    
    /* Content Cards: Medium Slate */
    .apple-card {
        background-color: #2c2c2e;
        border-radius: 20px;
        padding: 30px;
        border: 1px solid #3a3a3c;
        margin-bottom: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    
    /* Buttons: Primary Blue */
    .stButton > button {
        width: 100%; border-radius: 12px; background-color: #3a3a3c;
        color: #ffffff; border: 1px solid #48484a; padding: 14px;
        font-weight: 700; font-size: 16px; transition: 0.3s;
    }
    .stButton > button:hover { background-color: #007aff; border-color: #007aff; color: white; }
    
    /* Text Clarity */
    h1, h2, h3 { color: #ffffff !important; font-weight: 800 !important; letter-spacing: -0.5px; }
    p, label, .stMarkdown { color: #ffffff !important; font-size: 15px; }
    .stMetric { background-color: #2c2c2e; border-radius: 15px; border: 1px solid #3a3a3c; }
    </style>
""", unsafe_allow_html=True)

st_autorefresh(interval=5000, key="global_sync")

# --- 2. HARDENED DATA ENGINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        log = conn.read(worksheet="Log", ttl=0)
        prof = conn.read(worksheet="Profile", ttl=0)
        weight = conn.read(worksheet="WeightLog", ttl=0)
        # Standardize headers to lowercase to fix the 'KeyError' permanently
        for df in [log, prof, weight]:
            df.columns = [str(c).strip().lower() for c in df.columns]
        return log, prof, weight
    except:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 3. PERSISTENT NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "Dashboard"
if "logged_in" not in st.session_state: st.session_state.logged_in = False

log_df, profiles_df, weight_df = load_data()

# --- 4. AUTHENTICATION GATE ---
if not st.session_state.logged_in:
    cols = st.columns([1, 1.5, 1])
    with cols[1]:
        st.markdown("<h1 style='text-align: center; margin-top: 50px;'>🛡️ Shield OS</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            e_input = st.text_input("Neural ID (Email)").strip().lower()
            p_input = st.text_input("Access Key", type="password")
            if st.button("Unlock System"):
                if not profiles_df.empty and 'email' in profiles_df.columns:
                    user = profiles_df[(profiles_df['email'] == e_input) & (profiles_df['password'] == p_input)]
                    if not user.empty:
                        st.session_state.logged_in = True
                        st.session_state.user_email = e_input
                        st.rerun()
                    else: st.error("Verification Failed.")
                else: st.error("Database connection error.")
    st.stop()

# --- 5. LOGGED-IN OPERATIONS ---
u_p = profiles_df[profiles_df['email'] == st.session_state.user_email].iloc[0].to_dict()

with st.sidebar:
    st.markdown("<h2 style='color: #007aff !important;'>SHIELD OS</h2>", unsafe_allow_html=True)
    st.write(f"Identity: **{u_p.get('name', 'Operator')}**")
    st.divider()
    if st.button("📊 Dashboard"): st.session_state.page = "Dashboard"
    if st.button("🧠 Shield Brain"): st.session_state.page = "Brain"
    st.divider()
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- 6. PAGE: DASHBOARD ---
if st.session_state.page == "Dashboard":
    st.title("System Status")
    
    # Apple-Style Activity Rings
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.subheader("Nutrient Adherence")
    today_log = log_df[pd.to_datetime(log_df['date']).dt.date == datetime.now().date()]
    
    m_cols = st.columns(3)
    # Configuration: [Name, Key, PrimaryColor, TrackColor]
    rings = [
        ('Protein', 'goal_protein', '#ff2d55', '#3d0f1a'), # Red
        ('Carbs', 'goal_carbs', '#007aff', '#0a1d33'),    # Blue
        ('Fat', 'goal_fat', '#ffcc00', '#332b00')        # Yellow
    ]

    for i, (name, key, color, bg) in enumerate(rings):
        act = today_log[name.lower()].sum() if not today_log.empty else 0
        tar = u_p.get(key, 100)
        pct = min(act/tar, 1.0) if tar > 0 else 0
        
        fig = go.Figure(go.Pie(values=[pct, 1-pct], hole=0.82, marker=dict(colors=[color, bg]), textinfo='none', sort=False))
        fig.update_layout(showlegend=False, height=250, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)',
                          annotations=[dict(text=f"<b style='color:white; font-size:26px;'>{int(act)}g</b><br><span style='color:#a1a1a6; font-size:14px;'>{name}</span>", 
                                            x=0.5, y=0.5, showarrow=False)])
        m_cols[i].plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Weight Visualization
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.subheader("Weight Path Tracking")
    if not weight_df.empty:
        weight_df['date'] = pd.to_datetime(weight_df['date'])
        fig_w = go.Figure()
        # High-Vis Glowing Green Line
        fig_w.add_trace(go.Scatter(x=weight_df['date'], y=weight_df['weight'], line=dict(color='#30d158', width=5), name="Actual"))
        fig_w.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color="#ffffff", size=14),
                            xaxis=dict(showgrid=False, zeroline=False),
                            yaxis=dict(showgrid=True, gridcolor="#3a3a3c", zeroline=False))
        st.plotly_chart(fig_w, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
