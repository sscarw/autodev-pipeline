from typing import TypedDict
from review_agent import get_diff, run_review_agent
import coding_agent
import github_client
from models import Ticket, ReviewResult


class PipelineState(TypedDict):
    ticket: Ticket
    local_path: str
    branch_name: str
    diff: str
    review: ReviewResult | None
    attempts: int


async def code_node(state: PipelineState) -> dict:
    github_client.create_branch(state["local_path"], state["branch_name"])
    await coding_agent.run_coding_agent(state["ticket"], state["local_path"])
    github_client.commit_and_push(state["local_path"], state["branch_name"], state["ticket"].summary)
    return {}


async def review_node(state: PipelineState) -> dict:
    diff = get_diff(state["local_path"], state["branch_name"])
    review = await run_review_agent(diff)
    return {"diff": diff, "review": review, "attempts": state["attempts"] + 1}


def route_after_review(state: PipelineState) -> str:
    if state["review"].verdict == "approve":
        return "approved"

    if state["attempts"] < 3:
        return "revise"

    return "give_up"


from langgraph.graph import StateGraph, START, END

builder = StateGraph(PipelineState)
builder.add_node("code", code_node)
builder.add_node("review", review_node)
builder.add_edge(START, "code")
builder.add_edge("code", "review")
builder.add_conditional_edges(
    "review",
    route_after_review,
    {"approved": END, "revise": "code", "give_up": END},
)
graph = builder.compile()

if __name__ == "__main__":
    import asyncio

    initial_state = {
        "ticket": Ticket(key="AP-5", summary="Add PATCH endpoint to update todo title", description=None, status="To Do"),
        "local_path": "demo-folder",
        "branch_name": "feature/ap-5-test",
        "diff": "",
        "review": None,
        "attempts": 0,
    }

    result = asyncio.run(graph.ainvoke(initial_state))
    print(result)