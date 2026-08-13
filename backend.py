from langgraph.graph import StateGraph, START, END
from langchain_mistralai import ChatMistralAI
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver # stores memory in RAM

load_dotenv()  
llm = ChatMistralAI()


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

chatbot = graph.compile(checkpointer=checkpointer)


