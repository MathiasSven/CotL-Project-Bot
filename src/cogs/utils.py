import asyncio
import re
import random

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions

from src.models import PnWNation
from src.utils.checks import check_if_admin
from src.config import Config, codenames

config = Config()


class Utils(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.PNW_API_KEY = config.get("server", "PNW_API_KEY")
        self.WAR_ROOMS_CATEGORY_ID = int(config.get("utils", "WAR_ROOMS_CATEGORY_ID"))
        bot.loop.create_task(self.startup())

    # noinspection PyAttributeOutsideInit
    async def startup(self):
        await self.bot.wait_until_ready()
        self.GUILD = self.bot.get_guild(self.bot.GUILD_ID)
        self.WAR_ROOMS_CATEGORY = self.GUILD.get_channel(self.WAR_ROOMS_CATEGORY_ID)

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

    async def users_processor(self, ctx, users):
        async def process_user(user_id):

            user_pnw = await PnWNation.get_or_none(discord_user_id=user_id)

            if user_pnw is None:
                mentions = discord.AllowedMentions(users=False)
                await ctx.send(f"<@{user_id}> is not in the Database.", allowed_mentions=mentions)
                return None
            else:
                async with aiohttp.request('GET', f"http://politicsandwar.com/api/nation/id={user_pnw.nation_id}&key={self.PNW_API_KEY}") as response:
                    json_response = await response.json()
                    try:
                        nation_name = json_response['name']
                    except KeyError:
                        await ctx.send("There was an error requesting nation data.")
                        return None
                    else:
                        return json_response

        users_data = {}

        for user in users:
            regex = re.compile(r'^<@!?(?P<id>\d*)>$')
            regex_match = regex.match(user)

            if regex.match(user) is None:
                try:
                    user = int(user)
                except ValueError:
                    await ctx.send("Invalid user ID provided.")
                    return
                else:
                    processed_user_dict = await process_user(user)
                    if processed_user_dict is not None:
                        users_data[user] = processed_user_dict
                    else:
                        return
            else:
                user = regex_match.group("id")
                processed_user_dict = await process_user(user)
                if processed_user_dict is not None:
                    users_data[user] = processed_user_dict
                else:
                    return

        return users_data

    @commands.group(aliases=['warroom', 'wr'], invoke_without_command=True)
    async def war_room(self, ctx, *users):
        await asyncio.sleep(0.5)
        await ctx.message.delete()
        if not ctx.author.guild_permissions.manage_channels and str(ctx.author.id) not in str(users):
            await ctx.send("You do not have `manage_channels` perms, so you must include yourself in the 'users' argument")
            return

        users_data = await self.users_processor(ctx, users)
        if users_data is None:
            return

        # war_room_name = ""
        war_room_topic = ""
        embed_description = "\n"
        overwrites = self.WAR_ROOMS_CATEGORY.overwrites
        for user in users_data:
            user_data = users_data[user]
            # war_room_name += f"{'-' if war_room_name else ''}{user_data['leadername']}>"
            war_room_topic += f"{' | ' if war_room_topic else ''}<@{user}>"
            embed_description += f"<@{user}> | [{user_data['name']}](https://politicsandwar.com/nation/id={user_data['nationid']})" \
                                 f"```{user_data['soldiers']} 💂| {user_data['tanks']} ⚙| {user_data['aircraft']} ✈| {user_data['ships']} ⛵```"

            overwrites[self.GUILD.get_member(int(user))] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Maybe this will change
        tmp_codenames = codenames
        for exiting_channel in self.WAR_ROOMS_CATEGORY.text_channels:
            if exiting_channel.name in codenames:
                tmp_codenames.remove(exiting_channel.name)
        war_room_name = random.choice(codenames)
        ################

        war_room_embed = discord.Embed(colour=discord.Colour(self.bot.COLOUR), description=embed_description)
        war_room_embed.set_footer(text="Army info is only accurate upon creation")

        war_room_channel = await self.WAR_ROOMS_CATEGORY.create_text_channel(name=war_room_name, topic=f"War Room for: {war_room_topic}", overwrites=overwrites)
        msg = await war_room_channel.send(content=war_room_topic, embed=war_room_embed)
        await asyncio.sleep(0.5)
        await msg.edit(content="Start of war room.")

    @war_room.group(name='add')
    async def add_to_wr(self, ctx, *users):
        await asyncio.sleep(0.5)
        await ctx.message.delete()

        war_room = ctx.channel
        if war_room.category_id != self.WAR_ROOMS_CATEGORY_ID:
            await ctx.send("This is not a war room.")
            return

        users_data = await self.users_processor(ctx, users)
        if users_data is None:
            return

        war_room_topic = war_room.topic
        embed_description = "\n"
        overwrites = war_room.overwrites

        users_to_mention = ""

        for user in users_data:
            user_data = users_data[user]
            if user in war_room_topic:
                await ctx.send("One of the users provided is already in the war room.")
                return
            # war_room_name += f"{'-' if war_room_name else ''}{user_data['leadername']}>"
            war_room_topic += f"{' | ' if war_room_topic else ''}<@{user}>"
            embed_description += f"<@{user}> | [{user_data['name']}](https://politicsandwar.com/nation/id={user_data['nationid']})" \
                                 f"```{user_data['soldiers']} 💂| {user_data['tanks']} ⚙| {user_data['aircraft']} ✈| {user_data['ships']} ⛵```"

            overwrites[self.GUILD.get_member(int(user))] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            users_to_mention += f"<@{user}> "

        war_room_embed = discord.Embed(colour=discord.Colour(self.bot.COLOUR), description=embed_description)
        war_room_embed.set_footer(text="Army info is only accurate upon creation")

        await war_room.edit(topic=f"War Room for: {war_room_topic}", overwrites=overwrites)
        msg = await war_room.send(content=f"{users_to_mention}joined the room.", embed=war_room_embed)

    @war_room.group(name='exit')
    async def exit_wr(self, ctx):
        await asyncio.sleep(0.5)
        await ctx.message.delete()

        war_room = ctx.channel
        if war_room.category_id != self.WAR_ROOMS_CATEGORY_ID:
            await ctx.send("This is not a war room.")
            return
        if str(ctx.author.id) not in war_room.topic:
            await ctx.send("You are not in this war room.")
            return

        # name_regex = rf"(\| )?<\D\D?{ctx.author.id}>(?(1)| \|)"
        # name_result = re.sub(name_regex, "", war_room.name)

        regex = rf"(\| )?<\D\D?{str(ctx.author.id)}>(?(1)| \|)"
        topic_regex = re.finditer(regex, war_room.topic, re.MULTILINE)
        try:
            match = topic_regex.__next__()
        except StopIteration:
            await war_room.delete()
            return

        tmp_sting = war_room.topic
        topic_result = tmp_sting.replace(match.group(), "")

        await war_room.edit(topic=topic_result)
        await war_room.set_permissions(ctx.author, overwrite=None)

        embed = discord.Embed(description=f"**{ctx.author.mention} has left the war room.**", colour=discord.Colour(self.bot.COLOUR))

        await ctx.send(embed=embed)

    @war_room.group(name='remove')
    @has_permissions(manage_channels=True)
    async def remove_from_wr(self, ctx, user):
        await asyncio.sleep(0.5)
        await ctx.message.delete()

        regex = re.compile(r'^<@!?(?P<id>\d*)>$')
        regex_match = regex.match(user)

        if regex.match(user) is None:
            try:
                user = int(user)
            except ValueError:
                await ctx.send("Invalid user ID provided.")
        else:
            user = regex_match.group("id")

        war_room = ctx.channel
        if war_room.category_id != self.WAR_ROOMS_CATEGORY_ID:
            await ctx.send("This is not a war room.")
            return

        if str(user) not in war_room.topic:
            await ctx.send("This member is not in this war room.")
            return

        # name_regex = rf"(\| )?<\D\D?{ctx.author.id}>(?(1)| \|)"
        # name_result = re.sub(name_regex, "", war_room.name)

        regex = rf"(\| )?<\D\D?{user}>(?(1)| \|)"
        topic_regex = re.finditer(regex, war_room.topic, re.MULTILINE)
        try:
            match = topic_regex.__next__()
        except StopIteration:
            await war_room.delete()
            return

        tmp_sting = war_room.topic
        topic_result = tmp_sting.replace(match.group(), "")

        user_object = self.GUILD.get_member(int(user))
        await war_room.edit(topic=topic_result)
        await war_room.set_permissions(user_object, overwrite=None)

        embed = discord.Embed(description=f"**{user_object.mention} has been removed from the war room.**", colour=discord.Colour(self.bot.COLOUR))

        await ctx.send(embed=embed)

    @war_room.group(name='rename')
    async def rename_wr(self, ctx, *, new_name):
        await asyncio.sleep(0.5)
        await ctx.message.delete()

        war_room = ctx.channel
        if war_room.category_id != self.WAR_ROOMS_CATEGORY_ID:
            await ctx.send("This is not a war room.")
        else:
            regex = re.compile(r'^[a-zA-Z\d -]*?[^a-zA-Z\d -]+[a-zA-Z\d -]*?$')
            if regex.match(new_name) is not None:
                await ctx.send("Only english alphabet characters and digits are allowed [a-z 0-9]")
                return
            else:
                await war_room.edit(name=new_name)

                embed = discord.Embed(description=f"**War room successfully renamed to {war_room.mention}**", colour=discord.Colour(self.bot.COLOUR))
                await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Utils(bot))
