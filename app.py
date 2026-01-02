import streamlit as st
from google import genai  # New 2026 Library
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import json
import pandas as pd
from PIL import Image

# 1. Setup - Page Config for iPhone
st.set_page_config(page_title="Health Shield", page_icon="🛡️", layout="centered")

# 2. Connections
# Ensure your Streamlit Secrets has: GEMINI_API_KEY and [connections.gsheets]
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Sidebar: User Profile & Medical Math
with st.sidebar:
    st.header("👤 Your Profile")
    weight = st.number_input("Weight (kg)", value=70.0)
    height = st.number_input("Height (cm)", value=170.0)
    age = st.number_input("Age", value=25)
    goal = st.selectbox("Goal", ["Weight Loss", "Maintain", "Muscle Gain"])
    
    # Mifflin-St Jeor Calculation
    bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    tdee = int(bmr * 1.2) # Baseline Activity
    st.metric("Daily Target", f"{tdee} kcal")

# 4. Input Tabs
st.title("🛡️ AI Health Shield")
tab1, tab2, tab3 = st.tabs(["📸 Photo", "🎤 Voice", "⌨️ Text"])

user_content = None

with tab1:
    cam_img = st.camera_input("Snap your meal")
    if cam_img:
        user_content = Image.open(cam_img)

with tab2:
    voice_data = st.audio_input("Describe your meal")
    if voice_data:
        # Note: In 2026 SDK, audio is handled via parts
        user_content = "The user provided a voice description of a meal."

with tab3:
    text_msg = st.text_input("Describe what you ate...")
    if text_msg:
        user_content = text_msg

# 5. Analysis Logic
if st.button("🚀 Analyze & Log Meal"):
    if user_content:
        with st.spinner("Gemini 3 is evaluating health risks..."):
            
            # Clinical Prompt
            prompt = f"""
            System: Act as a Clinical Dietitian. User: {weight}kg, Goal: {goal}, Limit: {tdee}kcal.
            Task: Analyze the input. Provide Calories, Protein(g), Carbs(g), Fat(g).
            Clinical Note: Mention additives, sodium risks, or goal alignment.
            IMPORTANT: Return ONLY valid JSON.
            JSON Format: {{"food": "name", "calories": 0, "protein": 0, "carbs": 0, "fat": 0, "note": "..."}}
            """
            
            try:
                # Using the stable Gemini 3 Flash model
                response = client.models.generate_content(
                    model="gemini-3-flash",
                    contents=[prompt, user_content],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                
                # Parse JSON
                res_data = json.loads(response.text)
                
                # Display results
                st.subheader(f"Meal: {res_data['food']}")
                col1, col2, col3 = st.columns(3)
                col1.metric("Calories", f"{res_data['calories']} kcal")
                col2.metric("Protein", f"{res_data['protein']}g")
                col3.metric("Goal Status", "Aligned" if res_data['calories'] < (tdee/3) else "High")
                
                st.warning(f"⚕️ Clinical Note: {res_data['note']}")
                
                # Save to Google Sheets
                new_row = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Meal": res_data['food'],
                    "Calories": res_data['calories'],
                    "Protein": res_data['protein'],
                    "Note": res_data['note']
                }])
                
                existing = conn.read(worksheet="Log")
                updated = pd.concat([existing, new_row], ignore_index=True)
                conn.update(worksheet="Log", data=updated)
                st.success("Successfully logged to Sheets!")

            except Exception as e:
                st.error(f"Analysis failed. Ensure your API Key is valid. Error: {e}")
    else:
        st.info("Please provide a photo, voice, or text input first.")

# 6. Trends
st.divider()
st.subheader("📈 Your Calorie Trend")
try:
    history = conn.read(worksheet="Log")
    if not history.empty:
        st.line_chart(history.set_index("Date")["Calories"])
except:
    st.write("Log your first meal to see trends!")
