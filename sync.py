"""
Sync Strava activities from intervals.icu's web session into uploaded
activities accessible via the public API.

Why this exists: the intervals.icu API returns empty stubs for any activity
sourced from Strava. The web frontend, however, can download fit files for
fully-analyzed Strava activities. We re-upload them via the documented
upload endpoint so they become first-class `source=UPLOAD` activities, which
the API can then expose normally.

Required env vars:
    ICU_EMAIL        intervals.icu login email
    ICU_PASSWORD     intervals.icu login password
    ICU_API_KEY      intervals.icu API key (Settings -> Developer)
    ICU_ATHLETE_ID   e.g. i216809

Optional env vars:
    LOOKBACK_DAYS    how many days back to scan (default 7)
    ACTIVITY_TYPES   comma-separated Strava activity types to sync
                     (default "Ride"; empty string disables filter)
"""

import logging
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

API = "https://intervals.icu"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/148.0.0.0 Safari/537.36"
)

log = logging.getLogger("icu-sync")


def env(name: str, default: str | None = None) -> str:
    v = os.environ.get(name, default)
    if not v:
        log.error("missing required env var: %s", name)
        sys.exit(2)
    return v


def make_web_session(email: str, password: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": f"{API}/",
            "User-Agent": UA,
        }
    )
    s.cookies.set("locale", "en", domain="intervals.icu")
    r = s.post(
        f"{API}/api/login?deviceClass=desktop",
        files={"email": (None, email), "password": (None, password)},
        timeout=30,
    )
    if r.status_code != 200:
        log.error("web login failed: HTTP %s body=%s", r.status_code, r.text[:200])
        sys.exit(3)
    return s


def make_api_session(api_key: str) -> requests.Session:
    s = requests.Session()
    s.auth = ("API_KEY", api_key)
    s.headers.update({"User-Agent": "icu-auto-reload/1.0"})
    return s


def list_recent_activities(api: requests.Session, athlete_id: str, days: int) -> list[dict]:
    oldest = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    r = api.get(
        f"{API}/api/v1/athlete/{athlete_id}/activities",
        params={
            "oldest": oldest,
            "fields": "id,source,start_date_local,name,external_id",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def web_get_activity_meta(web: requests.Session, activity_id: str) -> dict | None:
    r = web.get(f"{API}/api/activity/{activity_id}", timeout=30)
    if r.status_code != 200:
        log.warning("meta fetch failed for %s: HTTP %s", activity_id, r.status_code)
        return None
    return r.json()


def web_download_fit(web: requests.Session, activity_id: str) -> bytes | None:
    r = web.get(f"{API}/api/activity/{activity_id}/fit-file", timeout=60)
    if r.status_code != 200:
        log.warning("fit download failed for %s: HTTP %s", activity_id, r.status_code)
        return None
    if len(r.content) < 1024:
        log.warning(
            "fit for %s suspiciously small (%dB) — skipping",
            activity_id,
            len(r.content),
        )
        return None
    return r.content


def upload_fit(
    api: requests.Session, athlete_id: str, strava_id: str, fit_bytes: bytes
) -> tuple[int, str]:
    r = api.post(
        f"{API}/api/v1/athlete/{athlete_id}/activities",
        params={"external_id": strava_id},
        files={"file": (f"{strava_id}.fit", fit_bytes, "application/octet-stream")},
        timeout=120,
    )
    return r.status_code, r.text


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    email = env("ICU_EMAIL")
    password = env("ICU_PASSWORD")
    api_key = env("ICU_API_KEY")
    athlete_id = env("ICU_ATHLETE_ID")
    days = int(os.environ.get("LOOKBACK_DAYS", "7"))
    allowed_types = {
        t.strip() for t in os.environ.get("ACTIVITY_TYPES", "Ride").split(",") if t.strip()
    }

    api = make_api_session(api_key)
    log.info("listing activities, lookback=%dd", days)
    activities = list_recent_activities(api, athlete_id, days)
    stravas = [a for a in activities if a.get("source") == "STRAVA"]
    log.info("found %d total, %d Strava stubs", len(activities), len(stravas))
    if not stravas:
        return 0

    web = make_web_session(email, password)
    log.info("web login ok")

    uploaded = skipped_queued = skipped_type = failed = 0
    for a in stravas:
        sid = a["id"]
        when = (a.get("start_date_local") or "")[:16]
        meta = web_get_activity_meta(web, sid)
        if meta is None:
            failed += 1
            continue
        atype = meta.get("type") or "?"
        if allowed_types and atype not in allowed_types:
            log.info("skip %s (%s) — type=%s not in %s", sid, when, atype, sorted(allowed_types))
            skipped_type += 1
            continue
        if not meta.get("analyzed"):
            log.info("skip %s (%s) — not yet analyzed by intervals.icu", sid, when)
            skipped_queued += 1
            continue

        fit = web_download_fit(web, sid)
        if fit is None:
            failed += 1
            continue

        code, body = upload_fit(api, athlete_id, sid, fit)
        if code in (200, 201):
            tag = "new" if code == 201 else "dup"
            log.info("uploaded %s (%s) [%s] %dB", sid, when, tag, len(fit))
            uploaded += 1
        else:
            log.error("upload failed for %s: HTTP %s body=%s", sid, code, body[:200])
            failed += 1

    log.info(
        "done: uploaded=%d queued=%d wrong-type=%d failed=%d",
        uploaded,
        skipped_queued,
        skipped_type,
        failed,
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
