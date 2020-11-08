import os

import discord
import requests
from discord.ext import commands
from discord.ext.commands import has_permissions


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
        await ctx.channel.purge(limit=1)
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
        response = requests.post(f"{self.bot.API_URL}/members-bulk", json=data, headers={'x-api-key': self.bot.API_KEY})
        if response.status_code == 201:
            await ctx.send(f"Successfully fetched all members to web server")
        print(f"Members bulk call: {response}")

    @commands.command(aliases=['clear'])
    @commands.check(check_if_admin)
    async def purge(self, ctx, amount=None):
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

        await ctx.channel.purge(limit=amount + 1)

    @purge.error
    async def purge_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.channel.purge(limit=1)
            await ctx.send("You do not have permission to execute this command.")


def setup(bot):
    bot.add_cog(Management(bot))
