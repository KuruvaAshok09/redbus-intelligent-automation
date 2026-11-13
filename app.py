"""
RedBus Intelligent Ticket Search and Automation System.
Enterprise SaaS Operations Console & Autonomics Dashboard.

Frontend UI/UX Redesign: High-end enterprise aesthetic with dark navy/charcoal theme,
crisp typography, observable telemetry cards, and explainable decision interfaces.
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
    /* Google Inter / System Font Stack */
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

    /* Global Body & Container Styles */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: var(--bg-main) !important;
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--text-primary) !important;
    }

    [data-testid="stHeader"] {
        background: transparent !important;
    }

    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 96% !important;
    }

    /* Hide Default Chrome Elements */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* Custom Scrollbars */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #0B0F17;
    }
    ::-webkit-scrollbar-thumb {
        background: #1E293B;
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #334155;
    }

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

    /* Sidebar Restyling */
    [data-testid="stSidebar"] {
        background-color: #0D131F !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
    }

    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #F8FAFC !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.03em !important;
        text-transform: uppercase !important;
    }

    .sidebar-section-card {
        background: #111827;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 14px;
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

    div.stButton > button[kind="secondary"]:hover {
        background: #334155 !important;
        color: #FFFFFF !important;
    }

    /* Enterprise Metric Card */
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

    /* Hero Recommendation Card */
    .hero-recommendation-card {
        background: linear-gradient(145deg, #111827 0%, #0D1424 100%);
        border: 1px solid rgba(59, 130, 246, 0.35);
        border-radius: 14px;
        padding: 24px;
        margin-top: 12px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
        position: relative;
    }

    .hero-top-badge {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: #FFFFFF;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        padding: 4px 10px;
        border-radius: 20px;
        display: inline-block;
        margin-bottom: 12px;
    }

    .hero-operator-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.02em;
        margin-bottom: 4px;
    }

    .hero-bus-spec {
        font-size: 0.85rem;
        color: var(--text-secondary);
        margin-bottom: 16px;
    }

    .timeline-container {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 10px;
        padding: 14px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 18px;
    }

    .timeline-time {
        font-size: 1.25rem;
        font-weight: 700;
        color: #FFFFFF;
        font-family: 'JetBrains Mono', monospace;
    }

    .timeline-city {
        font-size: 0.8rem;
        color: var(--text-secondary);
    }

    .timeline-divider {
        flex-grow: 1;
        margin: 0 20px;
        text-align: center;
        position: relative;
    }

    .timeline-duration-badge {
        background: #1E293B;
        color: #93C5FD;
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 12px;
        padding: 3px 12px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }

    .explainability-box {
        background: rgba(99, 102, 241, 0.08);
        border-left: 3px solid #6366F1;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin-top: 14px;
    }

    .explainability-title {
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #A5B4FC;
        margin-bottom: 4px;
    }

    .explainability-body {
        font-size: 0.85rem;
        color: #E2E8F0;
        line-height: 1.45;
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

    div[data-baseweb="tab"]:hover {
        color: #FFFFFF !important;
        background: rgba(255, 255, 255, 0.04) !important;
    }

    div[aria-selected="true"] {
        background: #1E293B !important;
        color: #60A5FA !important;
        border-bottom: 2px solid #3B82F6 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25) !important;
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

    /* Terminal-styled Logs Container */
    .terminal-container {
        background: #090D14;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 14px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: #CBD5E1;
        max-height: 480px;
        overflow-y: auto;
    }

    .log-line {
        padding: 3px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }

    .log-badge {
        font-size: 0.68rem;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 3px;
        margin-right: 6px;
    }

    .badge-info { background: rgba(59, 130, 246, 0.2); color: #60A5FA; }
    .badge-warn { background: rgba(245, 158, 11, 0.2); color: #FBBF24; }
    .badge-err { background: rgba(239, 68, 68, 0.2); color: #F87171; }
    .badge-crit { background: rgba(217, 70, 239, 0.25); color: #E879F9; }

    /* Report Download Card */
    .report-card {
        background: #111827;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 18px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .report-card-title {
        font-size: 1.0rem;
        font-weight: 700;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .report-card-desc {
        font-size: 0.8rem;
        color: var(--text-secondary);
        margin: 6px 0 14px 0;
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

# -----------------------------------------------------------------------------
# 4. Top Navigation Bar & Operational Header
# -----------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="top-navbar">
        <div>
            <div class="brand-title">
                <span>⚡ REDBUS INTELLIGENT AUTOMATION</span>
                <span class="brand-badge">AUTONOMICS OS</span>
            </div>
            <div class="brand-subtitle">
                Offline-First Enterprise Workflow Orchestration, Self-Healing Resilience & MCDA Decision Analysis
            </div>
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
            <div class="pill-badge pill-online">
                <span style="font-size: 10px;">●</span> ENGINE ACTIVE (OFFLINE NODE)
            </div>
            <div class="pill-badge pill-simulated">
                ⚠️ SIMULATED DATA DEMO
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
    city_options = ["Bangalore", "Hyderabad", "Chennai", "Pune", "Delhi", "Mumbai", "Jaipur", "Kolkata"]

    source_city = st.selectbox("Origin City", options=city_options, index=0)
    dest_city = st.selectbox(
        "Destination City",
        options=city_options,
        index=0 if source_city != "Hyderabad" else 1,
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
        st.caption("Simulate controlled faults to test automated recovery:")
        sim_transient = st.checkbox("Simulate Gateway 503 Timeout (Retry/Mirror)", value=False)
        sim_corruption = st.checkbox("Simulate Catalog Corruption (Seed Restore)", value=False)
        sim_empty = st.checkbox("Simulate Empty Search Results", value=False)
        sim_report_fail = st.checkbox("Simulate Report Filesystem Lock", value=False)
        sim_repeated_fail = st.checkbox("Simulate Repeated Unrecoverable Outage", value=False)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Primary Workflow Trigger
    execute_clicked = st.button("🚀 Search & Orchestrate Workflow", type="primary", use_container_width=True)

    # Secondary Actions
    if st.button("🔄 Reset Telemetry Counters", use_container_width=True):
        MONITOR.reset_metrics()
        st.toast("Telemetry and KPI counters reset to baseline.", icon="📊")
        st.rerun()

    st.markdown(
        """
        <div style="font-size: 0.72rem; color: #64748B; text-align: center; margin-top: 24px;">
            RedBus Intelligent Automation Engine<br>
            Offline Enterprise Evaluation Build v1.0.0
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

    with st.spinner("Executing Autonomic Pipeline: Validation → Bounded Retry → MCDA Ranking → Reporting..."):
        orchestrator = AutomationOrchestrator()
        result = orchestrator.run_workflow(request, fault_injection=faults)
        st.session_state.last_result = result

