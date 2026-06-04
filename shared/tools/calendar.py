"""Google Calendar — auth + event listing.

Ported from ``Ruhi/features/google_calendar.py``:
- Dropped ``pyttsx3 speak()`` (UI layer's job).
- Pulls credentials/timezone/calendar id from ``shared.config``.
- Returns structured ``CalendarEvent`` objects (not pre-formatted strings).

Auth is interactive on first run (OAuth installed-app flow) — exactly like
the legacy version, but token storage path is now configurable.
"""
from __future__ import annotations

import datetime as dt
import pickle
from dataclasses import dataclass
from pathlib import Path

import pytz

from shared.config import settings
from shared.tools.errors import ToolError

_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events.readonly",
]


@dataclass
class CalendarEvent:
    summary: str
    start: dt.datetime | dt.date
    end: dt.datetime | dt.date
    all_day: bool


def _load_service():
    creds_path: Path = settings.google_credentials_file
    token_path: Path = settings.google_token_file

    if not creds_path.exists():
        raise ToolError(
            f"Google credentials not found at {creds_path}. "
            "Download credentials.json from Google Cloud Console.",
            code="auth",
        )

    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if token_path.exists():
        try:
            creds = pickle.loads(token_path.read_bytes())
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), _SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_bytes(pickle.dumps(creds))

    return build("calendar", "v3", credentials=creds)


async def list_events(
    *,
    on: dt.date | None = None,
    days_ahead: int = 0,
    max_results: int = 10,
) -> list[CalendarEvent]:
    """List events for a given date, or the next ``days_ahead`` days from today."""
    tz = pytz.timezone(settings.calendar_timezone)
    today = dt.datetime.now(tz).date()
    target_start = on or today
    target_end = target_start + dt.timedelta(days=days_ahead)

    start_dt = tz.localize(dt.datetime.combine(target_start, dt.time.min))
    end_dt = tz.localize(dt.datetime.combine(target_end, dt.time.max))

    try:
        service = _load_service()
        result = (
            service.events()
            .list(
                calendarId=settings.google_calendar_id,
                timeMin=start_dt.isoformat(),
                timeMax=end_dt.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Calendar API error: {e}", code="upstream")

    events: list[CalendarEvent] = []
    for item in result.get("items", []):
        start_raw = item["start"].get("dateTime") or item["start"].get("date")
        end_raw = item["end"].get("dateTime") or item["end"].get("date")
        all_day = "dateTime" not in item["start"]
        if all_day:
            start = dt.date.fromisoformat(start_raw)
            end = dt.date.fromisoformat(end_raw)
        else:
            start = dt.datetime.fromisoformat(start_raw.replace("Z", "+00:00")).astimezone(tz)
            end = dt.datetime.fromisoformat(end_raw.replace("Z", "+00:00")).astimezone(tz)
        events.append(
            CalendarEvent(summary=item.get("summary", "(no title)"), start=start, end=end, all_day=all_day)
        )
    return events
