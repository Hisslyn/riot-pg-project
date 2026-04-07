"""
Riot Games → PostgreSQL sync tool.

Usage examples:
  # Sync a player's LoL data
  python main.py lol --name "PlayerName" --tag NA1 --region na1

  # Sync TFT data
  python main.py tft --name "PlayerName" --tag NA1 --region na1

  # Sync Valorant data
  python main.py val --name "PlayerName" --tag NA1 --region na1 --val-region na

  # Sync all three games
  python main.py all --name "PlayerName" --tag NA1 --region na1

  # Only initialize/migrate the database (no API calls)
  python main.py init-db
"""

import argparse
import sys

from database.connection import init_db, SessionLocal
from pipeline.sync import sync_lol_player, sync_tft_player, sync_val_player


def main():
    parser = argparse.ArgumentParser(
        description="Riot Games API → PostgreSQL sync tool"
    )
    parser.add_argument(
        "command",
        choices=["lol", "tft", "val", "all", "init-db"],
        help="Which game to sync, or 'init-db' to create tables only.",
    )
    parser.add_argument("--name",    help="Riot ID game name (e.g. PlayerName)")
    parser.add_argument("--tag",     help="Riot ID tag line (e.g. NA1)")
    parser.add_argument("--region",  default="na1", help="Platform region (default: na1)")
    parser.add_argument(
        "--val-region",
        default="na",
        help="Valorant region code (na, eu, ap, kr) — separate from LoL/TFT region",
    )
    parser.add_argument(
        "--matches",
        type=int,
        default=10,
        help="Number of recent matches to fetch (default: 10)",
    )
    parser.add_argument(
        "--refresh-key",
        action="store_true",
        help="Refresh the Riot API key via browser automation before syncing",
    )
    args = parser.parse_args()

    if args.refresh_key:
        from scripts.refresh_api_key import refresh_key
        refresh_key()
        # Reload the updated key into the config module
        import importlib, config
        importlib.reload(config)

    # Always make sure tables exist
    init_db()

    if args.command == "init-db":
        print("Database initialised. Exiting.")
        return

    # Validate required args for data commands
    if not args.name or not args.tag:
        print("❌  --name and --tag are required for sync commands.")
        sys.exit(1)

    session = SessionLocal()
    try:
        if args.command == "lol":
            print(f"\n🎮 Syncing League of Legends data for {args.name}#{args.tag}...")
            sync_lol_player(session, args.name, args.tag, args.region, args.matches)

        elif args.command == "tft":
            print(f"\n🎮 Syncing TFT data for {args.name}#{args.tag}...")
            sync_tft_player(session, args.name, args.tag, args.region, args.matches)

        elif args.command == "val":
            print(f"\n🎮 Syncing Valorant data for {args.name}#{args.tag}...")
            sync_val_player(session, args.name, args.tag, args.val_region, args.matches)

        elif args.command == "all":
            print(f"\n🎮 Syncing ALL games for {args.name}#{args.tag}...")
            sync_lol_player(session, args.name, args.tag, args.region, args.matches)
            sync_tft_player(session, args.name, args.tag, args.region, args.matches)
            sync_val_player(session, args.name, args.tag, args.val_region, args.matches)

        print("\n✅ Sync complete!")

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error during sync: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
