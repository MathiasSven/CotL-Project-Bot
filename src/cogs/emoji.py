import os

from discord.ext import commands

from src.config import Config
from src.utils.checks import check_if_admin

directory = os.path.dirname(os.path.realpath(__file__))
config = Config()


class Emoji(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(self.startup())

    # noinspection PyAttributeOutsideInit
    async def startup(self):
        await self.bot.wait_until_ready()
        self.GUILD = self.bot.get_guild(self.bot.GUILD_ID)

    @commands.Cog.listener()
    async def on_ready(self):
        print('Emoji Cog is loaded')

    async def add_emoji(self, emoji_name: str, location: str, emoji_ids: dict, reason: str):
        with open(f"{directory}/emoji/{location}/{emoji_name}.png", "rb") as img:
            emoji = await self.GUILD.create_custom_emoji(name=emoji_name, image=img.read(), reason=reason)
            emoji_ids[emoji_name] = emoji.id

    @commands.group()
    @commands.check(check_if_admin)
    async def add_bank_emoji(self, ctx):
        emoji_to_add = ['coal', 'oil', 'uranium', 'lead', 'iron', 'bauxite', 'gasoline', 'munitions', 'steel', 'aluminum', 'food']
        emoji_ids = {}

        for emoji_name in emoji_to_add:
            await self.add_emoji(emoji_name, 'resources', emoji_ids, "Aid Requests")
        
        config.dict_set('emoji', emoji_ids)

        await ctx.send("Successfully added emoji.")

    @commands.group()
    @commands.check(check_if_admin)
    async def add_policy_emoji(self, ctx):
        emoji_to_add = ['attrition', 'turtle', 'blitzkrieg', 'fortress', 'moneybags', 'pirate', 'tactician', 'guardian', 'covert', 'arcane']
        emoji_ids = {}

        for emoji_name in emoji_to_add:
            await self.add_emoji(emoji_name, 'warpolicies', emoji_ids, "War Info")

        config.dict_set('emoji', emoji_ids)

        await ctx.send("Successfully added emoji.")


def setup(bot):
    bot.add_cog(Emoji(bot))
