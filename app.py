import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
from datetime import datetime
import json
import pandas as pd

# 1. API & Sheet Connection
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Page Config for iPhone
st.set_page_config(page_title="Health Shield", page_icon="🛡️")

# 3. Sidebar Profile (Calculates your personal health limits)
with st.sidebar:
    st.header("👤 Your Profile")
    weight = st.number_input("Weight (kg)", value=70.0)
    height = st.number_input("Height (cm)", value=170.0)
    age = st.number_input("Age", value=25)
    goal = st.selectbox("Goal", ["Weight Loss", "Maintain", "Muscle Gain"])
    
    # Mifflin-St Jeor Formula
    bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    tdee = bmr * 1.2 # Sedentary multiplier
    st.info(f"Target: {int(tdee)} kcal/day")

# 4. Input Methods
st.title("🛡️ Health Shield")
tab1, tab2, tab3 = st.tabs(["📸 Photo", "🎤 Voice", "⌨️ Text"])

user_input = None
is_image = False

with tab1:
    img_file = st.camera_input("Take a photo of your meal")
    if img_file:
        user_input = img_file
        is_image = True
with tab2:
    audio_file = st.audio_input("Describe your meal")
    if audio_file:
        user_input = "The user provided a voice description of their meal."
with tab3:
    text_input = st.text_input("Type your meal (e.g. 2 eggs and toast)")
    if text_input:
        user_input = text_input

# 5. Analysis Engine
if st.button("Analyze & Log"):
    if user_input:
        with st.spinner("Clinical analysis in progress..."):
            model = genai.GenerativeModel('gemini-3-flash')
            
            prompt = f"""
            User Profile: {weight}kg, {goal} goal, {int(tdee)}kcal limit.
            Analyze this meal. Provide: Calories, Protein(g), Carbs(g), Fat(g).
            Provide a 'Clinical Note' regarding health/additives.
            Return ONLY JSON:
            {{"food": "name", "calories": 0, "protein": 0, "carbs": 0, "fat": 0, "note": "..."}}
            """
            
            if is_image:
                from PIL import Image
                img = Image.open(user_input)
                response = model.generate_content([prompt, img])
            else:
                response = model.generate_content(prompt + f"\nInput: {user_input}")
            
            try:
                data = json.loads(response.text.replace('```json', '').replace('```', ''))
                
                # Show results to user
                st.metric("Calories", f"{data['calories']} kcal")
                st.warning(f"⚕️ Clinical Note: {data['note']}")
                
                # Save to Google Sheets
                new_row = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Meal": data['food'],
                    "Calories": data['calories'],
                    "Protein": data['protein'],
                    "Carbs": data['carbs'],
                    "Fat": data['fat'],
                    "Clinical_Note": data['note']
                }])
                
                # Append to your Google Sheet
                existing_data = conn.read(worksheet="Log")
                updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                conn.update(worksheet="Log", data=updated_df)
                st.success("Meal logged successfully!")
                
            except Exception as e:
                st.error(f"Error parsing data: {e}")
    else:
        st.error("Please provide an input first!")

# 6. Trend Chart
st.divider()
st.subheader("📈 Daily Calorie Trend")
try:
    log_data = conn.read(worksheet="Log")
    if not log_data.empty:
        st.line_chart(log_data.set_index("Date")["Calories"])
except:
    st.info("Log some meals to see your trends!")
