"""
RedBus Intelligent Ticket Search and Automation Platform.
Enterprise Autonomics Operations Console & Booking Simulation Center.

Implements:
1. Executive Dashboard (KPIs, Health, Recovery Rate)
2. Automation Workflow (Visual Pipeline & Stage Tracking)
3. Bus Search & Simulated Booking Workflow (Seat selection, PNR generation, Booking History)
4. Incident Center (Incident lifecycle, failure classification, resolution metrics)
5. Reports & Audit Center (CSV/JSON artifacts, health telemetry)
"""

import json
import inspect
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
import pandas as pd

from redbus_automation.config import CONFIG
from redbus_automation.models import (
    AutomationEventType,
    SearchRequest,
    WorkflowExecutionResult,
    WorkflowStatus,
)
from redbus_automation.orchestrator import AutomationOrchestrator
from redbus_automation.monitoring import MONITOR
from redbus_automation.logger import LOGGER
from redbus_automation.incident_manager import INCIDENT_MANAGER
from redbus_automation.booking_engine import BOOKING_ENGINE
from redbus_automation.html_utils import escape_html
from redbus_automation.search_engine import BusSearchEngine


def _card_container():
    if "border" in inspect.signature(st.container).parameters:
        return st.container(border=True)
    return st.container()


def _build_workflow_stages(
    result: Optional[WorkflowExecutionResult],
    events: Optional[List[Dict[str, Any]]] = None,
) -> List[dict[str, str]]:
    stage_definitions = [
        ("Request Initialization", "Workflow execution was created and started."),
        ("Input Validation", "Request fields and business constraints were checked."),
        ("Bus Search", "Primary catalog search and any recorded recovery were evaluated."),
        ("Availability Evaluation", "Search results were evaluated against request constraints."),
        ("MCDA Recommendation", "Eligible results were ranked for recommendation."),
        ("Audit Report Generation", "Execution audit reports were generated."),
        ("Booking Simulation", "A simulated booking was recorded for this execution."),
        ("Execution Outcome", "The orchestrator returned its final execution result."),
        ("Audit Logging", "A terminal workflow event was recorded for this execution."),
    ]
    stages = [
        {"name": name, "description": description, "status": "Pending"}
        for name, description in stage_definitions
    ]

    if result is None:
        return stages

    events = events if events is not None else LOGGER.get_logs(result.execution_id)
    event_types = {entry.get("event_type") for entry in events}
    stage_position = {
        "WORKFLOW_INITIATION": 0,
        "INPUT_VALIDATION": 1,
        "CATALOG_SEARCH": 2,
        "AUTONOMIC_RECOVERY": 3,
        "FILTERING": 4,
        "FILTER_RELAXATION_RECOVERY": 5,
        "RANKING": 6,
        "REPORTING": 7,
        "COMPLETED": 8,
    }.get(result.stage_reached, 0)
    validation_passed = (
        AutomationEventType.VALIDATION_PASSED.value in event_types
        or stage_position > 1
    )
    validation_failed = (
        AutomationEventType.VALIDATION_FAILED.value in event_types
        or (
            result.stage_reached == "INPUT_VALIDATION"
            and result.status == WorkflowStatus.FAILED
        )
    )
    search_completed = (
        AutomationEventType.SEARCH_COMPLETED.value in event_types
        or stage_position > 3
    )
    search_failed = (
        result.status == WorkflowStatus.FAILED
        and result.stage_reached in ("CATALOG_SEARCH", "AUTONOMIC_RECOVERY")
    )
    availability_completed = (
        AutomationEventType.FILTER_APPLIED.value in event_types
        or stage_position > 5
    )
    availability_failed = (
        result.status == WorkflowStatus.FAILED
        and result.stage_reached in ("FILTERING", "FILTER_RELAXATION_RECOVERY")
        and not availability_completed
    )
    ranking_completed = (
        AutomationEventType.RANKING_COMPLETED.value in event_types
        or stage_position > 6
    )
    ranking_failed = (
        result.status == WorkflowStatus.FAILED
        and result.stage_reached == "RANKING"
        and not ranking_completed
    )
    report_generated = (
        AutomationEventType.REPORT_GENERATED.value in event_types
        or bool(result.report_paths)
        or stage_position > 7
    )
    report_failed = (
        result.status == WorkflowStatus.FAILED
        and result.stage_reached == "REPORTING"
        and not report_generated
    )

    initialization_failed = (
        result.status == WorkflowStatus.FAILED
        and result.stage_reached == "WORKFLOW_INITIATION"
    )
    stages[0]["status"] = (
        "Failed"
        if initialization_failed
        else "Completed"
        if AutomationEventType.WORKFLOW_STARTED.value in event_types or result.start_time
        else "Pending"
    )
    stages[1]["status"] = (
        "Completed"
        if validation_passed
        else "Failed"
        if validation_failed
        else "Skipped"
    )
    stages[2]["status"] = (
        "Completed"
        if search_completed
        else "Failed"
        if search_failed
        else "Skipped"
    )
    stages[3]["status"] = (
        "Completed"
        if availability_completed
        else "Failed"
        if availability_failed
        else "Skipped"
    )
    stages[4]["status"] = (
        "Completed"
        if ranking_completed
        else "Failed"
        if ranking_failed
        else "Skipped"
    )
    stages[5]["status"] = (
        "Completed"
        if report_generated
        else "Failed"
        if report_failed
        else "Skipped"
    )
    stages[6]["status"] = (
        "Completed"
        if AutomationEventType.BOOKING_SIMULATED.value in event_types
        else "Skipped"
    )
    stages[7]["status"] = "Completed"
    terminal_events = {
        AutomationEventType.WORKFLOW_COMPLETED.value,
        AutomationEventType.WORKFLOW_TERMINATED.value,
        AutomationEventType.VALIDATION_FAILED.value,
    }
    stages[8]["status"] = (
        "Completed" if terminal_events.intersection(event_types) else "Pending"
    )

    if search_completed and result.recovery_history:
        stages[2]["description"] = (
            "Search completed with recorded recovery: "
            + ", ".join(action.strategy_used for action in result.recovery_history)
            + "."
        )
    if ranking_completed and result.recommended_bus is None:
        stages[4]["description"] = (
            "Ranking completed; no eligible recommendation was returned."
        )
    if report_generated and result.status == WorkflowStatus.FAILED:
        stages[5]["description"] = (
            "Failure audit reports were generated for this unsuccessful execution."
        )
    if report_failed:
        stages[5]["description"] = (
            "The workflow failed during report generation; no report artifact was returned."
        )
    if stages[6]["status"] == "Skipped":
        stages[6]["description"] = (
            "No booking record is linked to this execution; booking is a separate action."
        )
    stages[7]["description"] = (
        f"Final result: {result.status.value} at {result.stage_reached}."
    )
    if stages[8]["status"] == "Pending":
        stages[8]["description"] = (
            "No terminal workflow event is available to confirm this stage."
        )

    return stages


