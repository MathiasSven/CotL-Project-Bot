import asyncio

from discord.ext.commands import CommandInvokeError


async def self_delete(ctx, time=0.5):
    await asyncio.sleep(time)
    try:
        await ctx.message.delete()
    except CommandInvokeError:
        pass