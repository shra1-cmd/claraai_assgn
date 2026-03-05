from langgraph.graph import StateGraph, END
from typing import TypedDict
import os

from extract_memo import extract_memo
from generate_agent import generate_agent_spec
from apply_patch import apply_patch


class PipelineState(TypedDict):
    account_id: str
    demo_transcript: str
    onboarding_transcript: str


def extract_demo(state):

    account_id = state["account_id"]
    demo = state["demo_transcript"]

    memo_v1 = f"outputs/accounts/{account_id}/v1/memo.json"
    agent_v1 = f"outputs/accounts/{account_id}/v1/agent_spec.json"

    extract_memo(demo, memo_v1, account_id)
    generate_agent_spec(memo_v1, agent_v1)

    return state


def onboarding_update(state):

    account_id = state["account_id"]
    onboarding = state["onboarding_transcript"]

    memo_v1 = f"outputs/accounts/{account_id}/v1/memo.json"
    memo_v2 = f"outputs/accounts/{account_id}/v2/memo.json"
    agent_v2 = f"outputs/accounts/{account_id}/v2/agent_spec.json"

    apply_patch(memo_v1, onboarding, account_id)

    generate_agent_spec(memo_v2, agent_v2)

    return state


builder = StateGraph(PipelineState)

builder.add_node("demo_pipeline", extract_demo)
builder.add_node("onboarding_pipeline", onboarding_update)

builder.set_entry_point("demo_pipeline")

builder.add_edge("demo_pipeline", "onboarding_pipeline")
builder.add_edge("onboarding_pipeline", END)

graph = builder.compile()


def run_pipeline():

    transcripts_dir = "outputs/transcripts"

    demo_files = sorted([f for f in os.listdir(transcripts_dir) if f.startswith("demo")])
    onboard_files = sorted([f for f in os.listdir(transcripts_dir) if f.startswith("onboard")])

    for i, demo_file in enumerate(demo_files):

        account_id = f"acc{i+1}"

        state = {
            "account_id": account_id,
            "demo_transcript": f"{transcripts_dir}/{demo_file}",
            "onboarding_transcript": f"{transcripts_dir}/{onboard_files[i]}"
        }

        graph.invoke(state)


if __name__ == "__main__":
    run_pipeline()