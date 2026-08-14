from langgraph.graph import StateGraph, START, END
from langchain_mistralai import ChatMistralAI
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver # stores memory in RAM
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

load_dotenv()  
llm = ChatMistralAI()

# setup checkpointer 
conn = sqlite3.connect(database='chatbot.db', check_same_thread=False) # connection object
memory = SqliteSaver(conn=conn)


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    # extract prev msg
    msg = state['messages']
    # send to llm
    response = llm.invoke(msg)
    # update state
    return {"messages": [response]}

checkpointer = InMemorySaver()
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)

graph.add_edge(START, 'chat_node')
graph.add_edge('chat_node', END)

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

