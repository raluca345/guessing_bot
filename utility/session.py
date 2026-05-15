from contextlib import asynccontextmanager
from utility_functions import active_session, get_active_session_lock


@asynccontextmanager
async def session_lock(channel_id):
    lock = get_active_session_lock(channel_id)
    
    async with lock:
        if active_session[channel_id]:
            raise RuntimeError("Session already started")
        active_session[channel_id] = True
    
    try:
        yield
    finally:
        active_session[channel_id] = False