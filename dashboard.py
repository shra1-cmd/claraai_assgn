"""
dashboard.py — Clara AI Pipeline Account Viewer
Run: streamlit run dashboard.py

Shows all processed accounts with their memos, agent specs, and v1 vs v2 diffs.
"""

import json
from pathlib import Path
import streamlit as st

OUTPUTS_DIR = Path("outputs/accounts")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Clara AI — Account Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.title("🤖 Clara AI Pipeline")
st.sidebar.caption("Account Viewer & Diff Dashboard")

if not OUTPUTS_DIR.exists():
    st.error("No pipeline outputs found. Run `python scripts/run_pipeline.py` first.")
    st.stop()

# Discover accounts
account_dirs = sorted([d for d in OUTPUTS_DIR.iterdir() if d.is_dir()])
if not account_dirs:
    st.warning("No accounts yet. Run the pipeline to generate outputs.")
    st.stop()


def _load_json(path: Path) -> dict | None:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def _account_label(acc_dir: Path) -> str:
    memo = _load_json(acc_dir / "v1" / "memo.json")
    company = memo.get("company_name") if memo else None
    return f"{company or acc_dir.name}  ({acc_dir.name})"


# Account selector
account_options = {_account_label(d): d for d in account_dirs}
selected_label  = st.sidebar.selectbox("Select Account", list(account_options.keys()))
selected_dir    = account_options[selected_label]

st.sidebar.markdown("---")
st.sidebar.markdown("**Run Pipeline**")
st.sidebar.code("python scripts/run_pipeline.py")
st.sidebar.markdown("**Start API (Swagger)**")
st.sidebar.code("python run_api.py")

# ── Main content ──────────────────────────────────────────────────────────────
memo_v1  = _load_json(selected_dir / "v1" / "memo.json")
memo_v2  = _load_json(selected_dir / "v2" / "memo.json")
agent_v1 = _load_json(selected_dir / "v1" / "agent_spec.json")
agent_v2 = _load_json(selected_dir / "v2" / "agent_spec.json")

company    = (memo_v2 or memo_v1 or {}).get("company_name", selected_dir.name)
account_id = selected_dir.name

st.title(f"🏢 {company}")
st.caption(f"`{account_id}` —  {'✅ v1 + v2 available' if memo_v2 else '⚠️ v1 only (run Pipeline B for v2)'}")

# ── Summary KPI row ───────────────────────────────────────────────────────────
memo = memo_v2 or memo_v1 or {}
hours  = memo.get("business_hours") or {}
hours_str = (
    f"{', '.join(hours.get('days',[]))}, {hours.get('start_time','')}–{hours.get('end_time','')} {hours.get('timezone','')}"
    if isinstance(hours, dict) else str(hours)
).strip()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Account ID",    account_id)
col2.metric("Business Hours", hours_str or "—")
col3.metric("Services",      len(memo.get("services_supported") or []))
col4.metric("Versions",      "v1 + v2" if memo_v2 else "v1 only")

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tabs = st.tabs(["📋 Overview", "📄 Memo v1", "📄 Memo v2", "🤖 Agent Spec", "🔍 v1 → v2 Diff"])

# ── Tab 1: Overview ───────────────────────────────────────────────────────────
with tabs[0]:
    st.subheader("Account Overview")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Company**")
        st.write(memo.get("company_name", "—"))

        st.markdown("**Address**")
        st.write(memo.get("office_address") or "—")

        st.markdown("**Business Hours**")
        st.write(hours_str or "—")

        st.markdown("**Services Supported**")
        services = memo.get("services_supported") or []
        if services:
            for s in services:
                st.write(f"  • {s}")
        else:
            st.write("—")

    with c2:
        st.markdown("**Emergency Definition**")
        emergencies = memo.get("emergency_definition") or []
        if emergencies:
            for e in emergencies:
                st.write(f"  🚨 {e}")
        else:
            st.write("—")

        st.markdown("**Emergency Routing**")
        st.write(memo.get("emergency_routing_rules") or "—")

        st.markdown("**After-Hours Flow**")
        st.write(memo.get("after_hours_flow_summary") or "—")

    if memo.get("questions_or_unknowns"):
        st.warning(
            "**Open Questions / Unknowns:**  \n" +
            "  \n".join(f"• {q}" for q in memo["questions_or_unknowns"])
        )

    if memo.get("notes"):
        with st.expander("📝 Notes"):
            st.write(memo["notes"])

