import asyncio
import json
import re
import urllib.parse
from datetime import datetime

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
from emoji import EMOJI_ALIAS_UNICODE as EMOJI
import validators

from src.models import PnWNation
from src.config import Config
from src.utils.selfdelete import self_delete

config = Config()


class Bank(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.PNW_API_KEY = config.get("server", "PNW_API_KEY")
        self.BANK_REQUEST_ID = int(config.get("server", "BANK_REQUEST_ID"))
        self.BANK_LOGS_ID = int(config.get("server", "BANK_LOGS_ID"))
        bot.loop.create_task(self.startup())

    # noinspection PyAttributeOutsideInit
    async def startup(self):
        await self.bot.wait_until_ready()
        self.resource_emoji = {
            'coal': self.bot.get_emoji(int(config.get("emoji", "coal"))),
            'oil': self.bot.get_emoji(int(config.get("emoji", "oil"))),
            'uranium': self.bot.get_emoji(int(config.get("emoji", "uranium"))),
            'lead': self.bot.get_emoji(int(config.get("emoji", "lead"))),
            'iron': self.bot.get_emoji(int(config.get("emoji", "iron"))),
            'bauxite': self.bot.get_emoji(int(config.get("emoji", "bauxite"))),
            'gasoline': self.bot.get_emoji(int(config.get("emoji", "gasoline"))),
            'munitions': self.bot.get_emoji(int(config.get("emoji", "munitions"))),
            'steel': self.bot.get_emoji(int(config.get("emoji", "steel"))),
            'aluminum': self.bot.get_emoji(int(config.get("emoji", "aluminum"))),
            'food': self.bot.get_emoji(int(config.get("emoji", "food"))),
            'money': EMOJI[':moneybag:']
        }
        self.aid_emoji = {x: self.resource_emoji[x] for x in self.resource_emoji if x not in ['coal', 'oil', 'lead', 'iron', 'bauxite']}
        self.GUILD = self.bot.get_guild(self.bot.GUILD_ID)
        self.BANK_REQUEST_CHANNEL = self.GUILD.get_channel(self.BANK_REQUEST_ID)
        self.BANK_LOGS_CHANNEL = self.GUILD.get_channel(self.BANK_LOGS_ID)

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

        regex = re.compile(r'^<@!?(?P<id>\d*)>$')
        request_author_id = int(regex.match(message.content).group("id"))
        request_author = self.GUILD.get_member(request_author_id)

        if member == request_author and str(payload.emoji) == EMOJI[':x:']:
            await message.delete()

        if not member.guild_permissions.manage_guild:
            return
        else:
            embed = discord.Embed(description=f"placeholder", colour=discord.Colour(self.bot.COLOUR))

            await message.clear_reactions()
            field_num = len(aid_request_embed.fields)
            if str(payload.emoji) == EMOJI[':white_check_mark:']:
                aid_request_embed.set_field_at(index=field_num - 1, name=f"Status:", value=f"Fulfilled by {member.mention}")
                await message.edit(embed=aid_request_embed)
                embed.description = f"**Your [request]({message.jump_url}) was fulfilled by {member.mention}**"

            elif str(payload.emoji) == EMOJI[':x:']:
                aid_request_embed.set_field_at(index=field_num - 1, name=f"Status:", value=f"Denied by {member.mention}")
                await message.edit(embed=aid_request_embed)
                embed.description = f"**Your [request]({message.jump_url}) was denied by {member.mention}**"

            if member != request_author:
                await request_author.send(embed=embed)

    async def resource_getter(self, user, channel, _type, getter_message):

        def check(msg):
            return msg.channel == channel and msg.author == user

        resources_requested = []
        _reactions = await channel.fetch_message(getter_message.id)
        _reactions = _reactions.reactions
        for _reaction in _reactions:
            if _reaction.count == 2 and _reaction.emoji != '✅':
                resources_requested.append(_reaction.emoji)

        resource_amount = []
        for i in resources_requested:
            if _type == 'aid':
                resource = list(self.aid_emoji.keys())[list(self.aid_emoji.values()).index(i)]
            else:
                resource = list(self.resource_emoji.keys())[list(self.resource_emoji.values()).index(i)]

            if _type == 'aid':
                embed_argument = 'the desired'
                common_argument = 'Aid Request'
            elif _type == 'deposit':
                embed_argument = 'depositing'
                common_argument = 'Deposit'
            else:
                embed_argument = 'the'
                common_argument = 'Action'

            embed = discord.Embed(description=f"**Type {embed_argument} amount of {resource}** {i}", colour=discord.Colour(self.bot.COLOUR))
            await channel.send(embed=embed)

            number_of_tries = 5
            for x in range(number_of_tries):
                if x == 1:
                    await channel.send("Make sure to not include any commas")
                if x == number_of_tries - 1:
                    await channel.send("This is your last try!")
                try:
                    message = await self.bot.wait_for('message', timeout=60.0, check=check)
                except asyncio.TimeoutError:
                    await channel.send('You took too long...')
                    return
                else:
                    try:
                        amount = int(message.content)
                        if amount < 0:
                            await channel.send("Haha, very funny. Now please type a positive number :)")
                            del amount
                        elif amount > 100000000000 and _type == 'aid':
                            await channel.send("In your dreams, try again")
                            del amount
                        else:
                            break
                    except ValueError or TypeError:
                        if message.content == "cancel":
                            await channel.send(f"{common_argument} Canceled")
                            return
                        elif message.content == "retry":
                            # TODO
                            await channel.send(f"{common_argument} Canceled. For now you will have to use the command again")
                            return
                        else:
                            if x == number_of_tries - 1:
                                await channel.send("You have exceeded your number of tries. Use the command again if you wish to retry")
                                return
                            else:
                                await channel.send("Please type an integer")

            if "amount" in locals():
                # noinspection PyUnboundLocalVariable
                resource_amount.append((f"{resource}", f"{amount}"))
            else:
                return
        return resource_amount

    @staticmethod
    def reaction_check_constructor(ctx, channel):
        def reaction_check(reaction, user):
            return (str(reaction.emoji) == EMOJI[':white_check_mark:'] or str(reaction.emoji) == EMOJI[':x:']) and \
                   (user == ctx.message.author and reaction.message.channel == channel)
        return reaction_check

    @commands.command()
    async def aid(self, ctx):
        """
        Request military aid from Alliance
        """
        if ctx.message.channel != self.BANK_REQUEST_CHANNEL:
            await self_delete(ctx)
            await ctx.send(f"Please use {self.BANK_REQUEST_CHANNEL.mention}.")
            return

        aid_dm = await ctx.message.author.create_dm()

        aid_embed = discord.Embed(title="Military Aid Request", colour=discord.Colour(self.bot.COLOUR))
        aid_embed.add_field(name="**Process:**",
                            value="React to the resources you would like to request below,\nonce you have selected all of them react to the checkmark :white_check_mark:\n\u200b\nYou will then be prompted to give your requested values.",
                            inline=False)

        aid_embed.add_field(name="**Cancel/Retry:**",
                            value="If at anytime you wish to cancel the request just type `cancel`, or `retry` if you entered any value incorrectly.",
                            inline=False)

        aid_embed = await aid_dm.send(embed=aid_embed)

        await self_delete(ctx)

        for _, emoji in self.aid_emoji.items():
            await aid_embed.add_reaction(emoji)
        await aid_embed.add_reaction(EMOJI[':white_check_mark:'])

        reaction_check = self.reaction_check_constructor(ctx, aid_dm)

        # noinspection PyShadowingNames
        def check(msg):
            return msg.channel == aid_dm and msg.author == ctx.message.author

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=reaction_check)
        except asyncio.TimeoutError:
            await aid_dm.send('You took too long...')
        else:
            resource_amount = await self.resource_getter(user=ctx.message.author, channel=aid_dm, _type='aid', getter_message=aid_embed)
            if resource_amount is None or not resource_amount:
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

            nation_object = await PnWNation.get_or_none(pk=ctx.message.author.id)
            if nation_object is None:
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
            else:
                nation_id = nation_object.nation_id
                nation_link = f"https://politicsandwar.com/nation/id={nation_id}"

            # noinspection PyUnboundLocalVariable
            async with aiohttp.request('GET', f"http://politicsandwar.com/api/nation/id={nation_id}&key={self.PNW_API_KEY}") as response:
                json_response = await response.json()
                try:
                    nation_name = json_response['name']
                    leader_name = json_response['leadername']
                    flagurl = json_response['flagurl']
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
            withdraw_link = f"https://politicsandwar.com/alliance/id=7452&display=bank&w_type=nation&w_recipient={nation_name.replace(' ', '%20')}&w_note=War%20Aid:%20{urllib.parse.quote(reason, safe='/')}"
            for res, amo in resource_amount:
                public_aid_embed.add_field(name=f"{res.capitalize()} {self.aid_emoji[res]}",
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

    @commands.command()
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
        await ctx.send(embed=embed)

    @commands.command()
    async def deposit(self, ctx):
        # noinspection PyShadowingNames
        async def check_transactions():
            async with aiohttp.request('GET', f"https://politicsandwar.com/api/v2/nation-bank-recs/{self.PNW_API_KEY}/&nation_id={nation_object.nation_id}") as response:
                json_response = await response.json()
                try:
                    records = json_response['data']
                except KeyError:
                    await deposit_dm.send(f"I was not able to fetch bank records, please contact a Gov member to inform about this issue.")
                    return
                max_days_passed = 3
                records = [record for record in records if
                           record['receiver_type'] == 2 and
                           record['receiver_id'] == self.bot.AA_ID and
                           (datetime.utcnow() - datetime.strptime(record['tx_datetime'], '%Y-%m-%d %H:%M:%S')).days < max_days_passed and
                           record['note'].lower() == "deposit"]
                if len(records) == 0:
                    await deposit_dm.send(f'There are no deposits in the last {max_days_passed} days.')
                    return
                records.sort(key=lambda d: datetime.strptime(d['tx_datetime'], '%Y-%m-%d %H:%M:%S'), reverse=True)
                for i, record in list(enumerate(records)):
                    embed = discord.Embed(title="Is this your deposit?", colour=discord.Colour(self.bot.COLOUR))
                    embed.add_field(name="Nation Link:",
                                    value=f"https://politicsandwar.com/nation/id={nation_object.nation_id}",
                                    inline=False)
                    resources_sent = [(resource, record[resource]) for resource in record if
                                      resource in ['money', 'coal', 'oil', 'uranium', 'lead', 'iron', 'bauxite', 'gasoline', 'munitions', 'steel',
                                                   'aluminum', 'food'] and record[resource] != 0]
                    for res, amo in resources_sent:
                        embed.add_field(name=f"{res.capitalize()} {self.resource_emoji[res]}",
                                        value=f"{int(amo):,}")
                    embed.add_field(name="Date:",
                                    value=f"{record['tx_datetime']}")
                    is_this_embed = await deposit_dm.send(embed=embed)
                    await is_this_embed.add_reaction(EMOJI[':white_check_mark:'])
                    await is_this_embed.add_reaction(EMOJI[':x:'])

                    try:
                        reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=reaction_check)
                    except asyncio.TimeoutError:
                        await deposit_dm.send('You took too long...')
                        return
                    else:
                        if reaction.emoji == EMOJI[':white_check_mark:']:
                            chosen_record = record
                            break
                        else:
                            if i == len(records) - 1:
                                await deposit_dm.send(f'There are no previous deposits in the last {max_days_passed} days.')
                                return
                            else:
                                continue

                # noinspection PyAssignmentToLoopOrWithParameter
                async with aiohttp.request('POST', f"{self.bot.API_URL}/bank-deposit", json=chosen_record, headers={'x-api-key': self.bot.API_KEY}) as response:
                    json_response = await response.text()
                    print(json_response)
                    if response.status == 201:
                        deposited_embed = discord.Embed(description=f"**Successfully registered your deposit.**", colour=discord.Colour(self.bot.COLOUR))
                    elif response.status == 409:
                        deposited_embed = discord.Embed(description=f"**This deposit has already been registered.**", colour=discord.Colour(self.bot.COLOUR))
                    await deposit_dm.send(embed=deposited_embed)

        await self_delete(ctx)
        deposit_dm = await ctx.message.author.create_dm()

        nation_object = await PnWNation.get_or_none(pk=ctx.message.author.id)
        if nation_object is None:
            deposit_dm.send("Your nation is not in our database. please ask for someone to link your nation and try again.")
            return

        has_deposited_embed = discord.Embed(description=f"**Have you deposited on the game already?**", colour=discord.Colour(self.bot.COLOUR))
        has_deposited_embed = await deposit_dm.send(embed=has_deposited_embed)
        await has_deposited_embed.add_reaction(EMOJI[':white_check_mark:'])
        await has_deposited_embed.add_reaction(EMOJI[':x:'])

        reaction_check = self.reaction_check_constructor(ctx, deposit_dm)

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=reaction_check)
        except asyncio.TimeoutError:
            await deposit_dm.send('You took too long...')
        else:
            if reaction.emoji == EMOJI[':white_check_mark:']:
                await check_transactions()
            else:
                deposit_creation_embed = discord.Embed(title="Deposit Form", colour=discord.Colour(self.bot.COLOUR))
                deposit_creation_embed.add_field(name="**Process:**",
                                                 value="React to the resources you would like to deposit below,\nonce you have selected all of them react to the checkmark :white_check_mark:\n\u200b\n"
                                                       "You will then be prompted to give your depositing values.",
                                                 inline=False)

                deposit_creation_embed.add_field(name="**Cancel/Retry:**",
                                                 value="If at anytime you wish to cancel the deposit just type `cancel`, or `retry` if you entered any value incorrectly.",
                                                 inline=False)

                deposit_creation_embed = await deposit_dm.send(embed=deposit_creation_embed)

                for _, emoji in self.resource_emoji.items():
                    await deposit_creation_embed.add_reaction(emoji)
                await deposit_creation_embed.add_reaction(EMOJI[':white_check_mark:'])

                try:
                    await self.bot.wait_for('reaction_add', timeout=60.0, check=reaction_check)
                except asyncio.TimeoutError:
                    await deposit_dm.send('You took too long...')
                else:
                    resource_amount = await self.resource_getter(user=ctx.message.author, channel=deposit_dm, _type='deposit', getter_message=deposit_creation_embed)
                    if resource_amount is None:
                        return

                    embed = discord.Embed(title="Confirm Deposit", colour=discord.Colour(self.bot.COLOUR))
                    embed.set_footer(text="Only react with ✅ once you have deposited in-game.")

                    deposit_link = f"https://politicsandwar.com/alliance/id=7452&display=bank&d_type=nation&d_note=Deposit"
                    for res, amo in resource_amount:
                        embed.add_field(name=f"{res.capitalize()} {self.resource_emoji[res]}",
                                        value=f"{int(amo):,}")
                        deposit_link += f"&d_{res}={amo}"

                    embed.add_field(name=f"Deposit Link:",
                                    value=f"[Here]({deposit_link})",
                                    inline=False)
                    embed = await deposit_dm.send(embed=embed)
                    await embed.add_reaction(EMOJI[':white_check_mark:'])

                    try:
                        await self.bot.wait_for('reaction_add', timeout=120.0, check=reaction_check)
                    except asyncio.TimeoutError:
                        await deposit_dm.send('You took too long...')
                    else:
                        await check_transactions()

    @commands.command()
    async def withdraw(self, ctx):
        await self_delete(ctx)
        withdraw_dm = await ctx.message.author.create_dm()

        nation_object = await PnWNation.get_or_none(pk=ctx.message.author.id)
        if nation_object is None:
            withdraw_dm.send("Your nation is not in our database. please ask for someone to link your nation and try again.")
            return

        reaction_check = self.reaction_check_constructor(ctx, withdraw_dm)

        withdraw_embed = discord.Embed(title="Withdraw Form", colour=discord.Colour(self.bot.COLOUR))
        withdraw_embed.add_field(name="**Process:**",
                                 value="React to the resources you would like to withdraw below,\nonce you have selected all of them react to the checkmark :white_check_mark:\n\u200b\n"
                                       "You will then be prompted to give your withdrawing values.",
                                 inline=False)

        withdraw_embed.add_field(name="**Cancel/Retry:**",
                                 value="If at anytime you wish to cancel the withdraw just type `cancel`, or `retry` if you entered any value incorrectly.",
                                 inline=False)

        withdraw_embed = await withdraw_dm.send(embed=withdraw_embed)

        for _, emoji in self.resource_emoji.items():
            await withdraw_embed.add_reaction(emoji)
        await withdraw_embed.add_reaction(EMOJI[':white_check_mark:'])

        try:
            await self.bot.wait_for('reaction_add', timeout=60.0, check=reaction_check)
        except asyncio.TimeoutError:
            await withdraw_dm.send('You took too long...')
        else:
            resource_amount = await self.resource_getter(user=ctx.message.author, channel=withdraw_dm, _type='withdraw', getter_message=withdraw_embed)
            if resource_amount is None:
                return
            resource_amount.append(('nationid', nation_object.nation_id))
            data = dict(resource_amount)
            async with aiohttp.request('POST', f"{self.bot.API_URL}/bank-withdraw", json=data, headers={'x-api-key': self.bot.API_KEY}) as response:
                json_response = await response.text()
                print(json_response)
                if response.status == 201:
                    withdrew_embed = discord.Embed(description=f"**Successfully registered your withdraw request.**", colour=discord.Colour(self.bot.COLOUR))
                elif response.status == 403:
                    withdrew_embed = discord.Embed(description=f"**You requested more of a resource then you have _available_**", colour=discord.Colour(self.bot.COLOUR))
                elif response.status == 404:
                    withdrew_embed = discord.Embed(description=f"**You don't have any holdings to withdraw form**", colour=discord.Colour(self.bot.COLOUR))
                await withdraw_dm.send(embed=withdrew_embed)

    @commands.command(aliases=['deposits'])
    async def holdings(self, ctx):
        await self_delete(ctx)
        holdings_dm = await ctx.message.author.create_dm()

        nation_object = await PnWNation.get_or_none(pk=ctx.message.author.id)
        if nation_object is None:
            holdings_dm.send("Your nation is not our database. please ask for someone to link your nation and try again.")
            return

        data = {
            'nationid': nation_object.nation_id
        }
        async with aiohttp.request('GET', f"{self.bot.API_URL}/bank-holdings", json=data, headers={'x-api-key': self.bot.API_KEY}) as response:
            json_response = await response.text()
            if response.status == 404:
                await holdings_dm.send("You dont have any holdings.")
                return

        data = json.loads(json_response)
        data.pop('nation_id')
        data.pop('last_updated')
        holdings_embed = discord.Embed(title="Holdings:", colour=discord.Colour(self.bot.COLOUR))
        holdings_embed.add_field(name="Nation Link:",
                                 value=f"https://politicsandwar.com/nation/id={nation_object.nation_id}",
                                 inline=False)
        for res in data:
            holdings_embed.add_field(name=f"{res.capitalize()} {self.resource_emoji[res]}",
                                     value=f"{int(data[res]):,}", inline=True)

        await holdings_dm.send(embed=holdings_embed)

    # @commands.command()
    # async def loan(self, ctx):
    #     await self_delete(ctx)
    #     loan_dm = await ctx.message.author.create_dm()
    #
    #     nation_object = await PnWNation.get_or_none(pk=ctx.message.author.id)
    #     if nation_object is None:
    #         loan_dm.send("Your nation is not our database. please ask for someone to link your nation and try again.")
    #         return
    #
    #     def reaction_check(reaction, user):
    #         return (str(reaction.emoji) == EMOJI[':white_check_mark:'] or str(reaction.emoji) == EMOJI[':x:']) and \
    #                (user == ctx.message.author and reaction.message.channel == loan_dm)
    #
    #     loan_embed = discord.Embed(title="Loan Form", colour=discord.Colour(self.bot.COLOUR))
    #     loan_embed.add_field(name="**Process:**",
    #                          value="React to the resources you would like to withdraw below,\nonce you have selected all of them react to the checkmark :white_check_mark:\n\u200b\n"
    #                                "You will then be prompted to give your withdrawing values.",
    #                          inline=False)
    #
    #     loan_embed.add_field(name="**Cancel/Retry:**",
    #                          value="If at anytime you wish to cancel the withdraw just type `cancel`, or `retry` if you entered any value incorrectly.",
    #                          inline=False)
    #
    #     loan_embed = await loan_dm.send(embed=loan_embed)
    #
    #     for _, emoji in self.resource_emoji.items():
    #         await withdraw_embed.add_reaction(emoji)
    #     await withdraw_embed.add_reaction(EMOJI[':white_check_mark:'])
    #
    #     try:
    #         await self.bot.wait_for('reaction_add', timeout=60.0, check=reaction_check)
    #     except asyncio.TimeoutError:
    #         await withdraw_dm.send('You took too long...')
    #     else:
    #         resource_amount = await self.resource_getter(user=ctx.message.author, channel=withdraw_dm, _type='withdraw', getter_message=withdraw_embed)
    #         if resource_amount is None:
    #             return

    @commands.command()
    async def available_holdings(self, ctx):
        await self_delete(ctx)
        holdings_dm = await ctx.message.author.create_dm()

        nation_object = await PnWNation.get_or_none(pk=ctx.message.author.id)
        if nation_object is None:
            holdings_dm.send("Your nation is not our database. please ask for someone to link your nation and try again.")
            return

        data = {
            'nationid': nation_object.nation_id
        }
        async with aiohttp.request('GET', f"{self.bot.API_URL}/bank-ava-holdings", json=data, headers={'x-api-key': self.bot.API_KEY}) as response:
            json_response = await response.text()
            if response.status == 404:
                await holdings_dm.send("You dont have any holdings.")
                return

        data = json.loads(json_response)
        data.pop('nation_id')
        holdings_embed = discord.Embed(title="Available Holdings:", colour=discord.Colour(self.bot.COLOUR))
        holdings_embed.add_field(name="Nation Link:",
                                 value=f"https://politicsandwar.com/nation/id={nation_object.nation_id}",
                                 inline=False)
        for res in data:
            holdings_embed.add_field(name=f"{res.capitalize()} {self.resource_emoji[res]}",
                                     value=f"{int(data[res]):,}", inline=True)

        await holdings_dm.send(embed=holdings_embed)


def setup(bot):
    bot.add_cog(Bank(bot))
