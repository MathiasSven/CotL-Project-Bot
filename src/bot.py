import datetime
import os
from typing import Union

import discord
from discord.ext import commands, tasks
import requests

intents = discord.Intents.all()


class MyBot(commands.Bot):

    def __init__(self, **options):
        super().__init__(command_prefix=os.getenv('PREFIX'), intents=intents)
        self.GUILD_ID = int(os.getenv('GUILD_ID'))
        self.AUTO_ROLE_ID = int(os.getenv('AUTO_ROLE_ID'))
        self.APPLICATION_CHANNEL_ID = int(os.getenv('APPLICATION_CHANNEL_ID'))
        self.API_KEY = os.getenv('API_KEY')
        self.API_URL = "http://127.0.0.1:8000/api"

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

        embed = discord.Embed(title="Children of the Light", colour=discord.Colour(0xa57d48), url="https://politicsandwar.com/alliance/id=7452",
                              description=f"**Salutations** {member.mention}**!**,\nWelcome to Children of the Light! If you wish to Join please follow the instructions in #applications")

        embed.set_image(url="https://images.cotl.pw/children-of-the-light.png")

        try:
            embed.add_field(name="​", value=f"For any of your FA concerns please speak with {self.GUILD.get_member(211389941475835904).mention} or {self.GUILD.get_member(364254409388982272).mention}.",
                            inline=False)
        except AttributeError:
            pass
        embed.add_field(name="​", value="**Praise be! For the light has shined upon you!**", inline=False)

        welcome_embed = await self.SYSTEM_CHANNEL.send(content=f"{member.mention}", embed=embed, allowed_mentions=mentions)
        await welcome_embed.edit(content="")

        roles = []
        for role in member.roles:
            roles.append({
                'id': role.id,
                'name': role.name,
                'colour': role.colour.value,
            })

        data = {
            'id': member.id,
            'username': member.name,
            'discriminator': member.discriminator,
            'avatar': member.avatar,
            'nick': member.nick,
            'roles': roles,
        }
        response = requests.post(f"{self.API_URL}/member-join", json=data, headers={'x-api-key': self.API_KEY})
        print(response)

    async def on_member_remove(self, member):
        data = {
            "id": member.id,
        }
        response = requests.post(f"{self.API_URL}/member-remove", json=data, headers={'x-api-key': self.API_KEY})
        print(response)

    async def on_member_update(self, before, after):
        if before.roles != after.roles or before.nick != after.nick:

            roles = []
            for role in after.roles:
                roles.append({
                    'id': role.id,
                    'name': role.name,
                    'colour': role.colour.value,
                })

            data = {
                "id": after.id,
                'username': after.name,
                'discriminator': after.discriminator,
                "avatar": after.avatar,
                "nick": after.nick,
                "roles": roles,
            }
            response = requests.post(f"{self.API_URL}/member-update", json=data, headers={'x-api-key': self.API_KEY})
            print(response)
        else:
            pass

    async def on_user_update(self, before, after):
        pass

    def run_bot(self):
        self.run(os.getenv('TOKEN'))


instance = MyBot()


@instance.command()
async def reload(ctx, extension=None):
    if extension is None:
        await ctx.send(f"Must specify extension to reload")
        return None
    instance.unload_extension(f'cogs.{extension}')
    instance.load_extension(f'cogs.{extension}')


for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        instance.load_extension(f'cogs.{filename[:-3]}')

instance.run_bot()
