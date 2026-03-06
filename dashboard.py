"""
dashboard.py — Clara AI Pipeline Minimal Dashboard
Run: streamlit run dashboard.py
"""

import json
from pathlib import Path
import streamlit as st

OUTPUTS_DIR = Path("outputs/accounts")

st.set_page_config(page_title="Clara AI — Account Dashboard", page_icon="🤖", layout="wide")
st.sidebar.title("🤖 Clara AI Pipeline")
st.sidebar.caption("Minimal Account Viewer")

if not OUTPUTS_DIR.exists():
    st.error("No pipeline outputs found. Run `python scripts/run_pipeline.py` first.")
    st.stop()

account_dirs = sorted([d for d in OUTPUTS_DIR.iterdir() if d.is_dir()])
if not account_dirs:
    st.warning("No accounts yet.")
    st.stop()

def _load_json(path: Path) -> dict | None:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None

def _account_label(acc_dir: Path) -> str:
    memo = _load_json(acc_dir / "v1" / "memo.json")
    company = memo.get("company_name") if memo else None
    return f"{company or acc_dir.name} ({acc_dir.name})"

account_options = {_account_label(d): d for d in account_dirs}
selected_label  = st.sidebar.selectbox("Select Account", list(account_options.keys()))
selected_dir    = account_options[selected_label]

st.sidebar.markdown("---")
st.sidebar.code("python scripts/run_pipeline.py\npython run_api.py")

memo_v1  = _load_json(selected_dir / "v1" / "memo.json")
memo_v2  = _load_json(selected_dir / "v2" / "memo.json")
agent_v1 = _load_json(selected_dir / "v1" / "agent_spec.json")
agent_v2 = _load_json(selected_dir / "v2" / "agent_spec.json")

company = (memo_v2 or memo_v1 or {}).get("company_name", selected_dir.name)
st.title(f"🏢 {company}")

tabs = st.tabs(["📄 Memo v1", "📄 Memo v2", "🤖 Agent Spec v1", "🤖 Agent Spec v2"])

with tabs[0]:
    st.subheader("Account Memo — v1")
    if memo_v1: st.json(memo_v1)
    else: st.warning("v1 memo not found.")

with tabs[1]:
    st.subheader("Account Memo — v2")
    if memo_v2: st.json(memo_v2)
    else: st.info("v2 memo not available yet.")

with tabs[2]:
    st.subheader("Retell Agent Spec - v1")
    if agent_v1: st.json(agent_v1)
    else: st.warning("v1 agent spec not found.")

with tabs[3]:
    st.subheader("Retell Agent Spec - v2")
    if agent_v2: st.json(agent_v2)
    else: st.info("v2 agent spec not found.")
