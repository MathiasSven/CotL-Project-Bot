import asyncio
import os
import string
import random
import sys

import aiohttp
import configparser

import tortoise
from captcha.image import ImageCaptcha

import discord
from discord.ext import commands

directory = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(1, os.path.dirname(directory))

config = configparser.ConfigParser()
config.read(f"{os.path.join(directory, os.pardir)}/config.ini")

intents = discord.Intents.all()


# noinspection PyUnusedLocal
class MyBot(commands.Bot):

    def __init__(self, **options):
        super().__init__(command_prefix=config.get("server", "PREFIX"), intents=intents)
        self.GUILD_ID = int(config.get("server", "GUILD_ID"))
        self.AUTO_ROLE_ID = int(config.get("server", "AUTO_ROLE_ID"))
        self.APPLICATION_CHANNEL_ID = int(config.get("server", "APPLICATION_CHANNEL_ID"))
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
        self.SYSTEM_CHANNEL = self.GUILD.system_channel
        self.APPLICATION_CHANNEL = self.GUILD.get_channel(self.APPLICATION_CHANNEL_ID)
        # self.PUBLIC_CATEGORY = self.GUILD.get_channel(self.PUBLIC_CATEGORY_ID)

        print("Bot is Ready!")

    async def on_member_join(self, member):
        verify_dm = await member.create_dm()

        characters = string.ascii_uppercase + "123456789123456789123456789"
        captcha_result = ''.join(random.choice(characters) for i in range(5))

        image = ImageCaptcha()
        data = image.generate(captcha_result)
        image.write(captcha_result, f'{directory}/captchas/{captcha_result}.png')
        image_file = discord.File(f'{directory}/captchas/{captcha_result}.png', filename=f'{captcha_result}.png')

        verify_embed = discord.Embed(title="Welcome to the Children of the Light", colour=discord.Colour(self.COLOUR))
        verify_embed.add_field(name="**Captcha**", value="Please complete the captcha below to gain access to the server.\n**NOTE:** Only **Uppercase** and **No Zeros**\n\u200b", inline=False)
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
                captcha_attempt = await self.wait_for('message', check=check_captcha, timeout=120.0)
            except asyncio.exceptions.TimeoutError or asyncio.TimeoutError:
                await verify_dm.send(f'You took too long...\nPlease rejoin using this link to try again:\n{self.GUILD_INVITE_URL}')
                await member.kick(reason="Took to long to answer the captcha.")
                break
            else:
                if captcha_attempt.content == captcha_result:
                    await verify_dm.send(f'You successfully answered the captcha! You should now have access to the server.')
                    await self.verified_new_user(member)
                    break
                else:
                    if i == 4:
                        await verify_dm.send(
                            f'You have **incorrectly** answered the captcha **{number_of_tries}** times.\nPlease rejoin using this link to try again:\n{self.GUILD_INVITE_URL}')
                        await member.kick(reason="Failed the captcha multiple times.")
                    elif i == 3:
                        await verify_dm.send(f'Your answer was incorrect, you have **{number_of_tries - 1 - i}** attempt left.')
                    else:
                        await verify_dm.send(f'Your answer was incorrect, you have **{number_of_tries - 1 - i}** attempts left.')

    # New Method
    async def verified_new_user(self, member):
        mentions = discord.AllowedMentions(users=True)

        embed = discord.Embed(title="Children of the Light", colour=discord.Colour(self.COLOUR), url="https://politicsandwar.com/alliance/id=7452",
                              description=f"**Salutations** {member.mention},\nWelcome to Children of the Light! If you wish to Join please follow the instructions in {self.APPLICATION_CHANNEL.mention}")

        embed.set_image(url="https://images.cotl.pw/children-of-the-light.png")

        try:
            embed.add_field(name="​",
                            value=f"For any of your FA concerns please speak with {self.GUILD.get_member(364254409388982272).mention}.",
                            inline=False)
        except AttributeError:
            pass
        embed.add_field(name="​", value="**Praise be! For the light has shined upon you!**", inline=False)

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
        data = {
            "id": member.id,
        }
        async with aiohttp.request('PUT', f"{self.API_URL}/member-remove", json=data, headers={'x-api-key': self.API_KEY}) as response:
            json_response = await response.text()
            print(f"Member remove call: {json_response}")

    async def on_member_update(self, before, after):
        if len(before.roles) == 1:
            return
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
        async with aiohttp.request('PUT', f"{self.API_URL}/role-create", json=data, headers={'x-api-key': self.API_KEY}) as response:
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

instance = MyBot()


@instance.command()
async def reload(ctx, extension=None):
    await ctx.message.delete()
    if extension is None:
        await ctx.send(f"Must specify extension to reload")
        return None
    instance.unload_extension(f'src.cogs.{extension}')
    instance.load_extension(f'src.cogs.{extension}')
    await ctx.send(f"Successfully reloaded {extension} ")


for filename in os.listdir(f'{directory}/cogs'):
    if filename.endswith('.py') and not filename.startswith('__init__'):
        instance.load_extension(f'src.cogs.{filename[:-3]}')

instance.run_bot()