#!/usr/bin/env python3
import argparse
import sys
import config
import downloader
import profiles
import spotify_client


def _resolve_profile(name_or_id):
    profs = profiles.load_profiles()
    if name_or_id in profs:
        return profs[name_or_id]
    for p in profs.values():
        if p["name"].lower() == name_or_id.lower():
            return p
    return None


def main():
    parser = argparse.ArgumentParser(description="em tee vee - music video downloader")
    parser.add_argument("--profile", help="profile name or id to sync (default: all connected)")
    parser.add_argument("--list", action="store_true", help="list profiles and exit")
    parser.add_argument("--limit", type=int, help="max number of songs per profile")
    parser.add_argument("--serve", action="store_true", help="start the web player after downloading")
    args = parser.parse_args()

    profs = profiles.load_profiles()

    if args.list:
        if not profs:
            print("No profiles yet. Create one in the web UI at /.")
        for p in profs.values():
            state = "connected" if profiles.is_authed(p["id"]) else "NOT connected"
            print(f"  {p['id']}  {p['name']}  ({state})")
        return

    if args.profile:
        profile = _resolve_profile(args.profile)
        if not profile:
            print(f"No profile matching '{args.profile}'", file=sys.stderr)
            sys.exit(1)
        targets = [profile["id"]]
    else:
        targets = [pid for pid in profs if profiles.is_authed(pid)]

    if not targets:
        print("No connected profiles. Connect Spotify in the web UI first.", file=sys.stderr)
        sys.exit(1)

    to_download = {}
    for pid in targets:
        name = profs[pid]["name"]
        print(f"Fetching liked songs for {name}...")
        try:
            songs = spotify_client.fetch_liked_songs(pid, limit=args.limit)
        except Exception as e:
            print(f"  Error for {name}: {e}", file=sys.stderr)
            continue
        downloader.save_songs(songs, pid)
        for s in songs:
            to_download[downloader.song_key(s)] = s
        print(f"  {len(songs)} songs")

    songs = list(to_download.values())
    print(f"\nDownloading videos for {len(songs)} unique songs...")

    def on_progress(current, total, song):
        print(f"  [{current}/{total}] {song['artist']} - {song['title']}")

    results = downloader.download_all(songs, progress_callback=on_progress)
    print(f"\nDone: {len(results['success'])} downloaded, {len(results['failed'])} failed")
    for err in results["failed"]:
        print(f"  FAILED: {err['song']['artist']} - {err['song']['title']}: {err['error']}",
              file=sys.stderr)

    if args.serve:
        from app import app
        print(f"\nStarting web player on http://localhost:{config.PORT}")
        app.run(host="0.0.0.0", port=config.PORT)


if __name__ == "__main__":
    main()
