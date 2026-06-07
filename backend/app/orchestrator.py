import os
import re
from typing import Dict, Any, TypedDict, List
from backend.app.schema import ChatMessage
from backend.app.sql_agent import run_sql_agent
from backend.app.tax_advisor import get_tax_advisory

# Define the State for LangGraph
class AgentState(TypedDict):
    user_id: str
    message: str
    history: List[ChatMessage]
    next_node: str
    response: str
    agent_used: str
    sql_query: str
    data: List[dict]

def route_query_procedural(message: str) -> str:
    """
    Standard procedural router matching keyword patterns.
    Determines if the query goes to SQL Agent, Tax Advisor, or Assistant.
    """
    msg_lower = message.lower()
    
    # 1. SQL Agent matches (spending history, average spend, math calculations, lists of transactions)
    sql_keywords = [
        "average", "avg", "spend", "spending", "spent", "total", "cost", "sum", 
        "calculate", "how much", "transactions", "list my", "show my", "history", "breakdown"
    ]
    
    # 2. Tax Advisor matches (deductions, 80c, 80d, tax, tax saving, freelancer, presumptive)
    tax_keywords = [
        "tax", "deduction", "deductible", "save tax", "advisory", "sections", 
        "80c", "80d", "44ada", "44ad", "80gg", "80tta", "freelancer tax", "income tax"
    ]
    
    # Check tax first (specific advisory request)
    if any(k in msg_lower for k in tax_keywords):
        return "tax_advisor"
        
    # Check SQL agent (spending statistics and transaction logs)
    if any(k in msg_lower for k in sql_keywords):
        return "sql_agent"
        
    # Default to assistant
    return "assistant"

def run_orchestrator(user_id: str, message: str, history: List[ChatMessage]) -> Dict[str, Any]:
    """
    Orchestrates routing between SQL Agent, Tax Advisor, and General Assistant.
    Uses LangGraph if available, falling back to a robust rule-based router if needed.
    """
    # 1. Route the query
    destination = route_query_procedural(message)
    
    openai_key = os.environ.get("OPENAI_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    # 2. Execute selected agent node
    if destination == "sql_agent":
        res = run_sql_agent(message, user_id)
        return {
            "response": res["response"],
            "agent_used": "sql_agent",
            "sql_query": res.get("sql_query"),
            "data": res.get("data")
        }
        
    elif destination == "tax_advisor":
        res = get_tax_advisory(user_id)
        if "error" in res:
            return {
                "response": f"Sorry, I couldn't compute tax advice: {res['error']}",
                "agent_used": "tax_advisor"
            }
        return {
            "response": res["summary"],
            "agent_used": "tax_advisor",
            "sql_query": None,
            "data": [dict(r) for r in res.get("recommendations", [])]
        }
        
    else:
        # Destination is assistant: generate a conversational response
        system_prompt = "You are an autonomous financial agent. You help users manage their money, upload statements, track spending, and lower their taxes."
        
        response_text = ""
        if openai_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                msgs = [{"role": "system", "content": system_prompt}]
                for h in history:
                    msgs.append({"role": h.role, "content": h.content})
                msgs.append({"role": "user", "content": message})
                
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=msgs
                )
                response_text = resp.choices[0].message.content
            except Exception as e:
                response_text = f"Conversational model error: {str(e)}"
                
        elif gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                resp = model.generate_content(message)
                response_text = resp.text
            except Exception as e:
                response_text = f"Gemini conversational model error: {str(e)}"
                
        # Default simple offline response if no LLM config is found
        if not response_text:
            response_text = (
                "Hi there! I am your local Autonomous Financial Agent. "
                "You can upload your bank statements as PDFs, and I'll parse them securely. "
                "You can ask me questions like 'What is my average monthly spend on utilities?' or 'How can I save taxes?' "
                "and I'll query your financial database to help you!"
            )
            
        return {
            "response": response_text,
            "agent_used": "assistant",
            "sql_query": None,
            "data": None
        }

# Try to define LangGraph Workflow if import succeeds
try:
    from langgraph.graph import StateGraph, END
    
    def router_node(state: AgentState) -> AgentState:
        state["next_node"] = route_query_procedural(state["message"])
        return state
        
    def sql_agent_node(state: AgentState) -> AgentState:
        res = run_sql_agent(state["message"], state["user_id"])
        state["response"] = res["response"]
        state["agent_used"] = "sql_agent"
        state["sql_query"] = res.get("sql_query")
        state["data"] = res.get("data")
        return state
        
    def tax_advisor_node(state: AgentState) -> AgentState:
        res = get_tax_advisory(state["user_id"])
        state["response"] = res.get("summary", "No recommendations found.")
        state["agent_used"] = "tax_advisor"
        state["data"] = res.get("recommendations", [])
        return state
        
    def assistant_node(state: AgentState) -> AgentState:
        res = run_orchestrator(state["user_id"], state["message"], state["history"])
        state["response"] = res["response"]
        state["agent_used"] = "assistant"
        return state

    workflow = StateGraph(AgentState)
    workflow.add_node("router", router_node)
    workflow.add_node("sql_agent", sql_agent_node)
    workflow.add_node("tax_advisor", tax_advisor_node)
    workflow.add_node("assistant", assistant_node)
    
    workflow.set_entry_point("router")
    
    # Route dynamically from router node
    workflow.add_conditional_edges(
        "router",
        lambda state: state["next_node"],
        {
            "sql_agent": "sql_agent",
            "tax_advisor": "tax_advisor",
            "assistant": "assistant"
        }
    )
    
    workflow.add_edge("sql_agent", END)
    workflow.add_edge("tax_advisor", END)
    workflow.add_edge("assistant", END)
    
    langgraph_app = workflow.compile()
except Exception as e:
    # LangGraph or components import failed/not installed yet. Procedural execution will be fallback.
    langgraph_app = None
