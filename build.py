#!/usr/bin/env python3
"""Fetches live data from APIs and writes data.json for the portfolio."""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DIR = Path(__file__).parent
DATA_FILE = DIR / "data.json"
CLAUDE_STATS_FILE = DIR / "claude-stats.json"


def load_existing():
    """Load existing data.json as fallback for failed API calls."""
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return {}


def fetch_json(url):
    """Fetch JSON from a URL. Returns None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "portfolio-build/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  Warning: failed to fetch {url}: {e}")
        return None


def fetch_github():
    """Fetch GitHub profile data."""
    print("Fetching GitHub data...")
    data = fetch_json("https://api.github.com/users/matthewmcdowall")
    if not data:
        return None
    return {
        "username": "matthewmcdowall",
        "publicRepos": data.get("public_repos", 0),
        "followers": data.get("followers", 0),
        "following": data.get("following", 0),
        "profileUrl": "https://github.com/matthewmcdowall",
        "contribChartUrl": "https://ghchart.rshah.org/matthewmcdowall",
    }


def fetch_huggingface():
    """Fetch HuggingFace profile data."""
    print("Fetching HuggingFace data...")
    data = fetch_json("https://huggingface.co/api/users/MatthewMcDowall/overview")
    if not data:
        return None
    return {
        "username": "MatthewMcDowall",
        "numModels": data.get("numModels", 0),
        "numDatasets": data.get("numDatasets", 0),
        "numSpaces": data.get("numSpaces", 0),
        "numFollowers": data.get("numFollowers", 0),
        "numFollowing": data.get("numFollowing", 0),
        "profileUrl": "https://huggingface.co/MatthewMcDowall",
    }


def fetch_strava():
    """Fetch recent Strava activities using OAuth refresh token."""
    client_id = os.environ.get("STRAVA_CLIENT_ID")
    client_secret = os.environ.get("STRAVA_CLIENT_SECRET")
    refresh_token = os.environ.get("STRAVA_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print("  Strava env vars not set, skipping API fetch")
        return None

    print("Fetching Strava data...")

    # Exchange refresh token for access token
    try:
        token_data = json.dumps({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }).encode()
        req = urllib.request.Request(
            "https://www.strava.com/oauth/token",
            data=urllib.parse.urlencode({
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            tokens = json.loads(resp.read().decode())
        access_token = tokens["access_token"]
    except Exception as e:
        print(f"  Warning: failed to get Strava access token: {e}")
        return None

    # Fetch recent activities
    activities_raw = []
    try:
        req = urllib.request.Request(
            "https://www.strava.com/api/v3/athlete/activities?per_page=5",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            activities_raw = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  Warning: failed to fetch Strava activities: {e}")
        return None

    activities = []
    for a in activities_raw:
        activities.append({
            "name": a.get("name", ""),
            "type": a.get("type", "Run"),
            "distance": a.get("distance", 0),
            "movingTime": a.get("moving_time", 0),
            "date": a.get("start_date_local", "")[:10],
            "elevation": a.get("total_elevation_gain", 0),
        })

    return {
        "username": "matthew mcdowall",
        "athleteId": "93790524",
        "profileUrl": "https://www.strava.com/athletes/93790524",
        "recentActivities": activities,
    }


def load_claude_stats():
    """Load local Claude stats if available."""
    if CLAUDE_STATS_FILE.exists():
        print("Loading Claude stats from claude-stats.json...")
        with open(CLAUDE_STATS_FILE) as f:
            return json.load(f)
    print("  No claude-stats.json found (run sync-claude-stats.py locally)")
    return None


def build_data():
    existing = load_existing()

    github = fetch_github() or existing.get("github")
    huggingface = fetch_huggingface() or existing.get("huggingface")
    claude = load_claude_stats() or existing.get("claude")
    strava = fetch_strava() or existing.get("strava")

    data = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "claude": claude,
        "github": github,
        "spotify": {
            "showId": "1F1rBp40lgfZfIP5lLZVaK",
            "label": "Currently Listening",
        },
        "huggingface": huggingface,
        "strava": strava,
    }

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nWrote {DATA_FILE}")
    if github:
        print(f"  GitHub: {github['publicRepos']} repos")
    if huggingface:
        print(f"  HuggingFace: {huggingface['numFollowing']} following")
    if claude:
        print(f"  Claude: {claude['totalMessages']} messages, {claude['activeDays']} days")
    if strava and strava.get("recentActivities"):
        print(f"  Strava: {len(strava['recentActivities'])} recent activities")


if __name__ == "__main__":
    build_data()
