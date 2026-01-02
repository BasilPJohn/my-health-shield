import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import json
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go

# --- 1. SESSION STATE & UI THEME ---
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "meal_input" not in st.session_state:
    st.session_state.meal_input = None

st.set_page_config(page_title="Health Shield", page_icon="🛡️", layout="wide")

def apply_apple_theme():
    bg = "#FFFFFF" if not st.session_state.dark_mode else "#000000"
    card_bg = "#F2F2F7" if not st.session_state.dark_mode else "#1C1C1E"
    text_color = "#1D1D1F" if not st.session_state.dark_mode else "#F5F5F7"
    accent = "#007AFF" 
    st.markdown(f"""
        <style>
        @import url('https://fonts.cdnfonts.com/css/sf-pro-display-all');
        .stApp {{ background-color: {bg}; color: {text_color}; font-family: 'SF Pro Display', sans-serif; }}
        [data-testid="stSidebar"] {{ background-color: {card_bg} !important; border-right: 1px solid rgba(128,128,128,0.2); }}
        .apple-card {{
            background-color: {card_bg}; padding: 20px; border-radius: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom: 20px;
            border: 1px solid rgba(128,128,128,0.1);
        }}
        div.stButton > button {{
            background-color: {accent}; color: white; border-radius: 12px;
            padding: 0.6rem 1.5rem; font-weight: 600; width: 100%; border: none;
        }}
        </style>
    """, unsafe_allow_html=True)

apply_apple_theme()

# --- 2. CONNECTIONS ---
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. HELPER FUNCTIONS ---
def analyze_with_ai(user_text, meal_type):
    prompt = f"Dietitian Mode. Analyze {meal_type}. Return JSON ONLY: {{'food': str, 'calories': int, 'protein': int, 'carbs': int, 'fat': int, 'note': str}}"
    for model_id in ["gemini-2.0-flash", "gemini-1.5-flash"]:
        try:
            resp = client.models.generate_content(
                model=model_id, 
                contents=[prompt, user_text],
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
            )
            return json.loads(resp.text)
        except: continue
    return None

# --- 4. DATA LOADING & GOALS ---
try:
    profile_df = conn.read(worksheet="Profile")
    p = profile_df.iloc[0].to_dict()
except:
    p = {"Name": "User", "Weight": 70.0, "Height": 170.0, "Age": 25, "Target_Weight": 65.0}

bmr = (10 * p['Weight']) + (6.25 * p['Height']) - (5 * p['Age']) + 5
daily_target = int((bmr * 1.2) - (500 if p['Weight'] > p['Target_Weight'] else 0))

# Get Today's Total
try:
    log_df = conn.read(worksheet="Log")
    log_df['Date'] = pd.to_datetime(log_df['Date'])
    today_total = log_df[log_df['Date'].dt.date == datetime.now().date()]['Calories'].sum()
except:
    today_total = 0
    log_df = pd.DataFrame()

# --- 5. PROGRESS RING (TOP) ---
st.title("Health Shield")
c_top1, c_top2 = st.columns([1, 2])

with c_top1:
    progress_pct = min((today_total / daily_target) * 100, 100)
    ring_color = "#007AFF" if today_total <= daily_target else "#FF3B30"
    
    fig_ring = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = today_total,
        title = {'text': "Calories Today", 'font': {'size': 18}},
        number = {'suffix': f" / {daily_target}", 'font': {'size': 20}},
        gauge = {
            'axis': {'range': [None, daily_target], 'visible': False},
            'bar': {'color': ring_color},
            'bgcolor': "rgba(0,0,0,0.1)",
            'steps': [{'range': [0, daily_target], 'color': "rgba(0,0,0,0.05)"}],
        }
    ))
    fig_ring.update_layout(height=250, margin=dict(t=0, b=0, l=20, r=20))
    st.plotly_chart(fig_ring, use_container_width=True)

