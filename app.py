"""
Streamlit Web Dashboard for RedBus Intelligent Ticket Search and Automation System.
Enterprise Autonomics UI providing real-time workflow orchestration,
monitoring, incident self-healing telemetry, and operational reporting.
"""

import json
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional

import streamlit as st
import pandas as pd

from redbus_automation.config import CONFIG
from redbus_automation.models import SearchRequest, WorkflowStatus
from redbus_automation.orchestrator import AutomationOrchestrator
from redbus_automation.monitoring import MONITOR
from redbus_automation.logger import LOGGER

# -----------------------------------------------------------------------------
# Streamlit Page Setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="RedBus Intelligent Automation | HCLTech Autonomics",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Enterprise CSS
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.1rem;
        font-weight: 700;
        color: #d84e55;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #555;
        margin-bottom: 15px;
    }
    .sim-badge {
        background-color: #ffebe6;
        color: #bf2600;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid #ffbdad;
        display: inline-block;
        margin-bottom: 12px;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 6px;
        padding: 12px;
        border-left: 4px solid #d84e55;
    }
    .status-success {
        color: #00875a;
        font-weight: bold;
    }
    .status-recovered {
        color: #ff991f;
        font-weight: bold;
    }
    .status-failed {
        color: #de350b;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State
if "last_result" not in st.session_state:
    st.session_state.last_result = None

# -----------------------------------------------------------------------------
# Header & Compliance Notice
# -----------------------------------------------------------------------------
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown('<div class="main-header">🚌 RedBus Intelligent Automation Platform</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Offline-First Enterprise Workflow Orchestration, Autonomics & Observability Engine</div>',
        unsafe_allow_html=True,
    )
with col_h2:
    st.markdown(
        f'<div class="sim-badge">⚠️ {CONFIG.SIMULATION_DISCLAIMER}</div>',
        unsafe_allow_html=True,
    )

st.divider()

# -----------------------------------------------------------------------------
# Sidebar: Automation Inputs & Fault Injection
# -----------------------------------------------------------------------------
st.sidebar.header("🎯 Automation Parameters")

default_tomorrow = date.today() + timedelta(days=1)

source_city = st.sidebar.selectbox(
    "Source City",
    options=["Bangalore", "Hyderabad", "Chennai", "Pune", "Delhi", "Mumbai", "Jaipur", "Kolkata"],
    index=0,
)

dest_city = st.sidebar.selectbox(
    "Destination City",
    options=["Hyderabad", "Bangalore", "Chennai", "Pune", "Delhi", "Mumbai", "Jaipur", "Kolkata"],
    index=0 if source_city != "Hyderabad" else 1,
)

journey_date = st.sidebar.date_input(
    "Journey Date",
    value=default_tomorrow,
    min_value=date.today(),
)

passengers = st.sidebar.number_input(
    "Passenger Count",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
)

max_budget = st.sidebar.number_input(
    "Max Budget (₹)",
    min_value=200.0,
    max_value=10000.0,
    value=2500.0,
    step=100.0,
)

with st.sidebar.expander("⚙️ Optional Filtering"):
    pref_operator = st.text_input("Preferred Operator", value="")
    min_rating = st.slider("Minimum Rating", min_value=1.0, max_value=5.0, value=3.0, step=0.1)

# Autonomics Fault Injection Panel
st.sidebar.markdown("---")
st.sidebar.header("🧪 Autonomics Fault Injection")
st.sidebar.caption("Simulate controlled infrastructure and service disruptions to test self-healing resilience.")

sim_transient = st.sidebar.checkbox("Simulate Gateway 503 Timeout (Retry/Mirror)", value=False)
sim_corruption = st.sidebar.checkbox("Simulate Catalog Corruption (Seed Recovery)", value=False)
sim_empty = st.sidebar.checkbox("Simulate Empty Search Results", value=False)
sim_report_fail = st.sidebar.checkbox("Simulate Report Generation Lock", value=False)
sim_repeated_fail = st.sidebar.checkbox("Simulate Repeated Unrecoverable Failure", value=False)

st.sidebar.markdown("---")
execute_clicked = st.sidebar.button("🚀 Search & Execute Automation", type="primary", use_container_width=True)

if st.sidebar.button("🔄 Reset Observability Metrics", use_container_width=True):
    MONITOR.reset_metrics()
    st.sidebar.success("Monitoring telemetry reset.")
    st.rerun()

# -----------------------------------------------------------------------------
# Automation Execution Trigger
# -----------------------------------------------------------------------------
if execute_clicked:
    request = SearchRequest(
        source=source_city,
        destination=dest_city,
        journey_date=journey_date.strftime("%Y-%m-%d"),
        passengers=int(passengers),
        max_budget=float(max_budget),
        preferred_operator=pref_operator.strip() if pref_operator.strip() else None,
        min_rating=float(min_rating),
    )

    faults = {
        "simulate_transient_failure": sim_transient,
        "simulate_corruption": sim_corruption,
        "force_empty": sim_empty,
        "simulate_report_failure": sim_report_fail,
        "repeated_workflow_failure": sim_repeated_fail,
    }

    with st.spinner("Orchestrating workflow: Validation -> Search -> Retries -> Filter -> Ranking -> Reporting..."):
        orchestrator = AutomationOrchestrator()
        result = orchestrator.run_workflow(request, fault_injection=faults)
        st.session_state.last_result = result

# -----------------------------------------------------------------------------
# Main Dashboard Body
# -----------------------------------------------------------------------------
tab_overview, tab_results, tab_monitoring, tab_recovery, tab_logs, tab_reports = st.tabs([
    "📊 Automation Overview",
    "🚌 Bus Search Results",
    "📈 Workflow Monitoring",
    "🛡️ Incident & Recovery",
    "📜 Execution Logs",
    "📁 Reports & Artifacts",
])

result = st.session_state.last_result

# -----------------------------------------------------------------------------
# TAB 1: Automation Overview
# -----------------------------------------------------------------------------
with tab_overview:
    if result is None:
        st.info("👈 Configure parameters in the sidebar and click **'Search & Execute Automation'** to start.")
    else:
        # Status Banner
        if result.status == WorkflowStatus.SUCCESS:
            st.success(f"✅ Workflow Execution **{result.execution_id}** completed successfully in {result.execution_duration_sec:.3f}s.")
        elif result.status == WorkflowStatus.RECOVERED:
            st.warning(f"⚠️ Workflow **{result.execution_id}** recovered via self-healing in {result.execution_duration_sec:.3f}s.")
        else:
            st.error(f"❌ Workflow **{result.execution_id}** terminated with status FAILED in {result.execution_duration_sec:.3f}s: {result.error_message}")

        # Top KPIs
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Execution ID", result.execution_id.split("-")[-1])
        k1.caption(result.execution_id)
        k2.metric("Workflow Status", result.status.value)
        k3.metric("Duration", f"{result.execution_duration_sec:.3f}s")
        k4.metric("Retry Attempts", len(result.retry_history))
        k5.metric("Recovery Actions", len(result.recovery_history))

        st.markdown("### 🏆 Top Recommended Bus")
        if result.recommended_bus:
            top = result.recommended_bus
            with st.container(border=True):
                r_col1, r_col2, r_col3 = st.columns([2, 1, 1])
                with r_col1:
                    st.subheader(f"{top.bus.operator_name}")
                    st.caption(f"Bus ID: {top.bus.bus_id} | Type: {top.bus.bus_type}")
                    st.info(f"💡 **Decision Explainability:** {top.recommendation_reason}")

                with r_col2:
                    st.metric("Optimal Fare", f"₹{top.bus.fare:.2f}")
                    st.metric("Composite Score", f"{top.composite_score:.4f}")

                with r_col3:
                    st.metric("Schedule", f"{top.bus.departure_time} - {top.bus.arrival_time}")
                    st.caption(f"Duration: {top.bus.duration_formatted}")
                    st.metric("Rating / Seats", f"{top.bus.rating}★ | {top.bus.available_seats} seats")
        else:
            st.warning("No candidate bus met the specified search and budget constraints.")

# -----------------------------------------------------------------------------
# TAB 2: Bus Search Results
# -----------------------------------------------------------------------------
with tab_results:
    if result and result.ranked_buses:
        st.write(f"Displaying **{len(result.ranked_buses)}** evaluated buses ranked by multi-criteria decision algorithm:")

        table_data = []
        for rb in result.ranked_buses:
            table_data.append({
                "Rank": f"#{rb.rank}",
                "Bus ID": rb.bus.bus_id,
                "Operator": rb.bus.operator_name,
                "Type": rb.bus.bus_type,
                "Departure": rb.bus.departure_time,
                "Arrival": rb.bus.arrival_time,
                "Duration": rb.bus.duration_formatted,
                "Fare (₹)": rb.bus.fare,
                "Rating": f"{rb.bus.rating} ★",
                "Seats": rb.bus.available_seats,
                "Score": rb.composite_score,
                "Recommendation Explanation": rb.recommendation_reason,
            })

        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    elif result and not result.ranked_buses:
        st.warning("No bus matches found for the given criteria.")
    else:
        st.info("Execute a search to view bus ranking details.")

# -----------------------------------------------------------------------------
# TAB 3: Workflow Monitoring & Observability
# -----------------------------------------------------------------------------
with tab_monitoring:
    st.subheader("📈 Real-Time System Telemetry")
    metrics = MONITOR.get_metrics()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Executions", metrics["total_executions"])
    m2.metric("Successful Executions", metrics["successful_executions"])
    m3.metric("Failed Executions", metrics["failed_executions"])
    m4.metric("Recovered Executions", metrics["recovered_executions"])

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Success Rate", f"{metrics['success_rate_percent']}%")
    m6.metric("Failure Rate", f"{metrics['failure_rate_percent']}%")
    m7.metric("Average Latency", f"{metrics['average_duration_sec']}s")
    m8.metric("System Retries", metrics["total_retry_attempts"])

    st.markdown("#### System Health Status")
    status_color = "status-success" if metrics["failure_rate_percent"] < 20 else "status-failed"
    st.markdown(
        f"Active Execution ID: `{metrics['active_execution_id'] or 'IDLE'}` | "
        f"Last Engine Status: <span class='{status_color}'>{metrics['current_execution_status']}</span>",
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# TAB 4: Incident & Recovery
# -----------------------------------------------------------------------------
with tab_recovery:
    st.subheader("🛡️ Autonomic Resilience & Self-Healing Telemetry")

    if result:
        col_rec1, col_rec2 = st.columns(2)
        with col_rec1:
            st.markdown("#### Bounded Retry Telemetry")
            if result.retry_history:
                for r in result.retry_history:
                    st.warning(
                        f"**Attempt {r.attempt_number}** | Delay: {r.delay_seconds:.3f}s | "
                        f"Function: `{r.target_function}`\n\n*Cause:* {r.error_message}"
                    )
            else:
                st.success("No retries triggered. Workflow executed on initial attempt.")

        with col_rec2:
            st.markdown("#### Self-Healing Remediation Actions")
            if result.recovery_history:
                for rec in result.recovery_history:
                    icon = "✅" if rec.successful else "❌"
                    with st.container(border=True):
                        st.markdown(f"**{icon} Action:** `{rec.action_id}` | Strategy: **{rec.strategy_used}**")
                        st.write(rec.details)
                        st.caption(f"Timestamp: {rec.timestamp}")
            else:
                st.info("No failure incidents detected. System operated within normal parameters.")
    else:
        st.info("Execute a workflow with fault injection to observe incident response and recovery.")

# -----------------------------------------------------------------------------
# TAB 5: Execution Logs
# -----------------------------------------------------------------------------
with tab_logs:
    st.subheader("📜 Structured JSON Telemetry Logs")

    all_logs = LOGGER.get_logs()
    filter_cur = st.checkbox("Show only logs for current execution", value=True)

    if result and filter_cur:
        displayed_logs = [log for log in all_logs if log.get("execution_id") == result.execution_id]
    else:
        displayed_logs = all_logs

    if displayed_logs:
        log_df = pd.DataFrame(displayed_logs)
        cols_to_show = ["timestamp", "execution_id", "severity", "component", "event_type", "message", "execution_status"]
        st.dataframe(log_df[cols_to_show], use_container_width=True, hide_index=True)

        with st.expander("🔍 View Raw JSON Lines"):
            st.json(displayed_logs[-15:])
    else:
        st.info("No execution logs recorded yet.")

# -----------------------------------------------------------------------------
# TAB 6: Reports & Artifacts
# -----------------------------------------------------------------------------
with tab_reports:
    st.subheader("📁 Operational Audit Artifacts")

    if result and result.report_paths:
        csv_file = Path(result.report_paths.get("csv", ""))
        json_file = Path(result.report_paths.get("json", ""))

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            if csv_file.exists():
                with open(csv_file, "r", encoding="utf-8") as f:
                    csv_data = f.read()
                st.download_button(
                    label="📥 Download CSV Execution Report",
                    data=csv_data,
                    file_name=csv_file.name,
                    mime="text/csv",
                    use_container_width=True,
                )
                st.code(csv_data[:400] + "\n...", language="csv")

        with col_d2:
            if json_file.exists():
                with open(json_file, "r", encoding="utf-8") as f:
                    json_data = f.read()
                st.download_button(
                    label="📥 Download JSON Execution Report",
                    data=json_data,
                    file_name=json_file.name,
                    mime="application/json",
                    use_container_width=True,
                )
                st.json(json.loads(json_data))
    else:
        st.info("Execute an automation run to generate and download compliance reports.")
