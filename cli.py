#!/usr/bin/env python3
import argparse
import sys
import config
import downloader
import spotify_client


def main():
    parser = argparse.ArgumentParser(description="em tee vee - music video downloader")
    parser.add_argument("--limit", type=int, help="max number of songs to process")
    parser.add_argument("--serve", action="store_true", help="start the web player after downloading")
    args = parser.parse_args()

    print("Fetching liked songs from Spotify...")
    try:
        songs = spotify_client.fetch_liked_songs(limit=args.limit)
    except Exception as e:
        print(f"Error fetching from Spotify: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(songs)} liked songs")

    def on_progress(current, total, song):
        print(f"  [{current}/{total}] {song['artist']} - {song['title']}")

    results = downloader.download_all(songs, progress_callback=on_progress)
    print(f"\nDone: {len(results['success'])} downloaded, {len(results['failed'])} failed")

    for err in results["failed"]:
        print(f"  FAILED: {err['song']['artist']} - {err['song']['title']}: {err['error']}", file=sys.stderr)

    if args.serve:
        from app import app
        print(f"\nStarting web player on http://localhost:{config.PORT}")
        app.run(host="0.0.0.0", port=config.PORT)


if __name__ == "__main__":
    main()
