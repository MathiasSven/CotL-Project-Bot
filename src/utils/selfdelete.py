import asyncio

from discord.ext.commands import CommandInvokeError
from discord.errors import Forbidden


async def self_delete(ctx, time=0.5):
    await asyncio.sleep(time)
    try:
        await ctx.message.delete()
    except (CommandInvokeError, Forbidden):
        pass