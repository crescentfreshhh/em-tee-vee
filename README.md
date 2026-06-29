# em tee vee

A family music-video jukebox. It pulls each person's **Spotify liked songs**,
downloads the matching music videos in the best available quality
(YouTube / Vimeo / Dailymotion / … via `yt-dlp`), and plays them MTV-style in a
shuffled web player you can install on Android smart tablets.

- **Multi-user** — each family member (mom, dad, kids) connects their own
  Spotify account. Liked songs from every profile feed one shared video library;
  a track liked by several people is only downloaded once.
- **Installable PWA** — "Add to Home Screen" on any Android tablet/TV and it
  launches fullscreen like a native app, pointed at your home server.
- **Library page** — see every song, whether a video is matched/downloaded, and
  manually pair a specific video URL with a song.

## Running with Docker

1. Create a Spotify app at https://developer.spotify.com/dashboard.
2. In the app settings, add a **Redirect URI** that matches `SPOTIPY_REDIRECT_URI`
   exactly (e.g. `http://localhost:5000/auth/callback`).
   Spotify only permits `http` for loopback hosts (`localhost` / `127.0.0.1`);
   for a LAN IP use `https`, or do the one-time Spotify connect over an SSH
   tunnel to the server.
3. Copy `.env.example` to `.env` and fill in your credentials.
4. Start it:

   ```bash
   docker compose up --build
   ```

5. Open `http://<server>:5000`.

## Using it

1. On the **Profiles** page (the home screen), click **Add Profile**, enter a
   name, and you'll be sent to Spotify to connect that person's account.
2. Back on Profiles, hit the **⟳** on a profile (or **Sync** in the Library) to
   pull their liked songs and download the videos.
3. Pick a profile — or **Everyone** — to start the shuffled player.
4. On the **Library** page you can filter by profile, search, and **Match** /
   **Re-match** a song to a specific video URL if the automatic pick was wrong.

## Installing on Android smart tablets

The player is a PWA served by the Docker backend — there's no app store step.

1. On the tablet, open `http://<server>:5000` in Chrome.
2. Use the **⋮ menu → Install app / Add to Home Screen**.
3. Launch it from the home screen; it runs fullscreen in landscape.

The app shell is cached by a service worker so it opens instantly; videos and
Spotify data always come from the server over the network.

## Data & layout

Everything persists under `MTV_DOWNLOAD_DIR` (the mounted `./videos` volume):

| File | Contents |
|------|----------|
| `*.mp4` | downloaded music videos (one per song, shared across profiles) |
| `metadata.json` | video metadata keyed by song |
| `songs.json` | song catalog + which profiles like each song |
| `profiles.json` | family member profiles |
| `tokens/` | per-profile Spotify OAuth tokens |

## CLI (optional)

```bash
python cli.py --list                 # list profiles
python cli.py --profile Mom          # sync one connected profile
python cli.py                        # sync all connected profiles
python cli.py --serve                # sync, then start the web player
```
