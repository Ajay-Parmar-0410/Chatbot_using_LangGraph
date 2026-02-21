import os
import sqlite3
import operator
from pydantic import BaseModel, Field
from huggingface_hub import InferenceClient
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import TypedDict, Optional, Annotated, Literal
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage

# Set the HuggingFace API token
HF_TOKEN = os.getenv("HF_TOKEN")# Initialize the HuggingFace model
llm = HuggingFaceEndpoint(
    repo_id="meta-llama/Meta-Llama-3-8B-Instruct",
    temperature=0.7,
    max_new_tokens=252
)
model = ChatHuggingFace(llm=llm)

# Define the chat state
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]   


# Define the chat node function
def chat_node(state: ChatState):
    messages = state["messages"]

    response = model.invoke(messages)

    return {"messages": [response]}

conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)

# Set up the state graph and checkpointer
checkpointer = SqliteSaver(conn=conn)
graph = StateGraph(ChatState)

graph.add_node("chat_node", chat_node)

graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

chatbot = graph.compile(checkpointer=checkpointer)

# CONFIG = {'configurable': {'thread_id': 'thread_id-2'}}
# response = chatbot.invoke(
#     {"messages": [HumanMessage(content="What is my name")]}, config=CONFIG)

# print(response)



def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])

    return list(all_threads)

