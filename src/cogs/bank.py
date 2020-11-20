import asyncio
import configparser
import os
import urllib.parse

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
from emoji import EMOJI_ALIAS_UNICODE as EMOJI
import validators

directory = os.path.dirname(os.path.realpath(__file__))

config = configparser.ConfigParser()
config.read(f"{os.path.join(os.path.join(directory, os.pardir), os.pardir)}/config.ini")


def check_if_admin(ctx):
    return ctx.message.author.id == int(config.get("server", "ADMIN_ID"))


class Bank(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.PNW_API_KEY = config.get("server", "PNW_API_KEY")
        self.BANK_REQUEST_ID = int(config.get("server", "BANK_REQUEST_ID"))
        bot.loop.create_task(self.startup())

    # noinspection PyAttributeOutsideInit
    async def startup(self):
        await self.bot.wait_until_ready()
        self.resource_emoji = {
            'uranium': self.bot.get_emoji(int(config.get("server", "uranium"))),
            'gasoline': self.bot.get_emoji(int(config.get("server", "gasoline"))),
            'munitions': self.bot.get_emoji(int(config.get("server", "munitions"))),
            'steel': self.bot.get_emoji(int(config.get("server", "steel"))),
            'aluminum': self.bot.get_emoji(int(config.get("server", "aluminum"))),
            'food': self.bot.get_emoji(int(config.get("server", "food"))),
            'money': EMOJI[':moneybag:']
        }
        self.GUILD = self.bot.get_guild(self.bot.GUILD_ID)
        self.BANK_REQUEST_CHANNEL = self.GUILD.get_channel(self.BANK_REQUEST_ID)

    @commands.Cog.listener()
    async def on_ready(self):
        print('Bank Cog is loaded')

    # Aid Request reaction listener
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        try:
            message = await self.BANK_REQUEST_CHANNEL.fetch_message(payload.message_id)
        except discord.errors.NotFound:
            return
        else:
            member = payload.member
        if member is None or message.author != self.bot.user:
            return

        if member == self.bot.user:
            return

        try:
            aid_request_embed = message.embeds.pop()
        except IndexError:
            return
        if "Request " not in aid_request_embed.title:
            return

        # Found Embed
        if len(message.reactions) == 1:
            await message.remove_reaction(payload.emoji, member)
            return

        if str(payload.emoji) != EMOJI[':white_check_mark:'] and str(payload.emoji) != EMOJI[':x:']:
            await message.clear_reaction(payload.emoji)
            return

        await message.remove_reaction(payload.emoji, member)

        if not member.guild_permissions.manage_roles:
            return
        else:
            await message.clear_reactions()
            field_num = len(aid_request_embed.fields)
            if str(payload.emoji) == EMOJI[':white_check_mark:']:
                aid_request_embed.set_field_at(index=field_num - 1, name=f"Status:", value=f"Fulfilled by {member.mention}")
                await message.edit(embed=aid_request_embed)
            elif str(payload.emoji) == EMOJI[':x:']:
                aid_request_embed.set_field_at(index=field_num - 1, name=f"Status:", value=f"Denied by {member.mention}")
                await message.edit(embed=aid_request_embed)

    @commands.group()
    @commands.check(check_if_admin)
    async def add_emoji(self, ctx):
        with open(f"{directory}/emoji/uranium.png", "rb") as img:
            await self.GUILD.create_custom_emoji(name='uranium', image=img.read(), reason="Aid Requests")
        with open(f"{directory}/emoji/gasoline.png", "rb") as img:
            await self.GUILD.create_custom_emoji(name='gasoline', image=img.read(), reason="Aid Requests")
        with open(f"{directory}/emoji/munitions.png", "rb") as img:
            await self.GUILD.create_custom_emoji(name='munitions', image=img.read(), reason="Aid Requests")
        with open(f"{directory}/emoji/steel.png", "rb") as img:
            await self.GUILD.create_custom_emoji(name='steel', image=img.read(), reason="Aid Requests")
        with open(f"{directory}/emoji/aluminum.png", "rb") as img:
            await self.GUILD.create_custom_emoji(name='aluminum', image=img.read(), reason="Aid Requests")
        with open(f"{directory}/emoji/food.png", "rb") as img:
            await self.GUILD.create_custom_emoji(name='food', image=img.read(), reason="Aid Requests")

    @commands.group()
    async def aid(self, ctx):
        if ctx.message.channel != self.BANK_REQUEST_CHANNEL:
            await asyncio.sleep(0.5)
            await ctx.message.delete()
            await ctx.send(f"Please use {self.BANK_REQUEST_CHANNEL.mention}.")
            return

        aid_dm = await ctx.message.author.create_dm()
        bot_user = self.bot.user

        aid_embed = discord.Embed(title="Military Aid Request", colour=discord.Colour(self.bot.COLOUR))
        aid_embed.add_field(name="**Process:**",
                            value="React to the resources you would like to request below,\nonce you have selected all of them react to the checkmark :white_check_mark:\n\u200b\nYou will then be prompted to give your requested values.",
                            inline=False)

        aid_embed.add_field(name="**Cancel/Retry:**",
                            value="If at anytime you wish to cancel the request just type `cancel`, or `retry` if you entered any value incorrectly.",
                            inline=False)

        aid_embed = await aid_dm.send(embed=aid_embed)

        await asyncio.sleep(0.5)
        await ctx.message.delete()

        for _, emoji in self.resource_emoji.items():
            await aid_embed.add_reaction(emoji)

        await aid_embed.add_reaction(EMOJI[':white_check_mark:'])

        # noinspection PyShadowingNames
        def reaction_check(reaction, user):
            return str(reaction.emoji) == EMOJI[':white_check_mark:'] and user == ctx.message.author

        # noinspection PyShadowingNames
        def check(msg):
            return msg.channel == aid_dm and msg.author == ctx.message.author

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=reaction_check)
        except asyncio.TimeoutError:
            await aid_dm.send('You took too long...')
        else:

            resources_requested = []
            _reactions = await aid_dm.fetch_message(aid_embed.id)
            _reactions = _reactions.reactions
            for _reaction in _reactions:
                if _reaction.count == 2 and _reaction.emoji != '✅':
                    resources_requested.append(_reaction.emoji)

            resource_amount = []
            for i in resources_requested:
                resource = list(self.resource_emoji.keys())[list(self.resource_emoji.values()).index(i)]
                embed = discord.Embed(description=f"**Type the desired amount of {resource}** {i}", colour=discord.Colour(self.bot.COLOUR))
                await aid_dm.send(embed=embed)

                number_of_tries = 5
                for x in range(number_of_tries):
                    if x == 1:
                        await aid_dm.send("Make sure to not include any commas")
                    if x == number_of_tries - 1:
                        await aid_dm.send("This is your last try!")
                    try:
                        message = await self.bot.wait_for('message', timeout=60.0, check=check)
                    except asyncio.TimeoutError:
                        await aid_dm.send('You took too long...')
                        return
                    else:
                        try:
                            amount = int(message.content)
                            if amount < 0:
                                await aid_dm.send("Haha, very funny. Now please type a positive number :)")
                                del amount
                            elif amount > 100000000000:
                                await aid_dm.send("In your dreams, try again")
                                del amount
                            else:
                                break
                        except ValueError or TypeError:
                            if message.content == "cancel":
                                await aid_dm.send("Aid Request Canceled")
                                return
                            elif message.content == "retry":
                                # TODO
                                await aid_dm.send("Aid Request Canceled. For now you will have to use the command again")
                                return
                            else:
                                if x == number_of_tries - 1:
                                    await aid_dm.send("You have exceeded your number of tries. Use the command again if you wish to retry")
                                    return
                                else:
                                    await aid_dm.send("Please type an integer")

                if "amount" in locals():
                    # noinspection PyUnboundLocalVariable
                    resource_amount.append((f"{resource}", f"{amount}"))
                else:
                    return

            embed = discord.Embed(description="**State your reason**", colour=discord.Colour(self.bot.COLOUR))
            await aid_dm.send(embed=embed)
            try:
                message = await self.bot.wait_for('message', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await aid_dm.send('You took too long...')
                return
            else:
                if message.content == "cancel":
                    await aid_dm.send("Aid Request Canceled")
                    return
                elif message.content == "retry":
                    # TODO
                    await aid_dm.send("Aid Request Canceled. For now you will have to use the command again")
                    return
                else:
                    reason = message.content

            embed = discord.Embed(description="**Lastly, please link your nation**", colour=discord.Colour(self.bot.COLOUR))
            await aid_dm.send(embed=embed)
            for x in range(5):
                if x == 4:
                    await aid_dm.send("This is your last try!")
                try:
                    message = await self.bot.wait_for('message', timeout=60.0, check=check)
                except asyncio.TimeoutError:
                    await aid_dm.send('You took too long...')
                    return
                else:
                    if validators.url(message.content):
                        nation_link = message.content
                        nation_id = nation_link.split("politicsandwar.com/nation/id=")
                        if nation_link != nation_id[0]:
                            nation_id = nation_id[1]
                            break
                        else:
                            del nation_link
                            del nation_id
                            await aid_dm.send("Please type a valid link")
                    elif message.content == "cancel":
                        await aid_dm.send("Aid Request Canceled")
                        return
                    elif message.content == "retry":
                        # TODO
                        await aid_dm.send("Aid Request Canceled. For now you will have to use the command again.")
                        return
                    else:
                        await aid_dm.send("Please type a valid link")

            if "nation_link" in locals():
                # noinspection PyUnboundLocalVariable
                pass
            else:
                return

            # noinspection PyUnboundLocalVariable
            async with aiohttp.request('GET', f"http://politicsandwar.com/api/nation/id={nation_id}&key={self.PNW_API_KEY}") as response:
                json_response = await response.json()
                try:
                    nation_name = json_response['name']
                    leader_name = json_response['leadername']
                    flagurl = json_response['flagurl']
                    print(flagurl)
                except KeyError:
                    await aid_dm.send("I was not able to fetch your nation data.\nRetry and make sure there is nothing but numbers after the `id=` parameter")
                    return

            public_aid_embed = discord.Embed(title=f"Military Aid Request by {ctx.message.author.display_name}", colour=discord.Colour(self.bot.COLOUR))
            public_aid_embed.set_thumbnail(url=flagurl)

            # noinspection PyUnboundLocalVariable
            public_aid_embed.add_field(name="Nation:",
                                       value=f"[{nation_name}]({nation_link})",
                                       inline=False)

            reason = reason.replace("&", "and")
            withdraw_link = f"https://politicsandwar.com/alliance/id=7452&display=bank&w_type=nation&w_recipient={nation_name.replace(' ', '%20')}&w_note=War%20Aid:%20{urllib.parse.quote(reason, safe='')}"
            for res, amo in resource_amount:
                public_aid_embed.add_field(name=f"{res.capitalize()} {self.resource_emoji[res]}",
                                           value=f"{int(amo):,}")

                withdraw_link += f"&w_{res}={amo}"

            public_aid_embed.add_field(name="Reason:",
                                       value=f"{reason}",
                                       inline=False)

            public_aid_embed.add_field(name=f"Withdraw Link:",
                                       value=f"[Here]({withdraw_link})",
                                       inline=True)

            public_aid_embed.add_field(name=f"Status:",
                                       value=f"Unfulfilled",
                                       inline=True)

            public_aid_embed = await self.BANK_REQUEST_CHANNEL.send(content=f"{ctx.message.author.mention}", embed=public_aid_embed)
            await public_aid_embed.add_reaction(EMOJI[':white_check_mark:'])
            await public_aid_embed.add_reaction(EMOJI[':x:'])

            embed = discord.Embed(description="**Successfully created aid request**", colour=discord.Colour(self.bot.COLOUR))
            await aid_dm.send(embed=embed)

    @commands.group()
    @has_permissions(manage_roles=True)
    async def requests(self, ctx):
        if ctx.message.channel != self.BANK_REQUEST_CHANNEL:
            await asyncio.sleep(0.5)
            await ctx.message.delete()
            await ctx.send(f"Please use {self.BANK_REQUEST_CHANNEL.mention}.")
            return

        pending_requests = []
        async for message in ctx.channel.history(limit=200):
            if message.author.id == self.bot.user.id:
                try:
                    aid_request_embed = message.embeds.pop()
                    field_num = len(aid_request_embed.fields)
                    if aid_request_embed.fields[field_num - 1].value == "Unfulfilled":
                        pending_requests.append([message.jump_url, message.content])
                except IndexError:
                    pass

        await asyncio.sleep(0.5)
        await ctx.message.delete()

        if len(pending_requests) == 0:
            embed = discord.Embed(description="**There are no pending requests**", colour=discord.Colour(self.bot.COLOUR))
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(title=f"Pending Requests:", description="Requests made 200 massages or more prior to this are ignored", colour=discord.Colour(self.bot.COLOUR))
        _links = ""
        for x, y in pending_requests:
            _links += f"[Aid request for]({x}) {y}\n"
        embed.add_field(name="Request Links:", value=f"{_links}", inline=False)
        # embed.add_field(name="Number of pending requests:", value=f"{len(pending_requests)}", inline=False)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Bank(bot))
