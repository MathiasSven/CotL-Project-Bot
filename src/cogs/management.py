import os

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import validators
import re


def check_if_admin(ctx):
    return ctx.message.author.id == int(os.getenv('ADMIN_ID'))


class Management(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # Events
    # @commands.Cog.listener()
    # async def on_ready(self):
    #     print("Bot is ready")

    # Commands
    @commands.group(aliases=['fetch'])
    @commands.check(check_if_admin)
    async def get(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid get command passed...')

    @get.command()
    async def members(self, ctx):
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
            print(f"Member join call: {await response.text()}")
            if response.status == 201:
                await ctx.send(f"Successfully fetched all members to web server.")
            else:
                await ctx.send(f"Post request was unsuccessful.")
            print(f"Members bulk call: {await response.text()}")

    @commands.command(aliases=['clear'])
    @commands.check(check_if_admin)
    async def purge(self, ctx, amount=None):
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

    @commands.command(aliases=['connect'])
    @has_permissions(manage_roles=True)
    async def link(self, ctx, user="f", nation_url="s"):
        await ctx.message.delete()
        regex = re.compile(r'^<@!\d*>$')
        if regex.match(user) is not None:
            if validators.url(nation_url):
                data = {
                    'id': user[3:-1],
                    'nation_url': nation_url,
                }
                async with aiohttp.request('POST', f"{self.bot.API_URL}/link-nation", json=data, headers={'x-api-key': self.bot.API_KEY}) as resp:
                    response = await resp.text()
                    print(f"Link nation call: {response}")
                    if resp.status == 201:
                        mentions = discord.AllowedMentions(users=False)
                        await ctx.send(f"Successfully linked nation to {user}.", allowed_mentions=mentions)
                    else:
                        await ctx.send(f"Link request was unsuccessful.")
                    print(f"Link nation call: {response}")
            else:
                await ctx.send("Invalid nation URL.")
        else:
            await ctx.send("Invalid user argument.")

    @link.error
    @purge.error
    @get.error
    async def purge_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure) or isinstance(error, commands.MissingPermissions):
            await ctx.message.delete()
            await ctx.send("You do not have permission to execute this command.")


def setup(bot):
    bot.add_cog(Management(bot))
