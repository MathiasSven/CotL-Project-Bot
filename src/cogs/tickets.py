import discord
from discord.ext import commands

from emoji import EMOJI_ALIAS_UNICODE as EMOJI
import datetime

from src.config import Config

config = Config()


# noinspection DuplicatedCode
class Tickets(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.INTERVIEWER_CHANNEL_ID = int(config.get("interviews", "INTERVIEWER_CHANNEL_ID"))
        self.INTERVIEWER_ROLE_ID = int(config.get("interviews", "INTERVIEWER_ROLE_ID"))
        bot.loop.create_task(self.startup())

        self.applications_embed_title = "Applications"

    async def create_application_embed(self) -> discord.Message:
        embed = discord.Embed(title=self.applications_embed_title, colour=discord.Colour(self.bot.COLOUR),
                              description=f"To apply to join Cataclysm, react to this message with {EMOJI[':clipboard:']}"
                                          f", and wait until one of our interviewers adds you to create a group chat.")
        embed.set_footer(text="Cataclysm", icon_url=self.GUILD.icon_url)

        message = await self.APPLICATION_CHANNEL.send(embed=embed)
        await message.add_reaction(EMOJI[':clipboard:'])
        return message

    async def create_interviewer_embed(self, applicant: discord.Member) -> discord.Message:
        embed = discord.Embed(title="New Applicant", colour=discord.Colour(self.bot.COLOUR),
                              description=f"The first on the trigger, react with {EMOJI[':white_check_mark:']}")
        embed.set_author(name=applicant.display_name, icon_url=applicant.avatar_url)

        embed.add_field(name=f"Applicant:",
                        value=applicant.mention,
                        inline=True)

        embed.add_field(name=f"Assigned To:",
                        value=f"Unassigned",
                        inline=True)

        embed.set_footer(text="Applied:")
        embed.timestamp = datetime.datetime.utcnow()

        message = await self.INTERVIEWER_CHANNEL.send(self.INTERVIEWER_ROLE.mention, embed=embed)
        await message.add_reaction(EMOJI[':white_check_mark:'])
        return message

    # noinspection PyAttributeOutsideInit
    async def startup(self):
        await self.bot.wait_until_ready()
        self.GUILD = self.bot.get_guild(self.bot.GUILD_ID)
        self.INTERVIEWER_CHANNEL = self.GUILD.get_channel(self.INTERVIEWER_CHANNEL_ID)
        self.INTERVIEWER_ROLE = self.GUILD.get_role(self.INTERVIEWER_ROLE_ID)
        self.APPLICATION_CHANNEL = self.GUILD.get_channel(self.bot.APPLICATION_CHANNEL_ID)

        messages_w_embeds = [message async for message in self.APPLICATION_CHANNEL.history(limit=100) if bool(message.embeds)]
        try:
            application_message = next(filter(lambda message: message.embeds[0].title == self.applications_embed_title, messages_w_embeds))
        except StopIteration:
            application_message = await self.create_application_embed()

        # noinspection PyShadowingNames
        def reaction_check(payload):
            if payload.guild_id:
                return not payload.member.bot and payload.message_id == application_message.id
            return False

        while True:
            payload = await self.bot.wait_for('raw_reaction_add', check=reaction_check)
            if str(payload.emoji) == EMOJI[':clipboard:']:
                await self.create_interviewer_embed(payload.member)

            message = await self.APPLICATION_CHANNEL.fetch_message(payload.message_id)
            await message.remove_reaction(payload.emoji, payload.member)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        try:
            message = await self.INTERVIEWER_CHANNEL.fetch_message(payload.message_id)
        except discord.errors.NotFound:
            return
        else:
            member = payload.member

        if member is None or message.author != self.bot.user:
            return

        if member == self.bot.user:
            return

        try:
            interviewer_embed = message.embeds.pop()
        except IndexError:
            return
        if "New Applicant" not in interviewer_embed.title or not any((reaction.me for reaction in message.reactions)):
            await message.remove_reaction(payload.emoji, payload.member)
            return

        print(message.reactions)

        if str(payload.emoji) == EMOJI[':white_check_mark:']:
            await message.clear_reactions()
            interviewer_embed.timestamp = datetime.datetime.utcnow()
            interviewer_embed.set_footer(text=f"Assigned:")
            interviewer_embed.set_field_at(index=2, name=f"Assigned To:", value=member.mention)
            await message.edit(embed=interviewer_embed)
        else:
            await message.remove_reaction(payload.emoji, payload.member)

    @commands.Cog.listener()
    async def on_ready(self):
        print('Tickets Cog is loaded')


def setup(bot):
    bot.add_cog(Tickets(bot))
