"""CLI dashboard for displaying application statistics."""

from src.tracking.database import ApplicationDatabase
from src.utils.logger import log


def print_dashboard(db: ApplicationDatabase) -> None:
    """Display a CLI dashboard with application statistics."""
    stats = db.get_stats()

    print("\n" + "=" * 60)
    print("            SIVA JOB BOT - APPLICATION DASHBOARD")
    print("=" * 60)

    print(f"\n  Applications Today:    {stats.get('today_applied', 0)}")
    print(f"  Applications This Week:{stats.get('week_applied', 0)}")
    print(f"  Total Applications:    {stats.get('total_applied', 0)}")

    avg_score = stats.get("avg_ai_score")
    if avg_score is not None:
        print(f"  Average AI Score:      {avg_score:.2f}")

    ai_cost = stats.get("total_ai_cost", 0)
    if ai_cost > 0:
        print(f"  Total AI Cost:         ${ai_cost:.4f}")

    # By platform
    by_platform = stats.get("by_platform", {})
    if by_platform:
        print("\n  By Platform:")
        for platform, count in by_platform.items():
            print(f"    {platform:20s} {count}")

    # By status
    by_status = stats.get("by_status", {})
    if by_status:
        print("\n  By Status:")
        for status, count in by_status.items():
            print(f"    {status:20s} {count}")

    # Top companies
    top_companies = stats.get("top_companies", {})
    if top_companies:
        print("\n  Top Companies Applied To:")
        for company, count in list(top_companies.items())[:5]:
            print(f"    {company:30s} {count}")

    print("\n" + "=" * 60)


def print_session_summary(
    applied: int,
    skipped: int,
    failed: int,
    blacklisted: int,
    duration_minutes: float,
    ai_cost: float = 0.0,
) -> None:
    """Display end-of-session summary."""
    total = applied + skipped + failed + blacklisted

    print("\n" + "-" * 50)
    print("         SESSION SUMMARY")
    print("-" * 50)
    print(f"  Jobs Processed:     {total}")
    print(f"  Applied:            {applied}")
    print(f"  Skipped:            {skipped}")
    print(f"  Failed:             {failed}")
    print(f"  Blacklisted:        {blacklisted}")
    print(f"  Duration:           {duration_minutes:.1f} minutes")
    if ai_cost > 0:
        print(f"  AI Cost:            ${ai_cost:.4f}")
    print("-" * 50 + "\n")
