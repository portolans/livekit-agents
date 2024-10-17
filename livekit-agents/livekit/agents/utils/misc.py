from __future__ import annotations

import time
import uuid


def time_ms() -> int:
    return int(time.time() * 1000)


def shortuuid(prefix: str = "") -> str:
    return prefix + str(uuid.uuid4().hex)[:12]


def message_id() -> str:
    """<Portola> A globally unique, prefixed identifier for every message in the chat history.
    
    We do not use shortuuid() above because there is too high risk of collision.
    """
    return f"CM_{str(uuid.uuid4().hex)}"
