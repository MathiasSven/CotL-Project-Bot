import asyncio

MAX_ASYNCIO_SECONDS = 2678400  # 31 Days


async def chunked_sleep(time):
    for k in _chunk_sleep(time):
        await asyncio.sleep(k)


def _chunk_sleep(sleep_time):
    while sleep_time > 0:
        new = sleep_time - MAX_ASYNCIO_SECONDS

        if new < 0:
            yield sleep_time
            break
        elif new > MAX_ASYNCIO_SECONDS:
            yield MAX_ASYNCIO_SECONDS
            sleep_time -= MAX_ASYNCIO_SECONDS
        else:
            yield new
            break
