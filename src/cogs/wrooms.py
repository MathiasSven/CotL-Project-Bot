import asyncio
import re
import random

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions

from src.models import PnWNation, WarRoom
from src.config import Config, codenames
from src.utils.inputparse import InputParser
from src.utils.checks import is_war_room
from src.utils.selfdelete import self_delete

config = Config()


class WarRooms(commands.Cog):

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
        print('War Rooms Cog is loaded')

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if channel.category_id == self.WAR_ROOMS_CATEGORY_ID:
            war_room_instance = await WarRoom.w_get(channel)
            await war_room_instance.delete()

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
                        # noinspection PyUnusedLocal
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
    @commands.has_role(int(config.get("server", "MEMBER_ROLE_ID")))
    async def war_room(self, ctx, *users):
        await self_delete(ctx)

        if not ctx.author.guild_permissions.manage_channels and str(ctx.author.id) not in str(users):
            await ctx.send("You do not have `manage_channels` perms, so you must include yourself in the 'users' argument")
            return

        users_data = await self.users_processor(ctx, users)
        if not users_data:
            return

        users_to_mention = []
        embed_description = "\n"
        overwrites = self.WAR_ROOMS_CATEGORY.overwrites
        for user in users_data:
            user_data = users_data[user]
            users_to_mention.append(f"<@{user}>")

            embed_description += f"<@{user}> | [{user_data['name']}](https://politicsandwar.com/nation/id={user_data['nationid']})" \
                                 f"```{user_data['soldiers']} 💂| {user_data['tanks']} ⚙| {user_data['aircraft']} ✈| {user_data['ships']} ⛵```\n"

            overwrites[self.GUILD.get_member(int(user))] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)

        tmp_codenames = codenames
        for exiting_channel in self.WAR_ROOMS_CATEGORY.text_channels:
            if exiting_channel.name in codenames:
                tmp_codenames.remove(exiting_channel.name)
        war_room_name = random.choice(codenames)

        war_room_embed = discord.Embed(colour=discord.Colour(self.bot.COLOUR), description=embed_description)
        war_room_embed.set_footer(text="Army info is only accurate upon creation")

        war_room_channel = await WarRoom.w_create(self.WAR_ROOMS_CATEGORY, name=war_room_name, overwrites=overwrites)

        first_msg = await war_room_channel.send(content=' '.join([str(elem) for elem in users_to_mention]), embed=war_room_embed)
        await asyncio.sleep(0.5)
        await first_msg.edit(content="Start of war room.")

    @war_room.group(name='add')
    async def add_to_wr(self, ctx, *users):
        await self_delete(ctx)

        if not await is_war_room(ctx):
            return

        users_data = await self.users_processor(ctx, users)
        if not users_data:
            return

        war_room_instance = await WarRoom.w_get(ctx.channel)
        embed_description = "\n"
        overwrites = ctx.channel.overwrites

        participants = await war_room_instance.participants.all().values_list('discord_user_id', flat=True)
        users_to_mention = []
        for user in users_data:

            user_data = users_data[user]
            if user in participants:
                await ctx.send("One of the users provided is already in the war room.")
                return

            users_to_mention.append(f"<@{user}>")

            embed_description += f"<@{user}> | [{user_data['name']}](https://politicsandwar.com/nation/id={user_data['nationid']})" \
                                 f"```{user_data['soldiers']} 💂| {user_data['tanks']} ⚙| {user_data['aircraft']} ✈| {user_data['ships']} ⛵```\n"

            overwrites[self.GUILD.get_member(int(user))] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        war_room_embed = discord.Embed(colour=discord.Colour(self.bot.COLOUR), description=embed_description)
        war_room_embed.set_footer(text="Army info is only accurate upon creation")

        await war_room_instance.add(overwrites=overwrites)

        await ctx.send(content=f"{' '.join([str(elem) for elem in users_to_mention])} joined the room.", embed=war_room_embed)

    @war_room.group(name='exit')
    async def exit_wr(self, ctx):
        await self_delete(ctx)

        if not await is_war_room(ctx):
            return

        war_room_instance = await WarRoom.w_get(ctx.channel)
        if ctx.author.id not in await war_room_instance.participants.all().values_list('discord_user_id', flat=True):
            await ctx.send("You are not in this war room.")
            return

        await war_room_instance.exit(ctx.author)

        embed = discord.Embed(description=f"**{ctx.author.mention} has left this war room.**", colour=discord.Colour(self.bot.COLOUR))
        try:
            await ctx.send(embed=embed)
        except discord.errors.NotFound:
            pass

    @war_room.group(name='remove')
    @has_permissions(manage_roles=True)
    async def remove_from_wr(self, ctx, user="f"):
        await self_delete(ctx)

        parsed_input = InputParser(ctx)
        user = await parsed_input.user_mention_id(user)
        if user is None:
            return

        if not await is_war_room(ctx):
            return

        war_room_instance = await WarRoom.w_get(ctx.channel)
        if int(user) not in await war_room_instance.participants.all().values_list('discord_user_id', flat=True):
            await ctx.send("This member is not in this war room.")
            return

        member_object = self.GUILD.get_member(int(user))
        await war_room_instance.exit(member_object)

        embed = discord.Embed(description=f"**{member_object.mention} has been removed from this war room.**", colour=discord.Colour(self.bot.COLOUR))

        try:
            await ctx.send(embed=embed)
        except discord.errors.NotFound:
            pass

    @war_room.group(name='update', aliases=['info', 'now', 'up'])
    async def update_wr(self, ctx):
        await self_delete(ctx)

        war_room_instance = await WarRoom.w_get(ctx.channel)
        users = await war_room_instance.participants.all().values_list('discord_user_id', flat=True)
        users = [str(user_id) for user_id in users]
        users_data = await self.users_processor(ctx, users)
        if not users_data:
            return

        embed_description = "\n"
        for user in users_data:
            user_data = users_data[user]
            embed_description += f"<@{user}> | [{user_data['name']}](https://politicsandwar.com/nation/id={user_data['nationid']})" \
                                 f"```{user_data['soldiers']} 💂| {user_data['tanks']} ⚙| {user_data['aircraft']} ✈| {user_data['ships']} ⛵```\n"

        war_room_embed = discord.Embed(colour=discord.Colour(self.bot.COLOUR), description=embed_description)
        war_room_embed.set_footer(text="Army info is only accurate upon creation")
        await ctx.send(content="Update:", embed=war_room_embed)


def setup(bot):
    bot.add_cog(WarRooms(bot))
