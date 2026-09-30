from typing import Dict
from user_agents import parse


def parse_user_agent_metadata(user_agent_string: str) -> Dict[str, any]:
    """
    Parses a raw User-Agent header into structured dimensions:
    device_type, browser, os, and is_bot flag.
    """
    if not user_agent_string:
        return {
            "device_type": "unknown",
            "browser": "unknown",
            "os": "unknown",
            "is_bot": False,
        }

    try:
        ua = parse(user_agent_string)

        if ua.is_bot:
            device_type = "bot"
        elif ua.is_mobile:
            device_type = "mobile"
        elif ua.is_tablet:
            device_type = "tablet"
        elif ua.is_pc:
            device_type = "desktop"
        else:
            device_type = "other"

        browser_family = ua.browser.family or "unknown"
        os_family = ua.os.family or "unknown"

        return {
            "device_type": device_type,
            "browser": browser_family[:32],
            "os": os_family[:32],
            "is_bot": ua.is_bot,
        }
    except Exception:
        return {
            "device_type": "unknown",
            "browser": "unknown",
            "os": "unknown",
            "is_bot": False,
        }