# ── Tab 2: Memo v1 ────────────────────────────────────────────────────────────
with tabs[1]:
    st.subheader("Account Memo — v1 (Post Demo Call)")
    if memo_v1:
        st.json(memo_v1)
    else:
        st.warning("v1 memo not found. Run Pipeline A first.")

# ── Tab 3: Memo v2 ────────────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("Account Memo — v2 (Post Onboarding)")
    if memo_v2:
        st.json(memo_v2)
    else:
        st.info("v2 memo not available yet. Run Pipeline B to generate it.")

# ── Tab 4: Agent Spec ─────────────────────────────────────────────────────────
with tabs[3]:
    st.subheader("Retell Agent Spec")

    version_choice = st.radio("Version", ["v2", "v1"] if agent_v2 else ["v1"], horizontal=True)
    agent = agent_v2 if version_choice == "v2" else agent_v1

    if agent:
        col1, col2 = st.columns(2)
        col1.metric("Agent Name",  agent.get("agent_name", "—"))
        col2.metric("Voice Style", agent.get("voice_style", "—"))

        with st.expander("System Prompt", expanded=False):
            st.text(agent.get("system_prompt", "—"))

        with st.expander("Call Transfer Protocol"):
            st.json(agent.get("call_transfer_protocol", {}))

        with st.expander("Fallback Protocol"):
            st.json(agent.get("fallback_protocol", {}))

        with st.expander("Full Agent Spec JSON"):
            st.json(agent)
    else:
        st.warning("Agent spec not found for this version.")

# ── Tab 5: v1 → v2 Diff ───────────────────────────────────────────────────────
with tabs[4]:
    st.subheader("v1 → v2 Field Diff")

    if not memo_v1:
        st.warning("v1 memo not found.")
    elif not memo_v2:
        st.info("v2 memo not yet available. Run Pipeline B to generate it.")
    else:
        # Try deepdiff first, fallback to manual field comparison
        try:
            from deepdiff import DeepDiff
            diff = DeepDiff(memo_v1, memo_v2, ignore_order=True)

            if not diff:
                st.success("✅ No differences found between v1 and v2.")
            else:
                st.caption(f"Changes found in {len(diff)} category(ies)")

                if "values_changed" in diff:
                    st.markdown("#### 🔄 Changed Values")
                    for path, change in diff["values_changed"].items():
                        field = path.replace("root['", "").replace("']", "").replace("']['", " → ")
                        col1, col2, col3 = st.columns([2, 3, 3])
                        col1.markdown(f"**{field}**")
                        col2.markdown(f"~~{change['old_value']}~~")
                        col3.markdown(f"**{change['new_value']}**")

                if "dictionary_item_added" in diff:
                    st.markdown("#### ➕ New Fields")
                    for path in diff["dictionary_item_added"]:
                        field = path.replace("root['", "").replace("']", "")
                        st.success(f"Added: `{field}`")

                if "dictionary_item_removed" in diff:
                    st.markdown("#### ➖ Removed Fields")
                    for path in diff["dictionary_item_removed"]:
                        field = path.replace("root['", "").replace("']", "")
                        st.error(f"Removed: `{field}`")

                if "iterable_item_added" in diff:
                    st.markdown("#### ➕ New List Items")
                    for path, val in diff["iterable_item_added"].items():
                        field = path.replace("root['", "").replace("']", "")
                        st.success(f"`{field}` → {val}")

                with st.expander("Raw DeepDiff Output"):
                    st.json(diff.to_json())

        except ImportError:
            # Fallback: manual comparison
            st.info("deepdiff not installed — showing manual field comparison.")
            changed = {k: (memo_v1.get(k), memo_v2.get(k))
                       for k in set(memo_v1) | set(memo_v2)
                       if memo_v1.get(k) != memo_v2.get(k)}

            if not changed:
                st.success("✅ No differences found between v1 and v2.")
            else:
                for field, (old, new) in changed.items():
                    with st.expander(f"🔄 {field}"):
                        col1, col2 = st.columns(2)
                        col1.markdown("**v1:**")
                        col1.write(old)
                        col2.markdown("**v2:**")
                        col2.write(new)

        # Also show the text changelog if it exists
        changelog_path = selected_dir / "v2" / "changes.md"
        if changelog_path.exists():
            with st.expander("📝 Changelog (changes.md)"):
                st.markdown(changelog_path.read_text(encoding="utf-8"))