# -----------------------------------------------------------------------------
# 1. Page Configuration & Meta
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="RedBus Intelligent Automation | Enterprise Autonomics Console",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# 2. Enterprise SaaS Dark Theme CSS System
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --bg-main: #0B0F17;
        --bg-card: #111827;
        --bg-card-hover: #162032;
        --border-subtle: rgba(255, 255, 255, 0.08);
        --border-accent: rgba(59, 130, 246, 0.35);
        --accent-blue: #3B82F6;
        --accent-indigo: #6366F1;
        --accent-emerald: #10B981;
        --accent-amber: #F59E0B;
        --accent-rose: #EF4444;
        --text-primary: #F8FAFC;
        --text-secondary: #94A3B8;
        --text-muted: #64748B;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background-color: var(--bg-main) !important;
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--text-primary) !important;
    }

    [data-testid="stHeader"] { background: transparent !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 96% !important;
    }

    /* Custom Scrollbars */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0B0F17; }
    ::-webkit-scrollbar-thumb { background: #1E293B; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #334155; }

    /* Top Application Bar */
    .top-navbar {
        background: linear-gradient(180deg, rgba(17, 24, 39, 0.95) 0%, rgba(15, 23, 42, 0.75) 100%);
        backdrop-filter: blur(12px);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 16px 24px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .brand-title {
        font-size: 1.35rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .brand-badge {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: #FFFFFF;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        padding: 3px 8px;
        border-radius: 4px;
        display: inline-block;
    }

    .brand-subtitle {
        font-size: 0.82rem;
        color: var(--text-secondary);
        margin-top: 2px;
    }

    .pill-badge {
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    .pill-simulated {
        background: rgba(245, 158, 11, 0.12);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.28);
    }

    .pill-online {
        background: rgba(16, 185, 129, 0.12);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.28);
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #0D131F !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
    }

    .sidebar-section-title {
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #60A5FA;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    /* Primary & Secondary Buttons */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        border-radius: 8px !important;
        border: 1px solid #3B82F6 !important;
        padding: 10px 18px !important;
        box-shadow: 0 4px 16px rgba(37, 99, 235, 0.35) !important;
        transition: all 0.2s ease !important;
    }

    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5) !important;
        transform: translateY(-1px) !important;
    }

    div.stButton > button[kind="secondary"] {
        background: #1E293B !important;
        color: #CBD5E1 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }

    /* KPI Cards */
    .saas-kpi-card {
        background: linear-gradient(145deg, #111827 0%, #0F172A 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 18px 20px;
        position: relative;
        overflow: hidden;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }

    .saas-kpi-card:hover {
        transform: translateY(-2px);
        border-color: rgba(59, 130, 246, 0.4);
    }

    .kpi-label {
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: var(--text-secondary);
        margin-bottom: 6px;
    }

    .kpi-value {
        font-size: 1.85rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #FFFFFF;
        line-height: 1.1;
    }

    .kpi-subtext {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin-top: 6px;
    }

    /* Tabs Styling */
    div[data-baseweb="tab-list"] {
        gap: 6px;
        background: #0F172A;
        padding: 5px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.06);
        margin-bottom: 20px;
    }

    div[data-baseweb="tab"] {
        height: 42px;
        background: transparent !important;
        border: none !important;
        border-radius: 7px !important;
        color: #94A3B8 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 0 16px !important;
        transition: all 0.2s ease !important;
    }

    div[aria-selected="true"] {
        background: #1E293B !important;
        color: #60A5FA !important;
        border-bottom: 2px solid #3B82F6 !important;
    }

    /* Status Alert Banners */
    .status-banner {
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 18px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .status-banner-success {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #34D399;
    }

    .status-banner-recovered {
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.3);
        color: #FBBF24;
    }

    .status-banner-failed {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        color: #F87171;
    }

    /* Seat Layout Grid */
    .seat-badge-avail {
        background: #1E293B;
        color: #60A5FA;
        border: 1px solid #3B82F6;
        border-radius: 4px;
        padding: 4px 8px;
        font-family: monospace;
        display: inline-block;
        margin: 2px;
    }

    .seat-badge-booked {
        background: rgba(239, 68, 68, 0.15);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 4px;
        padding: 4px 8px;
        font-family: monospace;
        display: inline-block;
        margin: 2px;
    }

    /* Booking Confirmation Card */
    .confirmation-pass {
        background: linear-gradient(135deg, #111827 0%, #0F172A 100%);
        border: 1px solid #10B981;
        border-radius: 12px;
        padding: 22px;
        margin-top: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 3. Session State Management
# -----------------------------------------------------------------------------
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "selected_bus_for_booking" not in st.session_state:
    st.session_state.selected_bus_for_booking = None
if "latest_booking_confirmation" not in st.session_state:
    st.session_state.latest_booking_confirmation = None

# -----------------------------------------------------------------------------
# 4. Top Navigation Bar & Operational Header
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="top-navbar">
        <div>
            <div class="brand-title">
                <span>⚡ REDBUS INTELLIGENT AUTOMATION</span>
                <span class="brand-badge">AUTONOMICS OS</span>
            </div>
            <div class="brand-subtitle">
                Self-Healing Operations Console, Autonomic Workflow Orchestration & Simulated Booking Engine
            </div>
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
            <div class="pill-badge pill-online">
                <span style="font-size: 10px;">●</span> ENGINE ACTIVE (OFFLINE NODE)
            </div>
            <div class="pill-badge pill-simulated">
                ⚠️ DEMO / SIMULATION MODE
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 5. Enterprise Sidebar (Grouped Controls)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style="padding: 10px 0 16px 0; border-bottom: 1px solid rgba(255,255,255,0.06); margin-bottom: 14px;">
            <div style="font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: #60A5FA;">
                CONTROL CONSOLE
            </div>
            <div style="font-size: 1.1rem; font-weight: 700; color: #FFFFFF;">
                Workflow Parameters
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section 1: Route Parameters
    st.markdown('<div class="sidebar-section-title">📍 Route & Schedule</div>', unsafe_allow_html=True)
    city_options = BusSearchEngine().get_all_cities()
    source_default = city_options.index("Bangalore") if "Bangalore" in city_options else 0
    source_city = st.selectbox("Origin City", options=city_options, index=source_default)
    destination_options = [city for city in city_options if city != source_city]
    preferred_destination = "Hyderabad" if source_city == "Bangalore" else "Bangalore"
    destination_default = (
        destination_options.index(preferred_destination)
        if preferred_destination in destination_options
        else 0
    )
    dest_city = st.selectbox(
        "Destination City",
        options=destination_options,
        index=destination_default,
    )

    default_tomorrow = date.today() + timedelta(days=1)
    journey_date = st.date_input("Travel Date", value=default_tomorrow, min_value=date.today())

    # Section 2: Capacity & Constraints
    st.markdown('<div class="sidebar-section-title" style="margin-top: 14px;">👥 Capacity & Budget</div>', unsafe_allow_html=True)
    col_pax, col_bud = st.columns([1, 1.2])
    with col_pax:
        passengers = st.number_input("Passengers", min_value=1, max_value=10, value=1, step=1)
    with col_bud:
        max_budget = st.number_input("Max Fare (₹)", min_value=200.0, max_value=10000.0, value=2500.0, step=100.0)

    # Section 3: Preference Filters
    with st.expander("⚙️ Advanced Preferences"):
        pref_operator = st.text_input("Preferred Operator", placeholder="e.g. Orange, KSRTC, IntrCity")
        min_rating = st.slider("Minimum Rating Threshold", min_value=1.0, max_value=5.0, value=3.0, step=0.1)

    # Section 4: Fault Injection Panel (Resilience Testing)
    st.markdown('<div class="sidebar-section-title" style="margin-top: 16px;">🧪 Autonomics Fault Injection</div>', unsafe_allow_html=True)
    with st.expander("Controlled Disruption Scenarios", expanded=False):
        st.caption("Inject controlled faults to observe self-monitoring & self-healing:")
        sim_transient = st.checkbox("Scenario 2: Gateway 503 Timeout (Retry/Mirror)", value=False)
        sim_corruption = st.checkbox("Scenario 3: Catalog Corruption (Fallback Restore)", value=False)
        sim_empty = st.checkbox("Scenario 4: Empty Search Results", value=False)
        sim_report_fail = st.checkbox("Simulate Report Filesystem Lock", value=False)
        sim_repeated_fail = st.checkbox("Scenario 5: Complete Unrecoverable Outage", value=False)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Primary Workflow Trigger
    execute_clicked = st.button("🚀 Search & Orchestrate Workflow", type="primary", use_container_width=True)

    # Secondary Actions
    if st.button("🔄 Reset Telemetry Counters", use_container_width=True):
        MONITOR.reset_metrics()
        INCIDENT_MANAGER.reset_incidents()
        st.toast("Telemetry and Incident counters reset to baseline.", icon="📊")
        st.rerun()

    st.markdown(
        """
        <div style="font-size: 0.72rem; color: #64748B; text-align: center; margin-top: 24px;">
            RedBus Intelligent Autonomics Engine<br>
            Offline Enterprise Evaluation Build v1.1.0
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# 6. Workflow Orchestration Execution
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

    with st.spinner("Executing Autonomic Pipeline: Validation → Bounded Retry → Fallback Recovery → MCDA Ranking → Reporting..."):
        orchestrator = AutomationOrchestrator()
        result = orchestrator.run_workflow(request, fault_injection=faults)
        st.session_state.last_result = result
        if result.recommended_bus:
            st.session_state.selected_bus_for_booking = result.recommended_bus.bus

result = st.session_state.last_result

# -----------------------------------------------------------------------------
# 7. Main Dashboard Tabs
# -----------------------------------------------------------------------------
tab_exec, tab_workflow, tab_search, tab_incident, tab_reports = st.tabs([
    "📊 Executive Dashboard",
    "⚙️ Automation Workflow",
    "🚌 Bus Search & Booking Simulation",
    "🛡️ Incident Center",
    "📁 Reports & Audit Center",
])

# -----------------------------------------------------------------------------
# TAB 1: Executive Dashboard
# -----------------------------------------------------------------------------
with tab_exec:
    m = MONITOR.get_metrics()
    inc_sum = INCIDENT_MANAGER.get_summary()

    # System Health Badge Banner
    health_status = "HEALTHY" if m["failure_rate_percent"] < 25 else "DEGRADED"
    health_color = "#10B981" if health_status == "HEALTHY" else "#EF4444"

    st.markdown(
        f"""
        <div style="background: rgba(17, 24, 39, 0.7); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 12px 18px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 1.1rem; color: {health_color};">●</span>
                <span style="font-size: 0.9rem; font-weight: 700; color: #FFFFFF;">SYSTEM HEALTH STATUS:</span>
                <span style="background: {health_color}22; color: {health_color}; border: 1px solid {health_color}44; padding: 2px 10px; border-radius: 4px; font-weight: 700; font-size: 0.8rem;">{health_status}</span>
            </div>
            <div style="font-size: 0.8rem; color: #94A3B8;">
                Engine State: <strong style="color: #60A5FA;">{m['current_execution_status']}</strong> &nbsp;|&nbsp; Active Node: <strong>Local Offline Core</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Top KPI Metrics Row
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(
            f"""
            <div class="saas-kpi-card">
                <div class="kpi-label">Total Searches</div>
                <div class="kpi-value">{m['total_executions']}</div>
                <div class="kpi-subtext">Total orchestrations</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="saas-kpi-card">
                <div class="kpi-label">Clean Successes</div>
                <div class="kpi-value" style="color: #34D399;">{m['successful_executions'] - m['recovered_executions']}</div>
                <div class="kpi-subtext">Zero-intervention runs</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="saas-kpi-card">
                <div class="kpi-label">Recovered Runs</div>
                <div class="kpi-value" style="color: #FBBF24;">{m['recovered_executions']}</div>
                <div class="kpi-subtext">Self-healing remediations</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="saas-kpi-card">
                <div class="kpi-label">Failure Count</div>
                <div class="kpi-value" style="color: #EF4444;">{m['failed_executions']}</div>
                <div class="kpi-subtext">Permanent / unrecoverable</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c5:
        recovery_rate = round((m['recovered_executions'] / (m['recovered_executions'] + m['failed_executions']) * 100.0), 1) if (m['recovered_executions'] + m['failed_executions']) > 0 else 100.0
        st.markdown(
            f"""
            <div class="saas-kpi-card">
                <div class="kpi-label">Recovery Rate</div>
                <div class="kpi-value" style="color: #60A5FA;">{recovery_rate}%</div>
                <div class="kpi-subtext">Autonomic healing efficacy</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c6:
        st.markdown(
            f"""
            <div class="saas-kpi-card">
                <div class="kpi-label">Avg Execution Time</div>
                <div class="kpi-value">{m['average_duration_sec']}s</div>
                <div class="kpi-subtext">Rolling arithmetic mean</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Operational Status Summary & Recommendation
    if result is not None:
        if result.status == WorkflowStatus.SUCCESS:
            banner_class = "status-banner-success"
            banner_icon = "✅"
            status_desc = f"All stages completed successfully in {result.execution_duration_sec:.3f}s."
        elif result.status == WorkflowStatus.RECOVERED:
            banner_class = "status-banner-recovered"
            banner_icon = "🛡️"
            status_desc = f"Automated self-healing triggered and recovered in {result.execution_duration_sec:.3f}s."
        else:
            banner_class = "status-banner-failed"
            banner_icon = "❌"
            status_desc = f"Workflow halted with status FAILED: {escape_html(result.error_message or '')}"

        st.markdown(
            f"""
            <div class="status-banner {banner_class}">
                <div>
                    <strong>{banner_icon} Run Execution ID:</strong> <code>{escape_html(result.execution_id)}</code> &nbsp;•&nbsp;
                    <strong>Status:</strong> {escape_html(result.status.value)}
                    <div style="font-size: 0.82rem; margin-top: 2px;">{status_desc}</div>
                </div>
                <div style="font-size: 0.85rem; font-weight: 600;">
                    Stage Reached: <span style="color: #60A5FA;">{escape_html(result.stage_reached)}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if result.recommended_bus:
            recommendation = result.recommended_bus
            with _card_container():
                st.markdown("#### Top-ranked simulated bus")
                st.caption(
                    "Recommendation from the current offline search and MCDA ranking."
                )
                st.markdown(
                    f"**{recommendation.bus.operator_name}** · "
                    f"`{recommendation.bus.bus_id}` · {recommendation.bus.bus_type}"
                )
                recommendation_metrics = st.columns(4)
                recommendation_metrics[0].metric(
                    "Fare", f"₹{recommendation.bus.fare:.2f}"
                )
                recommendation_metrics[1].metric(
                    "MCDA score", f"{recommendation.composite_score:.4f}"
                )
                recommendation_metrics[2].metric(
                    "Rating", f"{recommendation.bus.rating:.1f} / 5.0"
                )
                recommendation_metrics[3].metric(
                    "Available seats", recommendation.bus.available_seats
                )
                st.markdown(
                    f"**Journey:** {recommendation.bus.departure_time} · "
                    f"{result.request.source} → {result.request.destination} · "
                    f"{recommendation.bus.arrival_time} · "
                    f"{recommendation.bus.duration_formatted}"
                )
                st.caption("Decision rationale")
                st.write(recommendation.recommendation_reason)
        else:
            st.info(
                "No ranked recommendation is available for this execution. "
                "Review the Bus Search & Booking Simulation section for results."
            )
    else:
        st.info("👈 Configure route parameters in the sidebar and execute an orchestration to view operational insights.")

# -----------------------------------------------------------------------------
# TAB 2: Automation Workflow (Visual Pipeline & Stage Tracking)
# -----------------------------------------------------------------------------
with tab_workflow:
    st.markdown("### ⚙️ Automation Workflow & Execution Lifecycle")
    st.caption(
        "Execution stages and outcomes below are derived from the completed workflow "
        "result and its execution-scoped audit events."
    )

    execution_events = (
        LOGGER.get_logs(result.execution_id) if result is not None else []
    )
    workflow_stages = _build_workflow_stages(result, execution_events)
    if result is not None:
        completed_stages = sum(
            stage["status"] == "Completed" for stage in workflow_stages
        )
        failed_stages = sum(
            stage["status"] == "Failed" for stage in workflow_stages
        )
        recovery_attempts = sum(
            event.get("event_type") == AutomationEventType.RECOVERY_INITIATED.value
            for event in execution_events
        )
        st.markdown(f"**Execution ID:** `{result.execution_id}`")

        summary_columns = st.columns(7)
        summary_columns[0].metric("Overall status", result.status.value)
        summary_columns[1].metric("Total stages", len(workflow_stages))
        summary_columns[2].metric("Completed", completed_stages)
        summary_columns[3].metric("Failed", failed_stages)
        summary_columns[4].metric("Retries", len(result.retry_history))
        summary_columns[5].metric("Recovery actions", len(result.recovery_history))
        summary_columns[6].metric(
            "Execution time", f"{result.execution_duration_sec:.3f}s"
        )
        if recovery_attempts > len(result.recovery_history):
            st.caption(
                f"{recovery_attempts} recovery attempt(s) were logged; "
                f"{len(result.recovery_history)} recovery action(s) returned."
            )
    else:
        st.info("No execution recorded yet. Stages remain pending until a workflow runs.")
        summary_columns = st.columns(6)
        summary_columns[0].metric("Overall status", "Pending")
        summary_columns[1].metric("Total stages", len(workflow_stages))
        summary_columns[2].metric("Completed", "—")
        summary_columns[3].metric("Failed", "—")
        summary_columns[4].metric("Retries", "—")
        summary_columns[5].metric("Recovery actions", "—")

    st.markdown("#### Execution pipeline")
    status_icons = {
        "Pending": "⏳",
        "Running": "🔄",
        "Completed": "✅",
        "Failed": "❌",
        "Skipped": "⏭️",
    }
    for index, stage in enumerate(workflow_stages, start=1):
        with _card_container():
            stage_columns = st.columns([0.45, 4.2, 1.35])
            stage_columns[0].markdown(f"**{index:02d}**")
            stage_columns[1].markdown(f"**{stage['name']}**")
            stage_columns[1].caption(stage["description"])
            stage_columns[2].markdown(
                f"**{status_icons[stage['status']]} {stage['status']}**"
            )
        if index < len(workflow_stages):
            connector_columns = st.columns([1, 8, 1])
            connector_columns[1].markdown("↓")

    if result is not None:
        detail_columns = st.columns(2)
        with detail_columns[0]:
            st.markdown(f"#### Bounded Retry Telemetry ({len(result.retry_history)} events)")
            if result.retry_history:
                for retry in result.retry_history:
                    st.warning(
                        f"**Attempt #{retry.attempt_number}** | "
                        f"Delay: `{retry.delay_seconds:.3f}s` | "
                        f"Target: `{retry.target_function}`\n\n"
                        f"*Cause:* {retry.error_message}"
                    )
            else:
                st.caption("No retry events were recorded for this execution.")

        with detail_columns[1]:
            st.markdown("#### Self-Healing Remediation Stream")
            if result.recovery_history:
                for recovery in result.recovery_history:
                    with _card_container():
                        recovery_columns = st.columns([3, 1])
                        recovery_columns[0].markdown(
                            f"**Strategy:** {recovery.strategy_used}"
                        )
                        recovery_columns[1].markdown(
                            "**✅ Successful**"
                            if recovery.successful
                            else "**❌ Failed**"
                        )
                        st.caption(recovery.details)
                        st.caption(f"Action ID: `{recovery.action_id}`")
            else:
                st.caption("No recovery actions were returned for this execution.")

# -----------------------------------------------------------------------------
# TAB 3: Bus Search & Simulated Booking Workflow
# -----------------------------------------------------------------------------
with tab_search:
    st.markdown("### 🚌 Bus Search Results & Simulated Reservation")
    st.markdown(
        "<div style='font-size: 0.85rem; color: #F59E0B; margin-bottom: 14px;'>"
        "⚠️ <strong>DEMO / SIMULATION MODE:</strong> Offline simulated bus schedules. Seat reservations generate a simulated PNR confirmation without real payment or ticket booking."
        "</div>",
        unsafe_allow_html=True,
    )

    if result and result.ranked_buses:
        # Sorting Options
        sort_col1, sort_col2 = st.columns([2, 1])
        with sort_col2:
            sort_by = st.selectbox(
                "Sort Results By",
                options=["MCDA Score (Recommended)", "Fare: Low to High", "Duration: Shortest", "Rating: Highest"],
                index=0,
            )

        # Sort buses accordingly
        display_buses = list(result.ranked_buses)
        if sort_by == "Fare: Low to High":
            display_buses.sort(key=lambda rb: rb.bus.fare)
        elif sort_by == "Duration: Shortest":
            display_buses.sort(key=lambda rb: rb.bus.duration_minutes)
        elif sort_by == "Rating: Highest":
            display_buses.sort(key=lambda rb: -rb.bus.rating)

        # Render Table
        table_rows = []
        for rb in display_buses:
            table_rows.append({
                "Rank": f"#{rb.rank}",
                "Bus ID": rb.bus.bus_id,
                "Operator": rb.bus.operator_name,
                "Departure": rb.bus.departure_time,
                "Arrival": rb.bus.arrival_time,
                "Duration": rb.bus.duration_formatted,
                "Fare (₹)": f"₹{rb.bus.fare:.2f}",
                "Rating": f"★ {rb.bus.rating}",
                "Available Seats": rb.bus.available_seats,
                "Score": f"{rb.composite_score:.4f}",
            })

        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

        st.divider()

        # Simulated Seat Selection & Booking Section
        st.markdown("#### 💺 Interactive Seat Selection & Simulated Booking")

        bus_selector_options = {f"{rb.bus.operator_name} ({rb.bus.bus_id}) - ₹{rb.bus.fare:.2f}": rb.bus for rb in result.ranked_buses}
        chosen_label = st.selectbox("Select Bus to Reserve Seats", options=list(bus_selector_options.keys()))
        selected_bus = bus_selector_options[chosen_label]

        # Generate seat layout
        seat_layout = BOOKING_ENGINE.generate_seat_layout(selected_bus)
        avail_seat_numbers = [s.seat_number for s in seat_layout if s.is_available]

        col_seat_map, col_book_form = st.columns([1.2, 1])

        with col_seat_map:
            st.markdown(f"**Simulated Seat Map for {selected_bus.operator_name}:**")
            st.caption(f"Available Seats: {selected_bus.available_seats} | Occupied: {len(seat_layout) - selected_bus.available_seats}")

            # Visual representation
            seats_html = "<div style='background: #111827; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px; margin-bottom: 12px;'>"
            for s in seat_layout:
                if s.is_available:
                    seats_html += f"<span class='seat-badge-avail'>{escape_html(s.seat_number)}</span>"
                else:
                    seats_html += f"<span class='seat-badge-booked'>{escape_html(s.seat_number)}</span>"
            seats_html += "</div>"
            st.markdown(seats_html, unsafe_allow_html=True)

        with col_book_form:
            st.markdown("**Passenger Details (Simulation Mode):**")
            p_name = st.text_input("Passenger Full Name", placeholder="e.g. Demo Passenger")
            p_email = st.text_input("Passenger Email", placeholder="demo@example.invalid")
            p_phone = st.text_input("Mobile Number", placeholder="0000000000")

            picked_seats = st.multiselect(
                "Choose Seat Numbers",
                options=avail_seat_numbers,
                default=[avail_seat_numbers[0]] if avail_seat_numbers else [],
                max_selections=result.request.passengers,
            )

            total_cost = round(selected_bus.fare * len(picked_seats), 2)
            st.write(f"Total Simulated Fare: **₹{total_cost:.2f}** ({len(picked_seats)} seats)")

            if st.button("🎟️ Issue Simulated Booking Confirmation", type="primary", use_container_width=True):
                if not picked_seats:
                    st.error("Please select at least one available seat to simulate booking.")
                elif not p_name.strip():
                    st.error("Please enter a passenger name.")
                else:
                    try:
                        conf = BOOKING_ENGINE.create_booking(
                            execution_id=result.execution_id,
                            bus=selected_bus,
                            passenger_name=p_name,
                            passenger_email=p_email,
                            passenger_phone=p_phone,
                            selected_seats=picked_seats,
                            journey_date=result.request.journey_date,
                        )
                    except ValueError as booking_error:
                        st.error(str(booking_error))
                    else:
                        st.session_state.latest_booking_confirmation = conf
                        st.success(f"Simulated Booking Confirmed! PNR Reference: {conf.pnr_number}")

        # Render Latest Booking Confirmation
        if st.session_state.latest_booking_confirmation:
            b_conf = st.session_state.latest_booking_confirmation
            st.markdown(
                f"""
                <div class="confirmation-pass">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; margin-bottom: 12px;">
                        <div>
                            <span style="background: rgba(16, 185, 129, 0.2); color: #34D399; font-weight: 700; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">SIMULATED RESERVATION</span>
                            <div style="font-size: 1.3rem; font-weight: 800; color: #FFFFFF; margin-top: 4px;">PNR: {escape_html(b_conf.pnr_number)}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 0.75rem; color: #94A3B8;">CONFIRMATION REF</div>
                            <code style="color: #60A5FA;">{escape_html(b_conf.confirmation_reference)}</code>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; font-size: 0.85rem;">
                        <div><strong>Passenger:</strong> {escape_html(b_conf.booking_request.passenger_name)}</div>
                        <div><strong>Route:</strong> {escape_html(b_conf.bus.source)} → {escape_html(b_conf.bus.destination)}</div>
                        <div><strong>Travel Date:</strong> {escape_html(b_conf.booking_request.journey_date)}</div>
                        <div><strong>Operator:</strong> {escape_html(b_conf.bus.operator_name)}</div>
                        <div><strong>Seats:</strong> {escape_html(', '.join(b_conf.booking_request.selected_seats))}</div>
                        <div><strong>Total Fare:</strong> ₹{b_conf.booking_request.total_fare:.2f}</div>
                    </div>
                    <div style="font-size: 0.72rem; color: #F59E0B; margin-top: 14px; border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 8px;">
                        {escape_html(b_conf.disclaimer)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Historical Simulated Bookings
        with st.expander("📜 View Simulated Booking History"):
            hist = BOOKING_ENGINE.get_all_bookings()
            if hist:
                st.dataframe(pd.DataFrame(hist), use_container_width=True, hide_index=True)
            else:
                st.info("No bookings recorded yet.")
    elif result and not result.buses_found:
        st.info("No simulated buses are available for this route. Please choose another supported route.")
    elif result:
        st.info("No buses match the selected fare, passenger, or rating filters.")
    else:
        st.info("Execute a search using the sidebar to view candidate buses and interactive booking.")

# -----------------------------------------------------------------------------
# TAB 4: Incident Center
# -----------------------------------------------------------------------------
with tab_incident:
    st.markdown("### 🛡️ Autonomic Incident Management Center")
    st.markdown(
        "<div style='font-size: 0.85rem; color: #94A3B8; margin-bottom: 16px;'>"
        "Tracks operational failures, failure classification, automated recovery attempts, and incident resolution status."
        "</div>",
        unsafe_allow_html=True,
    )

    inc_metrics = INCIDENT_MANAGER.get_summary()
    i1, i2, i3, i4 = st.columns(4)
    i1.metric("Total Incidents", inc_metrics["total_incidents"])
    i2.metric("Resolved Incidents", inc_metrics["resolved_incidents"])
    i3.metric("Unresolved Outages", inc_metrics["unresolved_incidents"])
    i4.metric("Resolution Rate", f"{inc_metrics['resolution_rate_percent']}%")

    st.markdown("#### Structured Incident Registry")
    all_incidents = INCIDENT_MANAGER.get_incidents()

    if all_incidents:
        inc_rows = []
        for inc in reversed(all_incidents):
            inc_rows.append({
                "Incident ID": inc.incident_id,
                "Timestamp": inc.timestamp,
                "Category": inc.failure_category.value,
                "Recoverable": "Yes" if inc.is_recoverable else "No",
                "Retries": inc.retry_attempts,
                "Retry Event History": "\n".join(
                    f"Attempt {event.get('metadata', {}).get('attempt')}: {event.get('message', '')}"
                    for event in inc.details.get("retry_events", [])
                ),
                "Recovery Action": inc.recovery_action or "None",
                "Final Status": inc.final_status,
                "Error Message": inc.error_message,
            })
        st.dataframe(pd.DataFrame(inc_rows), use_container_width=True, hide_index=True)
        for inc in reversed(all_incidents):
            retry_events = inc.details.get("retry_events", [])
            if retry_events:
                with st.expander(
                    f"Retry History — {inc.incident_id} ({inc.retry_attempts} retries)"
                ):
                    st.caption(
                        f"Status: {inc.final_status} | Recovery: {inc.recovery_action or 'None'}"
                    )
                    for event in retry_events:
                        metadata = event.get("metadata", {})
                        st.text(
                            f"Attempt {metadata.get('attempt')}/{metadata.get('max_retries')} "
                            f"| {event.get('event_type')}: {event.get('message', '')}"
                        )
    else:
        st.info("Zero operational incidents detected. The system has operated within normal parameters.")

# -----------------------------------------------------------------------------
# TAB 5: Reports & Audit Center
# -----------------------------------------------------------------------------
with tab_reports:
    st.markdown("### 📁 Operational Compliance & Audit Reports Center")
    st.markdown(
        "<div style='font-size: 0.85rem; color: #94A3B8; margin-bottom: 16px;'>"
        "Download structured compliance artifacts, audit logs, and operational health summaries."
        "</div>",
        unsafe_allow_html=True,
    )

    if result and result.report_paths:
        csv_file = Path(result.report_paths.get("csv", ""))
        json_file = Path(result.report_paths.get("json", ""))

        d1, d2 = st.columns(2)
        with d1:
            st.markdown(
                """
                <div class="report-card">
                    <div class="report-card-title">📊 Tabular CSV Execution Report</div>
                    <div class="report-card-desc">
                        Contains complete journey specs, timings, fares, MCDA composite scores, and explainability justifications.
                    </div>
                """,
                unsafe_allow_html=True,
            )
            if csv_file.exists():
                with open(csv_file, "r", encoding="utf-8") as f:
                    csv_raw = f.read()
                st.download_button("📥 Download CSV Report", data=csv_raw, file_name=csv_file.name, mime="text/csv", use_container_width=True)
                with st.expander("Preview CSV"):
                    st.code(csv_raw[:400] + "\n...", language="csv")
            st.markdown("</div>", unsafe_allow_html=True)

        with d2:
            st.markdown(
                """
                <div class="report-card">
                    <div class="report-card-title">📄 Hierarchical JSON Audit Report</div>
                    <div class="report-card-desc">
                        Complete execution trace including full search requests, retry histories, self-healing remediation logs, and telemetry metadata.
                    </div>
                """,
                unsafe_allow_html=True,
            )
            if json_file.exists():
                with open(json_file, "r", encoding="utf-8") as f:
                    json_raw = f.read()
                st.download_button("📥 Download JSON Report", data=json_raw, file_name=json_file.name, mime="application/json", use_container_width=True)
                with st.expander("Preview JSON"):
                    st.json(json.loads(json_raw))
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Execute a workflow orchestration to generate and download compliance reports.")

    st.divider()

    # Health Probe Monitor Log Viewer
    with st.expander("🔍 View System Health Monitoring Probe Logs (scripts/monitor.sh)"):
        monitor_log_file = Path("logs/monitor_health.log")
        if monitor_log_file.exists():
            with open(monitor_log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            st.code("".join(lines[-20:]), language="log")
        else:
            st.info("No monitor probe entries recorded yet. Run `bash scripts/monitor.sh` to generate probe records.")