result = st.session_state.last_result

# -----------------------------------------------------------------------------
# 7. Main Dashboard Tabs
# -----------------------------------------------------------------------------
tab_overview, tab_results, tab_monitoring, tab_recovery, tab_logs, tab_reports = st.tabs([
    "📊 Executive Overview",
    "🚌 Ranked Bus Results",
    "📈 Workflow Monitoring",
    "🛡️ Incident & Recovery",
    "📜 Telemetry Logs",
    "📁 Audit Artifacts",
])

# -----------------------------------------------------------------------------
# TAB 1: Executive Overview (Default Landing Page)
# -----------------------------------------------------------------------------
with tab_overview:
    # Top KPI Metrics Row
    metrics = MONITOR.get_metrics()
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(
            f"""
            <div class="saas-kpi-card">
                <div class="kpi-label">Total Orchestrations</div>
                <div class="kpi-value">{metrics['total_executions']}</div>
                <div class="kpi-subtext">Cumulative workflow runs</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="saas-kpi-card">
                <div class="kpi-label">Success Rate</div>
                <div class="kpi-value" style="color: #34D399;">{metrics['success_rate_percent']}%</div>
                <div class="kpi-subtext">{metrics['successful_executions']} successful runs</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="saas-kpi-card">
                <div class="kpi-label">Self-Healed Runs</div>
                <div class="kpi-value" style="color: #FBBF24;">{metrics['recovered_executions']}</div>
                <div class="kpi-subtext">{metrics['total_recovery_actions']} automated remedies</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="saas-kpi-card">
                <div class="kpi-label">Average Latency</div>
                <div class="kpi-value">{metrics['average_duration_sec']}s</div>
                <div class="kpi-subtext">Rolling mean duration</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c5:
        st.markdown(
            f"""
            <div class="saas-kpi-card">
                <div class="kpi-label">System Retries</div>
                <div class="kpi-value" style="color: #60A5FA;">{metrics['total_retry_attempts']}</div>
                <div class="kpi-subtext">Bounded backoff attempts</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    if result is None:
        st.markdown(
            """
            <div style="background: #111827; border: 1px dashed rgba(255,255,255,0.12); border-radius: 12px; padding: 48px 24px; text-align: center;">
                <div style="font-size: 2.2rem; margin-bottom: 12px;">🧭</div>
                <div style="font-size: 1.15rem; font-weight: 700; color: #FFFFFF; margin-bottom: 6px;">
                    Ready for Workflow Orchestration
                </div>
                <div style="font-size: 0.85rem; color: #94A3B8; max-width: 520px; margin: 0 auto 18px auto;">
                    Select origin, destination, and budget constraints in the left sidebar, then click 
                    <strong style="color: #60A5FA;">"Search & Orchestrate Workflow"</strong> to execute validation, search, 
                    MCDA multi-criteria ranking, and report generation.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Operational Status Banner
        if result.status == WorkflowStatus.SUCCESS:
            banner_class = "status-banner-success"
            banner_icon = "✅"
            status_desc = f"Completed successfully in {result.execution_duration_sec:.3f}s with 0 unhandled exceptions."
        elif result.status == WorkflowStatus.RECOVERED:
            banner_class = "status-banner-recovered"
            banner_icon = "🛡️"
            status_desc = f"Recovered through automated self-healing remediation in {result.execution_duration_sec:.3f}s."
        else:
            banner_class = "status-banner-failed"
            banner_icon = "❌"
            status_desc = f"Workflow halted with status FAILED: {result.error_message}"

        st.markdown(
            f"""
            <div class="status-banner {banner_class}">
                <div>
                    <strong>{banner_icon} Execution ID:</strong> <code>{result.execution_id}</code> &nbsp;•&nbsp; 
                    <strong>Status:</strong> {result.status.value}
                    <div style="font-size: 0.82rem; margin-top: 2px;">{status_desc}</div>
                </div>
                <div style="font-size: 0.85rem; font-weight: 600;">
                    Duration: {result.execution_duration_sec:.3f}s
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Hero Recommended Bus Card
        if result.recommended_bus:
            top = result.recommended_bus
            dep_city = result.request.source
            arr_city = result.request.destination

            st.markdown(
                f"""
                <div class="hero-recommendation-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div class="hero-top-badge">🏆 TOP RECOMMENDED OPTION (RANK #1)</div>
                            <div class="hero-operator-title">{top.bus.operator_name}</div>
                            <div class="hero-bus-spec">Bus ID: <code>{top.bus.bus_id}</code> &nbsp;•&nbsp; Category: {top.bus.bus_type}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase; font-weight: 600;">Optimal Fare</div>
                            <div style="font-size: 2.1rem; font-weight: 800; color: #FFFFFF; font-family: 'JetBrains Mono', monospace;">
                                ₹{top.bus.fare:.2f}
                            </div>
                            <div style="font-size: 0.75rem; color: #10B981; font-weight: 600;">Composite MCDA Score: {top.composite_score:.4f}</div>
                        </div>
                    </div>

                    <!-- Journey Timeline Block -->
                    <div class="timeline-container">
                        <div>
                            <div class="timeline-time">{top.bus.departure_time}</div>
                            <div class="timeline-city">{dep_city}</div>
                        </div>
                        <div class="timeline-divider">
                            <div class="timeline-duration-badge">⏱️ {top.bus.duration_formatted}</div>
                            <div style="border-top: 1px dashed rgba(255,255,255,0.2); margin-top: -10px;"></div>
                        </div>
                        <div style="text-align: right;">
                            <div class="timeline-time">{top.bus.arrival_time}</div>
                            <div class="timeline-city">{arr_city}</div>
                        </div>
                    </div>

                    <!-- Performance Attributes Grid -->
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 8px;">
                        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 10px; text-align: center;">
                            <div style="font-size: 0.7rem; color: #94A3B8; text-transform: uppercase;">Rating</div>
                            <div style="font-size: 1.1rem; font-weight: 700; color: #FBBF24;">★ {top.bus.rating} / 5.0</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 10px; text-align: center;">
                            <div style="font-size: 0.7rem; color: #94A3B8; text-transform: uppercase;">Availability</div>
                            <div style="font-size: 1.1rem; font-weight: 700; color: #34D399;">{top.bus.available_seats} Seats</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 10px; text-align: center;">
                            <div style="font-size: 0.7rem; color: #94A3B8; text-transform: uppercase;">Retries Triggered</div>
                            <div style="font-size: 1.1rem; font-weight: 700; color: #60A5FA;">{len(result.retry_history)}</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 10px; text-align: center;">
                            <div style="font-size: 0.7rem; color: #94A3B8; text-transform: uppercase;">Self-Healing Actions</div>
                            <div style="font-size: 1.1rem; font-weight: 700; color: #C084FC;">{len(result.recovery_history)}</div>
                        </div>
                    </div>

                    <!-- Explainability Callout -->
                    <div class="explainability-box">
                        <div class="explainability-title">💡 Autonomics Decision Explainability Engine</div>
                        <div class="explainability-body">{top.recommendation_reason}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.warning("No candidate bus satisfied the requested parameters and budget limits.")

# -----------------------------------------------------------------------------
# TAB 2: Ranked Bus Results
# -----------------------------------------------------------------------------
with tab_results:
    if result and result.ranked_buses:
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                <div style="font-size: 1.05rem; font-weight: 700; color: #FFFFFF;">
                    Evaluated Schedules ({len(result.ranked_buses)} of {len(result.buses_found)} qualifying options)
                </div>
                <div style="font-size: 0.8rem; color: #94A3B8;">
                    Ranked via Multi-Criteria Decision Analysis (Fare: 40%, Duration: 25%, Rating: 25%, Seats: 10%)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        table_rows = []
        for rb in result.ranked_buses:
            table_rows.append({
                "Rank": f"#{rb.rank}",
                "Bus ID": rb.bus.bus_id,
                "Operator": rb.bus.operator_name,
                "Type": rb.bus.bus_type,
                "Departure": rb.bus.departure_time,
                "Arrival": rb.bus.arrival_time,
                "Duration": rb.bus.duration_formatted,
                "Fare (₹)": f"₹{rb.bus.fare:.2f}",
                "Rating": f"★ {rb.bus.rating}",
                "Seats": rb.bus.available_seats,
                "Score": f"{rb.composite_score:.4f}",
                "Decision Explainability": rb.recommendation_reason,
            })

        df = pd.DataFrame(table_rows)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Rank": st.column_config.TextColumn("Rank", width="small"),
                "Score": st.column_config.TextColumn("MCDA Score", width="small"),
                "Fare (₹)": st.column_config.TextColumn("Fare", width="small"),
                "Rating": st.column_config.TextColumn("Rating", width="small"),
            },
        )
    elif result and not result.ranked_buses:
        st.warning("Zero buses matched the applied search criteria.")
    else:
        st.info("Execute a search using the sidebar to view ranked candidate buses.")

# -----------------------------------------------------------------------------
# TAB 3: Workflow Monitoring
# -----------------------------------------------------------------------------
with tab_monitoring:
    st.markdown("### 📈 Real-Time Engine Telemetry & System Observability")
    st.markdown(
        "<div style='font-size: 0.85rem; color: #94A3B8; margin-bottom: 18px;'>Continuous health counters tracked by AutomationMonitor service:</div>",
        unsafe_allow_html=True,
    )

    m = MONITOR.get_metrics()

    t_col1, t_col2 = st.columns(2)

    with t_col1:
        st.markdown(
            f"""
            <div style="background: #111827; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #60A5FA; text-transform: uppercase; margin-bottom: 14px;">
                    Execution Volume & Success Ratio
                </div>
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.06); padding: 8px 0;">
                    <span style="color: #94A3B8;">Total Lifecycle Runs:</span>
                    <strong style="color: #FFFFFF;">{m['total_executions']}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.06); padding: 8px 0;">
                    <span style="color: #94A3B8;">Clean Successful Runs:</span>
                    <strong style="color: #10B981;">{m['successful_executions'] - m['recovered_executions']}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.06); padding: 8px 0;">
                    <span style="color: #94A3B8;">Self-Healed (Recovered):</span>
                    <strong style="color: #FBBF24;">{m['recovered_executions']}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 8px 0;">
                    <span style="color: #94A3B8;">Failed Executions:</span>
                    <strong style="color: #EF4444;">{m['failed_executions']}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with t_col2:
        st.markdown(
            f"""
            <div style="background: #111827; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #60A5FA; text-transform: uppercase; margin-bottom: 14px;">
                    Reliability & Latency Benchmarks
                </div>
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.06); padding: 8px 0;">
                    <span style="color: #94A3B8;">System Success Rate:</span>
                    <strong style="color: #10B981;">{m['success_rate_percent']}%</strong>
                </div>
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.06); padding: 8px 0;">
                    <span style="color: #94A3B8;">System Failure Rate:</span>
                    <strong style="color: #EF4444;">{m['failure_rate_percent']}%</strong>
                </div>
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.06); padding: 8px 0;">
                    <span style="color: #94A3B8;">Rolling Average Latency:</span>
                    <strong style="color: #FFFFFF;">{m['average_duration_sec']}s</strong>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 8px 0;">
                    <span style="color: #94A3B8;">Current Engine Status:</span>
                    <strong style="color: #60A5FA;">{m['current_execution_status']}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# -----------------------------------------------------------------------------
# TAB 4: Incident & Recovery
# -----------------------------------------------------------------------------
with tab_recovery:
    st.markdown("### 🛡️ Autonomic Resilience & Self-Healing Remediation")

    if result:
        rec_col1, rec_col2 = st.columns(2)

        with rec_col1:
            st.markdown(
                """
                <div style="font-size: 0.85rem; font-weight: 700; color: #60A5FA; text-transform: uppercase; margin-bottom: 10px;">
                    Bounded Retry History (Exponential Backoff)
                </div>
                """,
                unsafe_allow_html=True,
            )
            if result.retry_history:
                for r in result.retry_history:
                    st.markdown(
                        f"""
                        <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                            <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 700; color: #FBBF24;">
                                <span>Attempt #{r.attempt_number}</span>
                                <span>Delay: {r.delay_seconds:.3f}s</span>
                            </div>
                            <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 4px;">Target: <code>{r.target_function}</code></div>
                            <div style="font-size: 0.8rem; color: #E2E8F0; margin-top: 4px;"><em>Cause:</em> {r.error_message}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    """
                    <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 8px; padding: 16px; color: #34D399; font-size: 0.85rem;">
                        ✓ Zero retries required. Operation completed on primary invocation.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with rec_col2:
            st.markdown(
                """
                <div style="font-size: 0.85rem; font-weight: 700; color: #60A5FA; text-transform: uppercase; margin-bottom: 10px;">
                    Self-Healing Remediation Actions
                </div>
                """,
                unsafe_allow_html=True,
            )
            if result.recovery_history:
                for rec in result.recovery_history:
                    status_badge = "✅ SUCCESS" if rec.successful else "❌ FAILED"
                    badge_style = "color: #34D399;" if rec.successful else "color: #F87171;"
                    st.markdown(
                        f"""
                        <div style="background: #111827; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 14px; margin-bottom: 10px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight: 700; color: #FFFFFF; font-size: 0.85rem;">Action: <code>{rec.action_id}</code></span>
                                <span style="{badge_style} font-weight: 700; font-size: 0.75rem;">{status_badge}</span>
                            </div>
                            <div style="font-size: 0.75rem; color: #60A5FA; margin: 4px 0;">Strategy: <strong>{rec.strategy_used}</strong></div>
                            <div style="font-size: 0.8rem; color: #CBD5E1;">{rec.details}</div>
                            <div style="font-size: 0.7rem; color: #64748B; margin-top: 6px;">Logged at: {rec.timestamp}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    """
                    <div style="background: #111827; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 16px; color: #94A3B8; font-size: 0.85rem;">
                        No failure incidents detected. Self-healing engine standing by.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("Execute a workflow with fault injection enabled in the sidebar to observe incident recovery.")

# -----------------------------------------------------------------------------
# TAB 5: Telemetry Logs
# -----------------------------------------------------------------------------
with tab_logs:
    st.markdown("### 📜 Structured JSON Telemetry Logs")

    all_logs = LOGGER.get_logs()
    filter_active = st.checkbox("Filter logs to active execution only", value=True)

    if result and filter_active:
        logs_to_render = [log for log in all_logs if log.get("execution_id") == result.execution_id]
    else:
        logs_to_render = all_logs

    if logs_to_render:
        st.markdown('<div class="terminal-container">', unsafe_allow_html=True)
        log_html = ""
        for entry in reversed(logs_to_render[-40:]):
            sev = entry.get("severity", "INFO")
            badge_class = "badge-info"
            if sev == "WARNING": badge_class = "badge-warn"
            elif sev == "ERROR": badge_class = "badge-err"
            elif sev == "CRITICAL": badge_class = "badge-crit"

            ts = entry.get("timestamp", "").split("T")[-1][:12]
            exec_short = entry.get("execution_id", "").split("-")[-1]
            comp = entry.get("component", "")
            evt = entry.get("event_type", "")
            msg = entry.get("message", "")

            log_html += f"""
            <div class="log-line">
                <span style="color: #64748B;">[{ts}]</span>
                <span class="log-badge {badge_class}">{sev}</span>
                <span style="color: #60A5FA;">{comp}</span>
                <span style="color: #94A3B8;">({evt}):</span>
                <span style="color: #F1F5F9;">{msg}</span>
            </div>
            """
        st.markdown(log_html + "</div>", unsafe_allow_html=True)

        with st.expander("🔍 View Raw Structured JSON Payload"):
            st.json(logs_to_render[-15:])
    else:
        st.info("No telemetry logs recorded yet.")

# -----------------------------------------------------------------------------
# TAB 6: Audit Artifacts & Reports
# -----------------------------------------------------------------------------
with tab_reports:
    st.markdown("### 📁 Operational Compliance & Audit Artifacts")

    if result and result.report_paths:
        csv_file = Path(result.report_paths.get("csv", ""))
        json_file = Path(result.report_paths.get("json", ""))

        d_col1, d_col2 = st.columns(2)

        with d_col1:
            st.markdown(
                """
                <div class="report-card">
                    <div>
                        <div class="report-card-title">📊 Tabular CSV Report</div>
                        <div class="report-card-desc">
                            Standard CSV containing journey specs, timings, fares, MCDA composite scores, and explainability justifications for enterprise data warehouse ingestion.
                        </div>
                    </div>
                """,
                unsafe_allow_html=True,
            )
            if csv_file.exists():
                with open(csv_file, "r", encoding="utf-8") as f:
                    csv_raw = f.read()
                st.download_button(
                    label="📥 Download CSV Report",
                    data=csv_raw,
                    file_name=csv_file.name,
                    mime="text/csv",
                    use_container_width=True,
                )
                with st.expander("Preview CSV Contents"):
                    st.code(csv_raw[:500] + "\n...", language="csv")
            st.markdown("</div>", unsafe_allow_html=True)

        with d_col2:
            st.markdown(
                """
                <div class="report-card">
                    <div>
                        <div class="report-card-title">📄 Hierarchical JSON Report</div>
                        <div class="report-card-desc">
                            Complete auditable execution trace including full search requests, retry histories, self-healing remediation logs, and telemetry metadata.
                        </div>
                    </div>
                """,
                unsafe_allow_html=True,
            )
            if json_file.exists():
                with open(json_file, "r", encoding="utf-8") as f:
                    json_raw = f.read()
                st.download_button(
                    label="📥 Download JSON Report",
                    data=json_raw,
                    file_name=json_file.name,
                    mime="application/json",
                    use_container_width=True,
                )
                with st.expander("Preview JSON Payload"):
                    st.json(json.loads(json_raw))
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Execute a workflow orchestration to generate downloadable audit reports.")
