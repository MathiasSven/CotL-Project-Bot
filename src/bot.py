import asyncio
import os
from concurrent import futures
import random
import sys

import aiohttp
import configparser

import tortoise
from captcha.image import ImageCaptcha

import discord
from discord.ext import commands
import traceback

from discord_slash import SlashCommand

directory = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(1, os.path.dirname(directory))
from src.utils import selfdelete

config = configparser.ConfigParser()
config.read(f"{os.path.join(directory, os.pardir)}/config.ini")

intents = discord.Intents.all()
activity = discord.Activity(name=f'the end of the world', type=discord.ActivityType.watching)


# noinspection PyUnusedLocal
class MyBot(commands.Bot):

    def __init__(self, **options):
        super().__init__(command_prefix=config.get("server", "PREFIX"), intents=intents)
        self.GUILD_ID = int(config.get("server", "GUILD_ID"))
        self.AA_ID = int(config.get("server", "AA_ID"))
        self.AUTO_ROLE_ID = int(config.get("server", "AUTO_ROLE_ID"))
        self.OFFENSIVE_WARS_CHANNEL_ID = int(config.get("tasks", "OFFENSIVE_WARS_CHANNEL_ID"))
        self.DEFENSIVE_WARS_CHANNEL_ID = int(config.get("tasks", "DEFENSIVE_WARS_CHANNEL_ID"))
        self.APPLICATION_CHANNEL_ID = int(config.get("server", "APPLICATION_CHANNEL_ID"))
        self.MODERATION_LOGS_CHANNEL_ID = int(config.get("logs", "MODERATION_LOGS_CHANNEL_ID"))
        self.IT_LOGS_CHANNEL_ID = int(config.get("logs", "IT_LOGS_ID"))
        self.PUBLIC_CATEGORY_ID = int(config.get("server", "PUBLIC_CATEGORY_ID"))
        self.ADMIN_ID = int(config.get("server", "ADMIN_ID"))
        self.API_KEY = config.get("server", "API_KEY")
        self.API_URL = config.get("server", "API_URL")
        self.GUILD_INVITE_URL = config.get("server", "GUILD_INVITE_URL")
        self.COLOUR = int(config.get("server", "COLOUR"), 16)

        self.loop.run_until_complete(start_database())

    # noinspection PyAttributeOutsideInit,PyTypeChecker
    async def on_ready(self):
        self.GUILD = self.get_guild(self.GUILD_ID)
        self.AUTO_ROLE = self.GUILD.get_role(self.AUTO_ROLE_ID)
        self.OFFENSIVE_WARS_CHANNEL = self.GUILD.get_channel(self.OFFENSIVE_WARS_CHANNEL_ID)
        self.DEFENSIVE_WARS_CHANNEL = self.GUILD.get_channel(self.DEFENSIVE_WARS_CHANNEL_ID)
        self.SYSTEM_CHANNEL = self.GUILD.system_channel
        self.APPLICATION_CHANNEL = self.GUILD.get_channel(self.APPLICATION_CHANNEL_ID)
        self.MODERATION_LOGS_CHANNEL = self.GUILD.get_channel(self.MODERATION_LOGS_CHANNEL_ID)
        self.IT_LOGS_CHANNEL = self.GUILD.get_channel(self.IT_LOGS_CHANNEL_ID) if self.IT_LOGS_CHANNEL_ID != 0 else None
        # self.PUBLIC_CATEGORY = self.GUILD.get_channel(self.PUBLIC_CATEGORY_ID)

        await self.change_presence(activity=activity)
        print("Bot is Ready!")

    async def on_error(self, event, *args, **kwargs):
        if self.IT_LOGS_CHANNEL_ID != 0:
            await self.IT_LOGS_CHANNEL.send(content=f"<@{self.ADMIN_ID}>```py\nIgnoring exception in **{event}**\n{traceback.format_exc(chain=False)}```")
        else:
            await super(MyBot, self).on_error(event, *args, **kwargs)

    async def on_command_error(self, ctx: commands.Context, exception):
        if isinstance(exception, commands.errors.CommandError):
            if isinstance(exception, commands.errors.MissingRole):
                await ctx.send("You don't have the role necessary to run this command.")
            elif isinstance(exception, commands.MissingPermissions):
                await ctx.send("You do not have permission to execute this command.")
            elif isinstance(exception, commands.CommandNotFound):
                print(f"ERROR -- {exception} -- ERROR")
            elif isinstance(exception, futures.TimeoutError):
                print(f"ERROR -- {exception} -- ERROR")
            else:
                if self.IT_LOGS_CHANNEL_ID != 0:
                    await self.IT_LOGS_CHANNEL.send(content=f'__**CommandError**__\n'
                                                            f'Command: {ctx.command.name}\n'
                                                            f'Caller: {ctx.author}\n'
                                                            f'Channel: {getattr(ctx.channel, "mention", "Private")}\n'
                                                            f'Exception: **{exception}**')
                raise exception
        else:
            if self.IT_LOGS_CHANNEL_ID != 0:
                await self.IT_LOGS_CHANNEL.send(content=exception.__traceback__)
            await super(MyBot, self).on_command_error(ctx, exception)

    async def moderation_log(self, event: str, **kwargs):
        embed = None
        member = kwargs.get('member', None)
        if event == 'server_join':
            embed = discord.Embed(description=f"{member.mention} **({member.name}#{member.discriminator}) has joined the server.**", colour=discord.Colour(self.COLOUR))
        elif event == 'left_server':
            roles = [role.mention for role in member.roles]
            del roles[0]
            if len(roles) == 0:
                return
            roles_append = f"**Their roles were:** {' '.join(roles)}" if roles else "**They had no roles.**"
            embed = discord.Embed(description=f"{member.mention} **({member.name}#{member.discriminator}) has left the server.**\n"
                                              f"{roles_append}", colour=discord.Colour(self.COLOUR))
        elif event == 'captcha_timeout':
            embed = discord.Embed(description=f"{member.mention} **({member.name}#{member.discriminator}) took too long to answer the captcha.**", colour=discord.Colour(self.COLOUR))
        elif event == 'captcha_passed':
            embed = discord.Embed(description=f"{member.mention} **({member.name}#{member.discriminator}) has successfully answered the captcha.**", colour=discord.Colour(self.COLOUR))
        elif event == 'incorrect_captcha':
            embed = discord.Embed(description=f"{member.mention} **({member.name}#{member.discriminator}) incorrectly answered the captcha.**", colour=discord.Colour(self.COLOUR))
        elif event == 'failed_captcha':
            embed = discord.Embed(description=f"{member.mention} **({member.name}#{member.discriminator}) failed the captcha too many times, they were kicked.**", colour=discord.Colour(self.COLOUR))
        await self.MODERATION_LOGS_CHANNEL.send(embed=embed)

    async def on_member_join(self, member):
        if member.bot:
            return
        await self.moderation_log('server_join', member=member)
        verify_dm = await member.create_dm()

        # characters = string.ascii_uppercase + "123456789123456789123456789"
        characters = "0123456789"
        captcha_result = ''.join(random.choice(characters) for i in range(5))

        image = ImageCaptcha()
        data = image.generate(captcha_result)
        image.write(captcha_result, f'{directory}/captchas/{captcha_result}.png')
        image_file = discord.File(f'{directory}/captchas/{captcha_result}.png', filename=f'{captcha_result}.png')

        verify_embed = discord.Embed(title="Welcome to the Cataclysm", colour=discord.Colour(self.COLOUR))
        # verify_embed.add_field(name="**Captcha**", value="Please complete the captcha below to gain access to the server.\n**NOTE:** Only **Uppercase** and **No Zeros**\n\u200b", inline=False)
        verify_embed.add_field(name="**Captcha**", value="Please complete the captcha below to gain access to the server.\n**NOTE:** Only **Numbers** and **No Spaces**\n\u200b", inline=False)
        verify_embed.add_field(name="**Why?**", value="This is to protect the server against\nmalicious raids using automated bots", inline=False)
        verify_embed.add_field(name="\u200b", value="**Your Captcha:**", inline=False)
        verify_embed.set_image(url=f'attachment://{captcha_result}.png')

        await verify_dm.send(file=image_file, embed=verify_embed)

        os.remove(f'{directory}/captchas/{captcha_result}.png')

        def check_captcha(m):
            return m.channel == verify_dm and m.author == member

        number_of_tries = 5

        for i in range(number_of_tries):
            try:
                captcha_attempt = await self.wait_for('message', check=check_captcha, timeout=180.0)
            except (asyncio.TimeoutError, futures.TimeoutError, futures._base.TimeoutError):
                await verify_dm.send(f'You took too long...\nPlease rejoin using this link to try again:\n{self.GUILD_INVITE_URL}')
                await self.moderation_log('captcha_timeout', member=member)
                await member.kick(reason="Took too long to answer the captcha.")
                break
            else:
                if captcha_attempt.content == captcha_result:
                    await verify_dm.send(f'You successfully answered the captcha! You should now have access to the server.')
                    await self.moderation_log('captcha_passed', member=member)
                    await self.verified_new_user(member)
                    break
                else:
                    if i == 4:
                        await verify_dm.send(
                            f'You have **incorrectly** answered the captcha **{number_of_tries}** times.\nPlease rejoin using this link to try again:\n{self.GUILD_INVITE_URL}')
                        await self.moderation_log('failed_captcha', member=member)
                        await member.kick(reason="Failed the captcha multiple times.")
                    elif i == 3:
                        await verify_dm.send(f'Your answer was incorrect, you have **{number_of_tries - 1 - i}** attempt left.')
                        await self.moderation_log('incorrect_captcha', member=member)
                    else:
                        await verify_dm.send(f'Your answer was incorrect, you have **{number_of_tries - 1 - i}** attempts left.')
                        await self.moderation_log('incorrect_captcha', member=member)

    # New Method
    async def verified_new_user(self, member):
        mentions = discord.AllowedMentions(users=True)

        embed = discord.Embed(title="Cataclysm", colour=discord.Colour(self.COLOUR), url="https://politicsandwar.com/alliance/id=7452",
                              description=f"**Salutations** {member.mention},\nWelcome to Cataclysm! If you wish to Join please follow the instructions in {self.APPLICATION_CHANNEL.mention}")

        # embed.set_image(url="https://images.cotl.pw/children-of-the-light.png")

        try:
            embed.add_field(name="​",
                            value=f"For any of your FA concerns please speak with {self.GUILD.get_member(211389941475835904).mention}.",
                            inline=False)
        except AttributeError:
            pass
        # embed.add_field(name="​", value="**Praise be! For the light has shined upon you!**", inline=False)

        await asyncio.sleep(1)
        welcome_embed = await self.SYSTEM_CHANNEL.send(content=f"{member.mention}", embed=embed, allowed_mentions=mentions)

        await member.add_roles(self.AUTO_ROLE, reason="Auto Role", atomic=True)
        roles = []
        for role in member.roles:
            roles.append({
                'id': role.id,
                'name': role.name,
                'position': role.position,
                'colour': role.colour.value,
            })

        data = {
            'id': member.id,
            'name': member.name,
            'discriminator': member.discriminator,
            'avatar': member.avatar,
            'nick': member.nick,
            'roles': roles,
        }
        async with aiohttp.request('POST', f"{self.API_URL}/member-join", json=data, headers={'x-api-key': self.API_KEY}) as response:
            json_response = await response.text()
            print(f"Member join call: {json_response}")

    async def on_member_remove(self, member):
        await self.moderation_log('left_server', member=member)
        data = {
            "id": member.id,
        }
        async with aiohttp.request('PUT', f"{self.API_URL}/member-remove", json=data, headers={'x-api-key': self.API_KEY}) as response:
            json_response = await response.text()
            print(f"Member remove call: {json_response}")

    async def on_member_update(self, before, after):
        if before.roles != after.roles or before.nick != after.nick:
            if before.roles != after.roles:
                roles = []
                for role in after.roles:
                    roles.append({
                        'id': role.id,
                        'name': role.name,
                        'position': role.position,
                        'colour': role.colour.value,
                    })
                data = {
                    "id": after.id,
                    "nick": after.nick,
                    "roles": roles,
                }
            else:
                data = {
                    "id": after.id,
                    "nick": after.nick,
                }
            async with aiohttp.request('PUT', f"{self.API_URL}/member-update", json=data, headers={'x-api-key': self.API_KEY}) as response:
                json_response = await response.text()
                print(f"Member update call: {json_response}")
        else:
            pass

    async def on_user_update(self, before, after):
        data = {
            "id": after.id,
            'name': after.name,
            'discriminator': after.discriminator,
            "avatar": after.avatar,
        }
        async with aiohttp.request('PUT', f"{self.API_URL}/user-update", json=data, headers={'x-api-key': self.API_KEY}) as response:
            json_response = await response.text()
            print(f"User update call: {json_response}")

    async def on_guild_role_create(self, role):
        data = {
            'id': role.id,
            'name': role.name,
            'position': role.position,
            'colour': role.colour.value,
        }
        async with aiohttp.request('POST', f"{self.API_URL}/role-create", json=data, headers={'x-api-key': self.API_KEY}) as response:
            json_response = await response.text()
            print(f"Role creation call: {json_response}")

    async def on_guild_role_delete(self, role):
        data = {
            'id': role.id
        }
        async with aiohttp.request('PUT', f"{self.API_URL}/role-remove", json=data, headers={'x-api-key': self.API_KEY}) as response:
            json_response = await response.text()
            print(f"Role deletion call: {json_response}")

    async def on_guild_role_update(self, before, after):
        data = {
            'id': after.id,
            'name': after.name,
            'position': after.position,
            'colour': after.colour.value,
        }
        async with aiohttp.request('PUT', f"{self.API_URL}/role-update", json=data, headers={'x-api-key': self.API_KEY}) as response:
            json_response = await response.text()
            print(f"Role update call: {json_response}")

    def run_bot(self):
        self.run(config.get("server", "TOKEN"))


async def start_database():
    await tortoise.Tortoise.init(
        db_url=f"sqlite://db.sqlite3",
        modules={"models": ["src.models"]}
    )
    await tortoise.Tortoise.generate_schemas()


bot_instance = MyBot()
slash_instance = SlashCommand(bot_instance, sync_commands=True, sync_on_cog_reload=True)


@bot_instance.command()
async def reload(ctx, extension=None):
    await ctx.message.delete()
    if extension is None:
        await ctx.send(f"Must specify extension to reload")
        return None
    bot_instance.unload_extension(f'src.cogs.{extension}')
    bot_instance.load_extension(f'src.cogs.{extension}')
    await ctx.send(f"Successfully reloaded {extension} ")


for filename in os.listdir(f'{directory}/cogs'):
    if filename.endswith('.py') and not filename.startswith('__init__'):
        bot_instance.load_extension(f'src.cogs.{filename[:-3]}')

bot_instance.run_bot()
