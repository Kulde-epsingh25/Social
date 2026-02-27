"""Streamlit monitoring dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable when launched via `streamlit run`.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    import streamlit as st
except ImportError:
    raise SystemExit("Install streamlit: pip install streamlit")

from src.dashboard.metrics import MetricsCollector
from src.publishing.hitl_queue import HITLQueue
from src.config.settings import settings


def main() -> None:
    """Entry point for the Streamlit dashboard."""
    st.set_page_config(
        page_title="Political Accountability Dashboard",
        page_icon="⚖️",
        layout="wide",
    )

    st.title("⚖️ Autonomous Political Accountability System")
    st.caption("Monitoring dashboard — IT Rules 2026 compliant | AI-Generated content")

    metrics = MetricsCollector()
    hitl = HITLQueue()

    # ── Sidebar ──────────────────────────────────────────────────────
    st.sidebar.header("System Configuration")
    st.sidebar.metric("Max Posts/Day", settings.max_posts_per_day)
    st.sidebar.metric("Post Interval (min)", settings.post_interval_minutes)
    st.sidebar.metric(
        "HITL Mode", "Enabled ✅" if settings.hitl_enabled else "Disabled ⚠️"
    )

    # ── Metrics row ───────────────────────────────────────────────────
    summary = metrics.get_summary()
    col1, col2, col3 = st.columns(3)
    col1.metric("Events Processed", summary["events_processed"])
    col2.metric("Posts Published", summary["posts_published"])
    col3.metric("Compliance Checks", summary["compliance_checks"])

    st.divider()

    # ── HITL review queue ─────────────────────────────────────────────
    st.subheader("🔍 Human Review Queue")
    pending = hitl.get_pending_reviews()
    if not pending:
        st.info("No posts pending review.")
    else:
        for item in pending:
            with st.expander(
                f"Review ID: {item['review_id'][:8]}… | {item['created_at'][:19]}"
            ):
                st.text_area(
                    "Post content",
                    item["post_content"],
                    height=150,
                    key=f"content_{item['review_id']}",
                    disabled=True,
                )
                analysis = item.get("analysis", {})
                st.json(analysis)
                col_a, col_r = st.columns(2)
                if col_a.button("✅ Approve", key=f"approve_{item['review_id']}"):
                    hitl.approve(item["review_id"])
                    st.success("Approved!")
                    st.rerun()
                reason = col_r.text_input(
                    "Rejection reason", key=f"reason_{item['review_id']}"
                )
                if col_r.button("❌ Reject", key=f"reject_{item['review_id']}"):
                    hitl.reject(item["review_id"], reason)
                    st.warning("Rejected.")
                    st.rerun()

    st.divider()

    # ── Philosophical framework usage ─────────────────────────────────
    st.subheader("📚 Philosophical Framework Usage")
    frameworks = [
        "Kantian (Deontology)",
        "Utilitarian (Mill/Bentham)",
        "Lockean (Liberty)",
        "Rawlsian (Justice)",
        "Virtue Ethics",
        "Machiavellian",
    ]
    # Placeholder data – replace with live metric queries.
    import random
    usage = {f: random.randint(1, 20) for f in frameworks}  # noqa: S311
    st.bar_chart(usage)

    st.divider()

    # ── System health ─────────────────────────────────────────────────
    st.subheader("🏥 System Health")
    health_col1, health_col2, health_col3 = st.columns(3)
    health_col1.metric("News API", "✅ Connected" if settings.news_api_key else "⚠️ Not configured")
    health_col2.metric("X API", "✅ Connected" if settings.x_api_key else "⚠️ Not configured")
    health_col3.metric("OpenAI", "✅ Connected" if settings.openai_api_key else "⚠️ Not configured")


if __name__ == "__main__":
    main()
