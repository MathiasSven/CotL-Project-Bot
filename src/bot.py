import asyncio
import os
import aiohttp
import configparser

import discord
from discord.ext import commands, tasks

directory = os.path.dirname(os.path.realpath(__file__))

config = configparser.ConfigParser()
config.read(f"{os.path.join(directory, os.pardir)}/config.ini")

intents = discord.Intents.all()


class MyBot(commands.Bot):

    def __init__(self, **options):
        super().__init__(command_prefix=config.get("server", "PREFIX"), intents=intents)
        self.GUILD_ID = int(config.get("server", "GUILD_ID"))
        self.AUTO_ROLE_ID = int(config.get("server", "AUTO_ROLE_ID"))
        self.APPLICATION_CHANNEL_ID = int(config.get("server", "APPLICATION_CHANNEL_ID"))
        self.APPLICATIONS_CATEGORY_ID = int(config.get("server", "APPLICATIONS_CATEGORY_ID"))
        self.ADMIN_ID = int(config.get("server", "ADMIN_ID"))
        self.API_KEY = config.get("server", "API_KEY")
        self.API_URL = config.get("server", "API_URL")
        self.COLOUR = int(config.get("server", "COLOUR"), 16)

    # noinspection PyAttributeOutsideInit,PyTypeChecker
    async def on_ready(self):
        self.GUILD = self.get_guild(self.GUILD_ID)
        self.AUTO_ROLE = self.GUILD.get_role(self.AUTO_ROLE_ID)
        self.SYSTEM_CHANNEL = self.GUILD.system_channel
        self.APPLICATION_CHANNEL = self.GUILD.get_channel(self.APPLICATION_CHANNEL_ID)

        print("Bot is Ready!")

    async def on_member_join(self, member):
        await member.add_roles(self.AUTO_ROLE, reason="Auto Role", atomic=True)

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
        await welcome_embed.edit(content="")

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
            print(f"Member join call: {await response.text()}")

    async def on_member_remove(self, member):
        data = {
            "id": member.id,
        }
        async with aiohttp.request('PUT', f"{self.API_URL}/member-remove", json=data, headers={'x-api-key': self.API_KEY}) as response:
            print(f"Member remove call: {await response.text()}")

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
                print(f"Member update call: {await response.text()}")
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
            print(f"User update call: {await response.text()}")

    async def on_guild_role_create(self, role):
        data = {
            'id': role.id,
            'name': role.name,
            'position': role.position,
            'colour': role.colour.value,
        }
        async with aiohttp.request('POST', f"{self.API_URL}/role-create", json=data, headers={'x-api-key': self.API_KEY}) as response:
            print(f"Role creation call: {await response.text()}")

    async def on_guild_role_delete(self, role):
        data = {
            'id': role.id
        }
        async with aiohttp.request('PUT', f"{self.API_URL}/role-create", json=data, headers={'x-api-key': self.API_KEY}) as response:
            print(f"Role deletion call: {await response.text()}")

    async def on_guild_role_update(self, before, after):
        data = {
            'id': after.id,
            'name': after.name,
            'position': after.position,
            'colour': after.colour.value,
        }
        async with aiohttp.request('PUT', f"{self.API_URL}/role-update", json=data, headers={'x-api-key': self.API_KEY}) as response:
            print(f"Role update call: {await response.text()}")

    def run_bot(self):
        self.run(config.get("server", "TOKEN"))


instance = MyBot()


@instance.command()
async def reload(ctx, extension=None):
    await ctx.message.delete()
    if extension is None:
        await ctx.send(f"Must specify extension to reload")
        return None
    instance.unload_extension(f'cogs.{extension}')
    instance.load_extension(f'cogs.{extension}')
    await ctx.send(f"Successfully reloaded {extension} ")


for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        instance.load_extension(f'cogs.{filename[:-3]}')

instance.run_bot()
