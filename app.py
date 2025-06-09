import streamlit as st
import requests
import pandas as pd
import json
from main import *
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.groq import Groq
from dotenv import load_dotenv
import os

# Set wide layout
st.set_page_config(page_title="Patient Management System", layout="wide")

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
# BASE_URL = "http://localhost:8000"
BASE_URL = "http://3.16.207.21:8000"

# Title
st.title("🩺 Patient Management System")

# Create 2-column layout
col1, col2 = st.columns([2, 2])  

# ----------------- LEFT COLUMN: PATIENT MANAGEMENT -----------------
with col1:

    # About Section
    st.header("ℹ️ About")
    try:
        response = requests.get(f"{BASE_URL}/about")
        if response.status_code == 200:
            st.info(response.json()["message"])
        else:
            st.error("Failed to fetch about page info.")
    except Exception as e:
        st.error(f"Error: {e}")

    # View Patients
    if st.button("📋 View Patients"):
        try:
            response = requests.get(f"{BASE_URL}/view")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    data = [{**v, "id": k} for k, v in data.items()]
                df = pd.DataFrame(data)
                st.dataframe(df)
            else:
                st.error("Failed to fetch patient data.")
        except Exception as e:
            st.error(f"Error: {e}")

    # Session state toggles
    if "show_create_form" not in st.session_state:
        st.session_state.show_create_form = False
    if "show_update_form" not in st.session_state:
        st.session_state.show_update_form = False
    if "show_delete_form" not in st.session_state:
        st.session_state.show_delete_form = False

    # Form Toggles
    st.subheader("🔧 Patient Operations")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("➕ Create Patient"):
            st.session_state.show_create_form = True
            st.session_state.show_update_form = False
            st.session_state.show_delete_form = False
    with c2:
        if st.button("✏️ Update Patient"):
            st.session_state.show_create_form = False
            st.session_state.show_update_form = True
            st.session_state.show_delete_form = False
    with c3:
        if st.button("🗑️ Delete Patient"):
            st.session_state.show_create_form = False
            st.session_state.show_update_form = False
            st.session_state.show_delete_form = True

    # Create Form
    if st.session_state.show_create_form:
        st.header("🆕 Create Patient")
        with st.form("create_patient_form"):
            patient_id = st.text_input("Patient ID", key="create_id")
            name = st.text_input("Name", key="create_name")
            city = st.text_input("City", key="create_city")
            age = st.number_input("Age", 1, 119, key="create_age")
            gender = st.selectbox("Gender", ["male", "female", "others"], key="create_gender")
            height = st.number_input("Height (m)", 0.01, step=0.01, format="%.2f", key="create_height")
            weight = st.number_input("Weight (kg)", 0.01, step=0.1, format="%.1f", key="create_weight")
            diagnosis = st.text_input("Diagnosis", key="create_diagnosis")
            submitted = st.form_submit_button("Create Patient")
            if submitted:
                try:
                    data = {
                        "id": patient_id,
                        "name": name,
                        "city": city,
                        "age": age,
                        "gender": gender,
                        "height": height,
                        "weight": weight,
                        "diagnosis": diagnosis
                    }
                    response = requests.post(f"{BASE_URL}/create", json=data)
                    if response.status_code == 201:
                        st.success("✅ Patient created successfully.")
                    else:
                        st.error(f"❌ Failed: {response.json().get('detail', 'Unknown error.')}")
                except Exception as e:
                    st.error(f"🚨 Error: {e}")

    # Update Form
    if st.session_state.show_update_form:
        st.header("🔁 Update Patient")
        with st.form("update_patient_form"):
            patient_id = st.text_input("Patient ID", key="update_id")
            name = st.text_input("Name", key="update_name")
            city = st.text_input("City", key="update_city")
            age = st.number_input("Age", 1, 119, key="update_age")
            gender = st.selectbox("Gender", ["male", "female", "others"], key="update_gender")
            height = st.number_input("Height (m)", 0.01, step=0.01, format="%.2f", key="update_height")
            weight = st.number_input("Weight (kg)", 0.01, step=0.1, format="%.1f", key="update_weight")
            diagnosis = st.text_input("Diagnosis", key="update_diagnosis")
            submitted = st.form_submit_button("Update Patient")
            if submitted:
                try:
                    data = {
                        "name": name,
                        "city": city,
                        "age": age,
                        "gender": gender,
                        "height": height,
                        "weight": weight,
                        "diagnosis": diagnosis
                    }
                    response = requests.put(f"{BASE_URL}/edit/{patient_id}", json=data)
                    if response.status_code == 200:
                        st.success("✅ Patient updated successfully.")
                    else:
                        st.error(f"❌ Failed: {response.json().get('detail', 'Unknown error.')}")
                except Exception as e:
                    st.error(f"🚨 Error: {e}")

    # Delete Form
    if st.session_state.show_delete_form:
        st.header("🗑️ Delete Patient")
        with st.form("delete_patient_form"):
            patient_id = st.text_input("Patient ID", key="delete_id")
            submitted = st.form_submit_button("Delete Patient")
            if submitted:
                try:
                    response = requests.delete(f"{BASE_URL}/delete/{patient_id}")
                    if response.status_code == 200:
                        st.success("✅ Patient deleted successfully.")
                    else:
                        st.error(f"❌ Failed: {response.json().get('detail', 'Unknown error.')}")
                except Exception as e:
                    st.error(f"🚨 Error: {e}")

# ----------------- RIGHT COLUMN: QUERY + MEDICAL NEWS -----------------
with col2:

    st.header("🔍 Ask About Patient Data")
    query = st.text_input("Enter query related to patient data", key="query")
    if query:
        def get_query_response(topic):
            try:
                data = load_data()
                response = requests.post(
                    f"{BASE_URL}/query/invoke",
                    json={"input": {"topic": topic, "file": json.dumps(data)}}
                )
                response.raise_for_status()
                return response.json()["output"]["content"]
            except Exception as e:
                return f"Error: {str(e)}"

        st.subheader("Response:")
        st.write(get_query_response(query))

    st.header("📰 Latest Medical News")
    web_search_agent = Agent(
        name='Medical websearch agent',
        role="search the web for latest medical news",
        model=Groq(id="gemma2-9b-it"),
        tools=[DuckDuckGoTools()],
        instructions=[
            "Use the DuckDuckGo to search the internet. Always include the source. "
            "Never say you don't have access to the internet. Just say something is not right."
        ],
        show_tool_calls=True,
        markdown=True
    )

    if st.button("🔍 Fetch Medical News"):
        with st.spinner("Fetching latest medical news..."):
            try:
                response = web_search_agent.run("Get the top 5 latest medical news worldwide", stream=False)
                st.markdown(response.content)
            except Exception as e:
                st.error(f"Error fetching medical news: {str(e)}")
