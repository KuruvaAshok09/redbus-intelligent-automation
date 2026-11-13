"""
CLI Entrypoint for RedBus Intelligent Ticket Search and Automation System.
Allows executing full autonomics workflows directly from the command line.
Usage:
    python -m redbus_automation.main --source Bangalore --destination Hyderabad
"""

import argparse
import sys
from datetime import datetime, timedelta

from redbus_automation.config import CONFIG
from redbus_automation.models import SearchRequest, WorkflowStatus
from redbus_automation.orchestrator import AutomationOrchestrator


def parse_arguments() -> argparse.Namespace:
    """Parses command-line inputs for the automation engine."""
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    parser = argparse.ArgumentParser(
        prog="python -m redbus_automation.main",
        description="RedBus Intelligent Ticket Search and Automation CLI (Offline-First Enterprise Autonomics)",
        epilog=CONFIG.SIMULATION_DISCLAIMER,
    )

    parser.add_argument(
        "--source",
        type=str,
        default="Bangalore",
        help="Departure city (default: Bangalore)",
    )
    parser.add_argument(
        "--destination",
        type=str,
        default="Hyderabad",
        help="Arrival city (default: Hyderabad)",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=tomorrow_str,
        help=f"Journey date in YYYY-MM-DD (default: {tomorrow_str})",
    )
    parser.add_argument(
        "--passengers",
        type=int,
        default=1,
        help="Number of passengers (default: 1)",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=2500.0,
        help="Maximum fare budget in INR (default: 2500.0)",
    )
    parser.add_argument(
        "--operator",
        type=str,
        default=None,
        help="Optional preferred bus operator name",
    )
    parser.add_argument(
        "--min-rating",
        type=float,
        default=None,
        help="Optional minimum bus rating (e.g. 4.0)",
    )

    # Fault Injection Flags for Testing
    parser.add_argument(
        "--simulate-transient-failure",
        action="store_true",
        help="Inject transient service failure to test retry and self-healing",
    )
    parser.add_argument(
        "--simulate-corruption",
        action="store_true",
        help="Inject corrupted catalog error to test unrecoverable escalation",
    )
    parser.add_argument(
        "--force-empty",
        action="store_true",
        help="Force search engine to return zero buses",
    )

    return parser.parse_args()


def main() -> int:
    """CLI execution workflow returning process exit codes."""
    args = parse_arguments()

    print("=" * 80)
    print(" REDBUS INTELLIGENT TICKET SEARCH & AUTOMATION SYSTEM")
    print(f" [OFFLINE-FIRST AUTONOMICS DEMONSTRATION - {CONFIG.SIMULATION_DISCLAIMER}]")
    print("=" * 80)

    request = SearchRequest(
        source=args.source,
        destination=args.destination,
        journey_date=args.date,
        passengers=args.passengers,
        max_budget=args.budget,
        preferred_operator=args.operator,
        min_rating=args.min_rating,
    )

    faults = {
        "simulate_transient_failure": args.simulate_transient_failure,
        "simulate_corruption": args.simulate_corruption,
        "force_empty": args.force_empty,
    }

    orchestrator = AutomationOrchestrator()
    result = orchestrator.run_workflow(request, fault_injection=faults)

    # Display Execution Summary
    print("\n--- WORKFLOW EXECUTION SUMMARY ---")
    print(f"Execution ID     : {result.execution_id}")
    print(f"Status           : {result.status.value}")
    print(f"Execution Time   : {result.execution_duration_sec:.3f} seconds")
    print(f"Buses Evaluated  : {len(result.buses_found)} found, {len(result.ranked_buses)} ranked")
    print(f"Retry Attempts   : {len(result.retry_history)}")
    print(f"Recovery Actions : {len(result.recovery_history)}")

    if result.retry_history:
        print("\n--- RETRY TELEMETRY ---")
        for r in result.retry_history:
            print(f"  [Attempt {r.attempt_number}] Delay: {r.delay_seconds:.3f}s | Target: {r.target_function} | Cause: {r.error_message}")

    if result.recovery_history:
        print("\n--- SELF-HEALING RECOVERY ACTIONS ---")
        for rec in result.recovery_history:
            status_tag = "SUCCESS" if rec.successful else "FAILED"
            print(f"  [{rec.action_id}] Strategy: {rec.strategy_used} ({status_tag})")
            print(f"    Details: {rec.details}")

    if result.status in (WorkflowStatus.SUCCESS, WorkflowStatus.RECOVERED):
        if result.recommended_bus:
            top = result.recommended_bus
            print("\n" + "=" * 80)
            print(f" ★ TOP RECOMMENDED BUS: {top.bus.operator_name} ({top.bus.bus_id})")
            print(f"   Fare        : ₹{top.bus.fare:.2f}")
            print(f"   Departure   : {top.bus.departure_time} -> Arrival: {top.bus.arrival_time} ({top.bus.duration_formatted})")
            print(f"   Type        : {top.bus.bus_type}")
            print(f"   Rating      : {top.bus.rating} / 5.0 ★")
            print(f"   Available   : {top.bus.available_seats} seats")
            print(f"   Score       : {top.composite_score:.4f}")
            print(f"   Reason      : {top.recommendation_reason}")
            print("=" * 80)

        if result.ranked_buses:
            print("\n--- ALL RANKED OPTIONS ---")
            print(f"{'Rank':<5} {'Bus ID':<20} {'Operator':<24} {'Fare':<9} {'Dep-Arr':<14} {'Rating':<8} {'Seats':<6} {'Score':<6}")
            print("-" * 96)
            for rb in result.ranked_buses:
                dep_arr = f"{rb.bus.departure_time}-{rb.bus.arrival_time}"
                print(
                    f"{rb.rank:<5} {rb.bus.bus_id:<20} {rb.bus.operator_name[:22]:<24} "
                    f"₹{rb.bus.fare:<8.1f} {dep_arr:<14} {rb.bus.rating:<8.1f} {rb.bus.available_seats:<6} {rb.composite_score:<6.3f}"
                )

        if result.report_paths:
            print("\n--- GENERATED ARTIFACTS ---")
            print(f"JSON Report : {result.report_paths.get('json', 'N/A')}")
            print(f"CSV Report  : {result.report_paths.get('csv', 'N/A')}")

        return 0

    else:
        print("\n" + "!" * 80)
        print(f" WORKFLOW FAILED: {result.error_message}")
        print("!" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
