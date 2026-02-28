#!/usr/bin/env python3
import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error

STRAVA_TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"
STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"

REQUIRED_ENV = [
    "STRAVA_CLIENT_ID",
    "STRAVA_CLIENT_SECRET",
    "STRAVA_REFRESH_TOKEN",
]


SENSITIVE_KEYS = {"access_token", "refresh_token"}


def getenv_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"Missing required env var: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def post_form(url: str, data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def safe_dict(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in SENSITIVE_KEYS}


def get_json(url: str, token: str):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        body = None
        try:
            body = err.read().decode("utf-8")
        except Exception:
            body = None
        print(f"HTTP Error {err.code} for {url}", file=sys.stderr)
        if body:
            print(body, file=sys.stderr)
        raise


def main() -> int:
    for name in REQUIRED_ENV:
        getenv_required(name)

    client_id = os.environ["STRAVA_CLIENT_ID"]
    client_secret = os.environ["STRAVA_CLIENT_SECRET"]
    refresh_token = os.environ["STRAVA_REFRESH_TOKEN"]

    token_payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    token_resp = post_form(STRAVA_TOKEN_URL, token_payload)
    access_token = token_resp.get("access_token")
    if not access_token:
        print("Failed to refresh access token", file=sys.stderr)
        print(json.dumps(safe_dict(token_resp), indent=2), file=sys.stderr)
        return 1

    activities_url = STRAVA_ACTIVITIES_URL + "?per_page=10"
    activities = get_json(activities_url, access_token)

    if not isinstance(activities, list) or not activities:
        print("No activities returned", file=sys.stderr)
        return 1

    latest_run = None
    for activity in activities:
        if activity.get("type") in ("Run", "VirtualRun", "TrailRun"):
            latest_run = activity
            break

    if latest_run is None:
        print("No recent run activities found", file=sys.stderr)
        return 1

    output = {
        "id": latest_run.get("id"),
        "name": latest_run.get("name"),
        "type": latest_run.get("type"),
        "start_date": latest_run.get("start_date"),
        "start_date_local": latest_run.get("start_date_local"),
        "timezone": latest_run.get("timezone"),
        "distance_m": latest_run.get("distance"),
        "moving_time_s": latest_run.get("moving_time"),
        "elapsed_time_s": latest_run.get("elapsed_time"),
        "total_elevation_gain_m": latest_run.get("total_elevation_gain"),
        "average_speed_mps": latest_run.get("average_speed"),
        "average_heartrate": latest_run.get("average_heartrate"),
    }

    out_path = os.path.join("data", "strava", "latest.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