with c_top2:
    st.write(f"### Hello, {p['Name']}")
    remaining = daily_target - today_total
    status = "Remaining" if remaining >= 0 else "Over Target"
    st.metric(status, f"{abs(remaining)} kcal", delta=remaining, delta_color="inverse")
    
    # Quick Action Tabs
    m_type = st.selectbox("Meal Category", ["Breakfast", "Lunch", "Dinner", "Snack"])
    entry_mode = st.radio("Entry Type", ["✏️ Type", "🎙️ Voice"], horizontal=True)
    
    if entry_mode == "✏️ Type":
        txt = st.text_input("What did you eat?", key="txt_in")
        if txt: st.session_state.meal_input = txt
    else:
        audio = st.audio_input("Record meal")
        if audio: st.session_state.meal_input = "User recorded an audio description."

# --- 6. LOGGING BUTTONS ---
cb1, cb2 = st.columns(2)
with cb1:
    if st.button("🚀 Analyze & Log"):
        if st.session_state.meal_input:
            with st.spinner("AI analyzing..."):
                data = analyze_with_ai(st.session_state.meal_input, m_type)
                if data:
                    new_entry = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d %H:%M"), "Type": m_type, "Meal": data['food'], "Calories": data['calories'], "Protein": data['protein'], "Carbs": data['carbs'], "Fat": data['fat'], "Note": data['note']}])
                    conn.update(worksheet="Log", data=pd.concat([log_df, new_entry], ignore_index=True))
                    st.success(f"Logged {data['food']}")
                    time.sleep(1)
                    st.rerun()
with cb2:
    if st.button("📥 Log Offline"):
        if st.session_state.meal_input:
            q_entry = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d %H:%M"), "Meal_Type": m_type, "Raw_Input": st.session_state.meal_input}])
            try:
                old_q = conn.read(worksheet="Queue")
                conn.update(worksheet="Queue", data=pd.concat([old_q, q_entry], ignore_index=True))
            except:
                conn.update(worksheet="Queue", data=q_entry)
            st.info("Saved to Queue")

# --- 7. QUEUE SYNC ---
try:
    q_df = conn.read(worksheet="Queue")
    if not q_df.empty:
        with st.expander(f"⏳ Pending Sync ({len(q_df)})"):
            if st.button("🔄 Sync All"):
                for _, row in q_df.iterrows():
                    res = analyze_with_ai(row['Raw_Input'], row['Meal_Type'])
                    if res:
                        final_meal = pd.DataFrame([{"Date": row['Date'], "Type": row['Meal_Type'], "Meal": res['food'], "Calories": res['calories'], "Protein": res['protein'], "Carbs": res['carbs'], "Fat": res['fat'], "Note": res['note']}])
                        log_h = conn.read(worksheet="Log")
                        conn.update(worksheet="Log", data=pd.concat([log_h, final_meal], ignore_index=True))
                conn.update(worksheet="Queue", data=pd.DataFrame(columns=["Date", "Meal_Type", "Raw_Input"]))
                st.rerun()
except: pass

# --- 8. DASHBOARD ---
st.divider()
d1, d2 = st.columns(2)
with d1:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.subheader("Calorie Distribution")
    if not log_df.empty:
        dist = log_df.groupby('Type')['Calories'].mean().reset_index()
        st.plotly_chart(px.bar(dist, x='Type', y='Calories', color='Type', color_discrete_sequence=['#007AFF','#34C759','#FF9500','#FF3B30']).update_layout(height=250, margin=dict(t=0,b=0,l=0,r=0), showlegend=False), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with d2:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.subheader("Macro Mix (Last 10)")
    if not log_df.empty:
        r = log_df.tail(10)
        st.plotly_chart(px.pie(pd.DataFrame({'N':['P','C','F'], 'V':[r['Protein'].sum(), r['Carbs'].sum(), r['Fat'].sum()]}), values='V', names='N', hole=0.6, color_discrete_sequence=['#007AFF','#FF9500','#FF3B30']).update_layout(height=250, margin=dict(t=0,b=0,l=0,r=0), showlegend=False), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Sidebar for Profile updates
with st.sidebar:
    st.subheader("Profile Update")
    u_w = st.number_input("Current Weight", value=p['Weight'])
    if st.button("Update Weight"):
        new_p = pd.DataFrame([{"Name": p['Name'], "Age": p['Age'], "Height": p['Height'], "Weight": u_w, "Target_Weight": p['Target_Weight']}])
        conn.update(worksheet="Profile", data=new_p)
        st.rerun()
