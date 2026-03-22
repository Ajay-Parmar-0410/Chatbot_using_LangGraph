"""Date/time utility tool using stdlib only."""

from datetime import datetime, timedelta
from langchain_core.tools import tool


def _get_tz(timezone: str):
    """Get timezone object, falling back to UTC."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(timezone)
    except (ImportError, KeyError):
        try:
            from zoneinfo import ZoneInfo
            return ZoneInfo("UTC")
        except ImportError:
            return None


@tool
def datetime_info(action: str, timezone: str = "UTC", date1: str = "", date2: str = "") -> str:
    """Get current date/time or perform date calculations.
    Actions: 'now', 'diff', 'day_of_week', 'add_days'.
    Dates format: YYYY-MM-DD. Timezones: 'US/Eastern', 'Asia/Tokyo', etc."""
    try:
        tz = _get_tz(timezone)

        if action == "now":
            now = datetime.now(tz) if tz else datetime.utcnow()
            return (
                f"Current date/time in {timezone}:\n"
                f"Date: {now.strftime('%Y-%m-%d')}\n"
                f"Time: {now.strftime('%H:%M:%S')}\n"
                f"Day: {now.strftime('%A')}\n"
                f"ISO: {now.isoformat()}"
            )

        elif action == "diff":
            if not date1 or not date2:
                return "Error: Both date1 and date2 are required for 'diff' action (YYYY-MM-DD)."
            d1 = datetime.strptime(date1, "%Y-%m-%d")
            d2 = datetime.strptime(date2, "%Y-%m-%d")
            delta = abs((d2 - d1).days)
            return f"Difference between {date1} and {date2}: {delta} days"

        elif action == "day_of_week":
            if not date1:
                return "Error: date1 is required for 'day_of_week' action (YYYY-MM-DD)."
            d = datetime.strptime(date1, "%Y-%m-%d")
            return f"{date1} is a {d.strftime('%A')}"

        elif action == "add_days":
            if not date1 or not date2:
                return "Error: date1 (YYYY-MM-DD) and date2 (number of days) are required."
            d = datetime.strptime(date1, "%Y-%m-%d")
            days = int(date2)
            result = d + timedelta(days=days)
            return f"{date1} + {days} days = {result.strftime('%Y-%m-%d')} ({result.strftime('%A')})"

        else:
            return f"Unknown action '{action}'. Use: 'now', 'diff', 'day_of_week', 'add_days'."

    except ValueError as e:
        return f"Error: Invalid date format. Use YYYY-MM-DD. Details: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"
