import asyncio

import discord
from discord.ext import commands

from src.models import PnWNation
from src.utils.checks import check_if_admin
from src.config import Config

config = Config()


class Utils(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Utils Cog is loaded')

    @commands.command(aliases=['nl', 'nation'])
    async def nation_link(self, ctx, user="f"):
        # await asyncio.sleep(0.5)
        # await ctx.message.delete()
        try:
            user = int(user)
        except ValueError:
            await ctx.send("Invalid user ID.")
            return
        user_pnw = await PnWNation.get_or_none(discord_user_id=user)
        if user_pnw is None:
            await ctx.send("User with the given ID is not in the Database.")
            return
        else:
            await ctx.send(f"https://politicsandwar.com/nation/id={user_pnw.nation_id}")


def setup(bot):
    bot.add_cog(Utils(bot))
