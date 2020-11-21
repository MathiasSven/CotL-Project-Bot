import asyncio
import configparser
import os
import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import validators
import re

directory = os.path.dirname(os.path.realpath(__file__))

config = configparser.ConfigParser()
config.read(f"{os.path.join(os.path.join(directory, os.pardir), os.pardir)}/config.ini")


def check_if_admin(ctx):
    return ctx.message.author.id == int(config.get("server", "ADMIN_ID"))


class Management(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Management Cog is loaded')

    # Commands
    @commands.group(aliases=['fetch'])
    @commands.check(check_if_admin)
    async def get(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid get command passed...')

    @get.command()
    async def members(self, ctx):
        await asyncio.sleep(0.5)
        await ctx.message.delete()
        members = self.bot.GUILD.members
        data = []
        for member in members:
            roles = []
            for role in member.roles:
                roles.append({
                    'id': role.id,
                    'name': role.name,
                    'position': role.position,
                    'colour': role.colour.value,
                })
            data.append({
                'id': member.id,
                'name': member.name,
                'discriminator': member.discriminator,
                'avatar': member.avatar,
                'nick': member.nick,
                'roles': roles,
            })
        async with aiohttp.request('POST', f"{self.bot.API_URL}/members-bulk", json=data, headers={'x-api-key': self.bot.API_KEY}) as response:
            json_response = await response.text()
            if response.status == 201:
                await ctx.send(f"Successfully fetched all members to web server.")
            else:
                await ctx.send(f"Post request was unsuccessful.")
            print(f"Members bulk call: {json_response}")

    @commands.group(aliases=['clear'], invoke_without_command=True)
    @commands.check(check_if_admin)
    async def purge(self, ctx, amount=None):
        await asyncio.sleep(0.5)
        await ctx.message.delete()
        if amount is None:
            await ctx.send(f"Must specify purge amount")
            return None
        try:
            amount = int(amount)
        except ValueError:
            await ctx.send(f"Argument must be of **Int** Type!")
            return None

        if amount <= 0:
            await ctx.send(f"Argument must be greater then 0")
            return None

        await ctx.channel.purge(limit=amount)

    @purge.group(name='from', invoke_without_command=True)
    @commands.check(check_if_admin)
    async def _from(self, ctx, from_id=None):
        await asyncio.sleep(0.5)
        await ctx.message.delete()

        if from_id is None:
            await ctx.send(f"Must specify message ID to purge from.")
            return None

        try:
            msg = await ctx.channel.fetch_message(from_id)
        except discord.errors.HTTPException or discord.errors.NotFound:
            await ctx.send(f"Message with **ID**:{from_id} was not found.")
            return None

        await ctx.channel.purge(limit=10, after=msg)

    @_from.command()
    @commands.check(check_if_admin)
    async def till(self, ctx, from_id=None, till_id=None):
        await asyncio.sleep(0.5)
        await ctx.message.delete()

        if from_id is None or till_id is None:
            await ctx.send(f"Must specify message ID to purge from and message ID to purge to.")
            return None

        try:
            from_msg = await ctx.channel.fetch_message(from_id)
            till_msg = await ctx.channel.fetch_message(till_id)
        except discord.errors.HTTPException or discord.errors.NotFound:
            await ctx.send(f"Messages with **ID**:{from_id} or **ID**:{till_id} were not found.")
            return None

        await ctx.channel.purge(after=from_msg, before=till_msg)

    @commands.command(aliases=['connect'])
    @has_permissions(manage_roles=True)
    async def link(self, ctx, user="f", nation_link="s"):
        await asyncio.sleep(0.5)
        await ctx.message.delete()
        regex = re.compile(r'^<@!\d*>$')
        if regex.match(user) is not None:
            if validators.url(nation_link):
                nation_id = nation_link.split("politicsandwar.com/nation/id=")
                if nation_link != nation_id[0]:
                    nation_id = nation_id[1]
                else:
                    await ctx.send("Invalid nation URL.")
                    return
                data = {
                    'id': user[3:-1],
                    'nation_id': nation_id,
                }
                async with aiohttp.request('POST', f"{self.bot.API_URL}/link-nation", json=data, headers={'x-api-key': self.bot.API_KEY}) as response:
                    json_response = await response.text()
                    if response.status == 201:
                        mentions = discord.AllowedMentions(users=False)
                        await ctx.send(f"Successfully linked nation to {user}.", allowed_mentions=mentions)
                    else:
                        await ctx.send(f"Link request was unsuccessful.")
                    print(f"Link nation call: {json_response}")
            else:
                await ctx.send("Invalid nation URL.")
        else:
            await ctx.send("Invalid user argument.")

    # @commands.command(aliases=['raid', 'panic'])
    # @has_permissions(manage_roles=True)
    # async def freeze(self, ctx):
    #     public_category = self.bot.APPLICATION_CHANNEL.category
    #     public_text_channels = public_category.text_channels
    #     for channel in public_text_channels:
    #         can_send_messages = channel.overwrites_for(self.bot.AUTO_ROLE).send_messages
    #         if can_send_messages
    #     pass

    @link.error
    @purge.error
    @_from.error
    @till.error
    @get.error
    async def perms_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure) or isinstance(error, commands.MissingPermissions):
            await ctx.message.delete()
            await ctx.send("You do not have permission to execute this command.")


def setup(bot):
    bot.add_cog(Management(bot))
