import os
import uuid
import time
import streamlit as st
from dotenv import load_dotenv
from chatbot_backend import chatbot, retrieve_all_threads
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage




load_dotenv(override=True)

print("LANGSMITH_ENDPOINT:", os.getenv("LANGSMITH_ENDPOINT"))
print("LANGSMITH_PROJECT:", os.getenv("LANGSMITH_PROJECT"))
print("LANGSMITH_API_KEY starts with:", os.getenv("LANGSMITH_API_KEY")[:6])

#********************************utility function**********************************

def generate_thread_id():
    return str(uuid.uuid4())

def reset_chat():
    st.session_state['message_history'] = []
    st.session_state['thread_id'] = generate_thread_id()
    add_thread(st.session_state['thread_id'])

def add_thread(thread_id):
    if thread_id not in st.session_state['chat_thread']:
        st.session_state['chat_thread'].append(thread_id)

def load_conversation(thread_id):
    state = chatbot.get_state(
        config={'configurable': {'thread_id': thread_id}}
    )
    return state.values.get("messages", [])

#*********************************Session state************************************ 
message_history = []
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_thread' not in st.session_state:
    st.session_state['chat_thread'] = retrieve_all_threads()

add_thread(st.session_state['thread_id'])

#**********************************Display chat history*****************************

for message in st.session_state['message_history']:
    with st.chat_message(message["role"]):
        st.write(message["content"])



#*******************************Sidebar configuration******************************

st.sidebar.title("Chatbot using LangGraph")

if st.sidebar.button("New Chat"):
    reset_chat()
    st.rerun()

st.sidebar.header("My Conversation History")

for thread_id in st.session_state['chat_thread'][::-1]:
    if st.sidebar.button(str(thread_id)):
        st.session_state['thread_id'] = thread_id
        messages = load_conversation(thread_id)

        temp_message = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "user"
            else:
                role = "assistant"
            temp_message.append({"role": role, "content": msg.content})

        st.session_state['message_history'] = temp_message
        st.rerun()


#**************************************Main UI*************************************
user_input = st.chat_input("Type here: ")

if user_input:
    # Append user message to history
    st.session_state['message_history'].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
    # Append assistant response to history
    
    #st.session_state['message_history'].append({"role": "assistant", "content": ai_message})
    with st.chat_message("assistant"):
        # status_placeholder = st.empty()
        # status_placeholder.markdown("🧠 **Thinking...**")
        # time.sleep(0.5)
        # status_placeholder.markdown("🔍 **Analyzing your question...**")
        # time.sleep(0.5)
        # status_placeholder.markdown("✍️ **Generating response...**")
        
        # CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}

        CONFIG = {
            "configurable": {"thread_id": st.session_state["thread_id"]},
            "metadata": {
                "thread_id": st.session_state["thread_id"]
            },
            "run_name": "chat_turn",
        }


        ai_message = st.write_stream(
            message_chunk.content for message_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]}, config=CONFIG,
                stream_mode="messages"
            )
        )
        #status_placeholder.empty()

    st.session_state['message_history'].append({"role": "assistant", "content": ai_message})