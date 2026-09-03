import streamlit as st
from agent import call_agent

st.set_page_config(page_title="AI Job Hunting Copilot")
st.title("🎯 AI Job Hunting Copilot")

if "history" not in st.session_state:
    st.session_state.history = []

user_id = st.sidebar.number_input("User ID", value=1)

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Npr: Nađi mi remote backend poslove bez 5+ god K8s iskustva"):
    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    reply = call_agent(prompt, user_id, st.session_state.history)

    st.session_state.history.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.write(reply)