#!/usr/bin/env python3
"""Entry point for the Siva Job Bot.

Usage:
    python run.py                    # Normal mode
    python run.py --dry-run          # Simulate without applying
    python run.py --config path.yaml # Custom config path
    python run.py --stats            # Show dashboard only
    python run.py --export           # Export applications to CSV
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    parser = argparse.ArgumentParser(
        description="Siva Job Bot - AI-powered automated job application bot"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without actually submitting applications",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to configuration file (default: config/config.yaml)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show application dashboard and exit",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export applications to CSV and exit",
    )
    parser.add_argument(
        "--followup",
        type=int,
        metavar="DAYS",
        help="Show applications needing follow-up after N days",
    )

    args = parser.parse_args()

    # Stats-only mode
    if args.stats:
        from src.tracking.dashboard import print_dashboard
        from src.tracking.database import ApplicationDatabase
        import yaml

        with open(args.config, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        db = ApplicationDatabase(config["database"]["path"])
        print_dashboard(db)
        db.close()
        return

    # Export-only mode
    if args.export:
        from src.tracking.database import ApplicationDatabase
        import yaml

        with open(args.config, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        db = ApplicationDatabase(config["database"]["path"])
        path = db.export_csv()
        if path:
            print(f"Exported to: {path}")
        db.close()
        return

    # Follow-up mode
    if args.followup:
        from src.tracking.database import ApplicationDatabase
        import yaml

        with open(args.config, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        db = ApplicationDatabase(config["database"]["path"])
        followups = db.get_applications_needing_followup(args.followup)
        if followups:
            print(f"\nApplications needing follow-up ({args.followup}+ days):\n")
            for app in followups:
                print(f"  {app['job_title']} at {app['company']}")
                print(f"    Applied: {app['applied_at']}")
                print(f"    URL: {app['job_url']}\n")
        else:
            print("No applications need follow-up.")
        db.close()
        return

    # Main bot execution
    from src.main import JobBot

    bot = JobBot(config_path=args.config)
    bot.run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
