import asyncio
import re

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
        regex = re.compile(r'^<@!?(?P<id>\d*)>$')
        regex_match = regex.match(user)
        if regex.match(user) is None:
            try:
                user = int(user)
            except ValueError:
                await ctx.send("Invalid user ID.")
                return
        else:
            user = regex_match.group("id")

        user_pnw = await PnWNation.get_or_none(discord_user_id=user)
        if user_pnw is None:
            await ctx.send("User with the given ID is not in the Database.")
            return
        else:
            await ctx.send(f"https://politicsandwar.com/nation/id={user_pnw.nation_id}")

    @commands.command(aliases=['du', 'au'])
    async def associated_user(self, ctx, nation_id="f"):
        # await asyncio.sleep(0.5)
        # await ctx.message.delete()
        try:
            user = int(nation_id)
        except ValueError:
            await ctx.send("Invalid nation ID.")
            return
        user_pnw = await PnWNation.get_or_none(nation_id=nation_id)
        if user_pnw is None:
            await ctx.send("Nation with given ID has no associated user in the Database.")
            return
        else:
            mentions = discord.AllowedMentions(users=False)
            await ctx.send(f"<@{user_pnw.discord_user_id}>", allowed_mentions=mentions)


def setup(bot):
    bot.add_cog(Utils(bot))
