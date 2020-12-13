import asyncio


async def self_delete(ctx, time=0.5):
    await asyncio.sleep(time)
    await ctx.message.delete()