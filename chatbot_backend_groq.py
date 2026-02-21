import os
import requests
import sqlite3
import operator
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from huggingface_hub import InferenceClient
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition
from typing import TypedDict, Optional, Annotated, Literal
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage

# Set the HuggingFace API token
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY")



# Initialize the HuggingFace model
llm = ChatGroq(model="llama-3.1-8b-instant")


@tool
def web_search(query: str) -> str:
    """
    Search the web for latest or real-time information using Google Serper.
    """
    os.environ["SERPER_API_KEY"] = "c5c2f08540810ce9b09732f511aef90c1d3c8369"

    try:
        search = GoogleSerperAPIWrapper()
        result = search.run(query)

        # IMPORTANT: return STRING
        # ToolNode will convert this into a ToolMessage
        return result

    except Exception as e:
        return f"Error during web search: {str(e)}"

@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num

        elif operation == "sub":
            result = first_num - second_num

        elif operation == "mul":
            result = first_num * second_num

        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num

        else:
            return {"error": f"Unsupported operation '{operation}'"}

        return {"result": result}

    except Exception as e:
        return {"error": str(e)}




@tool
def get_stock_price(symbol: str) -> dict:
    """
    Get the latest stock price for a given stock symbol using Alpha Vantage.
    Example symbols: AAPL, TSLA, MSFT, GOOGL
    """
    API_KEY = "GFHDFHBHXA3FQOGJ"

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "Global Quote" not in data or not data["Global Quote"]:
            return {"error": f"No data found for symbol '{symbol}'"}

        quote = data["Global Quote"]

        return {
            "symbol": quote.get("01. symbol"),
            "price": float(quote.get("05. price")),
            "change": float(quote.get("09. change")),
            "change_percent": quote.get("10. change percent")
        }

    except Exception as e:
        return {"error": str(e)}


tools = [web_search, calculator, get_stock_price]

llm_with_tools = llm.bind_tools(tools)


# Define the chat state
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]   


# Define the chat node function
def chat_node(state: ChatState):
    """LLM node they may answer or request a tool calls"""
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)

    return{"messages":[response]}

tool_node = ToolNode(tools)

#Database

conn = sqlite3.connect(database="chatbot2.db", check_same_thread=False)

# Set up the state graph and checkpointer
checkpointer = SqliteSaver(conn=conn)



graph = StateGraph(ChatState)

graph.add_node("Chat_node",chat_node)
graph.add_node("tools",tool_node)

graph.add_edge(START, "Chat_node")
graph.add_conditional_edges("Chat_node",tools_condition)
graph.add_edge("tools","Chat_node")

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

