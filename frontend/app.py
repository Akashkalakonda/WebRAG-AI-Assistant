import streamlit as st
import requests
import json

st.title("RAG based Chatbot🤖")
st.write("Ask about current affairs or other topics!")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

query = st.chat_input("Enter your question (e.g., Pahalgam current affairs):")
if query:
    with st.chat_message("user"):
        st.markdown(query)
    st.session_state.messages.append({"role": "user", "content": query})

    try:
        response = requests.post(
            "http://localhost:5001/query",
            json={"query": query}
        )
        response_data = response.json()
        answer = response_data.get("response", "Error: No response from server.")
    except Exception as e:
        answer = f"Error: Failed to connect to server ({str(e)})."

    with st.chat_message("assistant"):
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})