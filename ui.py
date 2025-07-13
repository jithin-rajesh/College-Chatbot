import streamlit as st
import requests
import json

st.set_page_config(
    page_title="College Syllabus Chatbot",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 College Syllabus Chatbot")
st.caption("Ask any question about the B.Tech Computer Science (AI) syllabus.")

FLASK_API_URL = "http://127.0.0.1:5000/ask"
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_question := st.chat_input("What would you like to know about the syllabus?"):
    
    st.chat_message("user").markdown(user_question)
    st.session_state.messages.append({"role": "user", "content": user_question})

    try:
        with st.spinner("Thinking..."):
            payload = {"question": user_question}
            
            response = requests.post(FLASK_API_URL, json=payload)
            
            if response.status_code == 200:
                api_response = response.json()
                bot_answer = api_response.get("answer", "Sorry, I couldn't get a valid answer.")
            else:
                error_details = response.json().get('error', response.text)
                bot_answer = f"Error: Failed to get a response from the server. Status Code: {response.status_code}. Details: {error_details}"
    
    except requests.exceptions.RequestException as e:
        bot_answer = f"Error: Could not connect to the backend server at {FLASK_API_URL}. Please make sure it's running. Details: {e}"

    with st.chat_message("assistant"):
        st.markdown(bot_answer)
    st.session_state.messages.append({"role": "assistant", "content": bot_answer})