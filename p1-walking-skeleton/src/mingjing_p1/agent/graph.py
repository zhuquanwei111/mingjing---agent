"""One interrupted approval node, one deterministic route, one tool Activity."""

from typing import TypedDict

from langgraph.errors import NodeError
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from temporalio import workflow
from temporalio.exceptions import is_cancelled_exception

with workflow.unsafe.imports_passed_through():
    from mingjing_p1.agent.fake_model import propose


class AgentState(TypedDict, total=False):
    job: dict
    denial: str
    result: dict


async def approval(state: AgentState) -> dict:
    interrupt({"decision_id": state["job"]["decision_id"]})
    return {}


async def decide(state: AgentState) -> dict:
    job = state["job"]
    proposal = propose(job["scenario"])
    if proposal.tool != "record":
        return {"denial": "agent_tool_denied"}
    if proposal.steps > job["step_limit"]:
        return {"denial": "agent_step_limit"}
    if proposal.depth > job["depth_limit"]:
        return {"denial": "agent_depth_limit"}
    if workflow.time() >= job["deadline_epoch"]:
        return {"denial": "agent_deadline"}
    return {}


async def route(state: AgentState) -> str:
    return END if state.get("denial") else "tool"


async def recover(state: AgentState, error: NodeError) -> dict:
    if is_cancelled_exception(error.error):
        raise error.error
    return {"denial": "agent_activity_failed"}


def build_graph(tool):
    graph = StateGraph(AgentState)
    graph.set_node_defaults(error_handler=recover)
    graph.add_node("approval", approval, metadata={"execute_in": "activity"})
    graph.add_node("decide", decide, metadata={"execute_in": "workflow"})
    graph.add_node("tool", tool, metadata={"execute_in": "activity"})
    graph.add_edge(START, "approval")
    graph.add_edge("approval", "decide")
    graph.add_conditional_edges("decide", route, [END, "tool"])
    graph.add_edge("tool", END)
    return graph
