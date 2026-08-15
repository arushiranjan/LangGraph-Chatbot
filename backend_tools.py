from langgraph.graph import StateGraph, START, END
from langchain_mistralai import ChatMistralAI
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

# tools calling
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
import requests

load_dotenv() 

llm = ChatMistralAI(model="mistral-large-latest", temperature=0)

# Tools ------------------------------------------------------------
search_tool = DuckDuckGoSearchRun(region="us-en")

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

        return {
            "first_num": first_num,
            "second_num": second_num,
            "operation": operation,
            "result": result
        }

    except Exception as e:
            return {"error": str(e)}


@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA')
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=ALPHA_API_KEY"
    r = requests.get(url)
    return r.json()

tools = [search_tool, calculator, get_stock_price]
llm_with_tools = llm.bind_tools(tools)


# setup checkpointer ------------------------------------------------------------------------
conn = sqlite3.connect(database='chatbot.db', check_same_thread=False) # connection object
memory = SqliteSaver(conn=conn)


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    # extract prev msg
    msg = state['messages']
    # send to llm
    response = llm_with_tools.invoke(msg)
    # update state
    return {"messages": [response]}

tool_node = ToolNode(tools)

# Graph -----------------------------------------------------------------------------------
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, 'chat_node')
graph.add_conditional_edges('chat_node', tools_condition)
graph.add_edge('tools', 'chat_node')

chatbot = graph.compile(checkpointer=memory)


# for message_chunk, metadata in chatbot.stream(
#     {'messages':HumanMessage(content="Blog on Independence day")},
#     config={'configurable': {'thread_id': 'thread-2'}},
#     stream_mode="messages"
# ):
#     if message_chunk.content:
#         print(message_chunk.content, end=" ", flush=True)

# give checkpoints stored in the db/ or checkpoints in a particular thread
# gives generator object -> Checkkpoint Tuple(config={'configurable':.., 'thread_id':..,..}, ...)
# get all unique threads
def retrieve_all_threads():
    all_threads = set()
    for checkpt in memory.list(None):
        all_threads.add(checkpt.config['configurable']['thread_id']) # will have duplicate t_id's too so store in a set

    return list(all_threads)

