import os
import aiohttp
import aiofiles
from typing import Union
from emoji import EMOJI_ALIAS_UNICODE as EMOJI

import discord
from discord.ext import commands

from src.models import PnWNation
from src.config import Config
from src.utils.inputparse import InputParser
from src.utils.selfdelete import self_delete

from discord_slash.cog_ext import cog_context_menu, cog_slash
from discord_slash.context import MenuContext, SlashContext
from discord_slash.model import ContextMenuType, SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option

directory = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
config = Config()

guild_ids = [int(config.get("server", "GUILD_ID"))]


class Utils(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.PNW_API_KEY = config.get("server", "PNW_API_KEY")
        bot.loop.create_task(self.startup())

    # noinspection PyAttributeOutsideInit
    async def startup(self):
        await self.bot.wait_until_ready()
        self.war_policy_emoji = {
            'attrition': self.bot.get_emoji(int(config.get("emoji", "attrition"))),
            'turtle': self.bot.get_emoji(int(config.get("emoji", "turtle"))),
            'blitzkrieg': self.bot.get_emoji(int(config.get("emoji", "blitzkrieg"))),
            'fortress': self.bot.get_emoji(int(config.get("emoji", "fortress"))),
            'moneybags': self.bot.get_emoji(int(config.get("emoji", "moneybags"))),
            'pirate': self.bot.get_emoji(int(config.get("emoji", "pirate"))),
            'tactician': self.bot.get_emoji(int(config.get("emoji", "tactician"))),
            'guardian': self.bot.get_emoji(int(config.get("emoji", "guardian"))),
            'covert': self.bot.get_emoji(int(config.get("emoji", "covert"))),
            'arcane': self.bot.get_emoji(int(config.get("emoji", "arcane"))),
        }
        self.GUILD = self.bot.get_guild(self.bot.GUILD_ID)

    @commands.Cog.listener()
    async def on_ready(self):
        print('Utils Cog is loaded')

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        pass

    @staticmethod
    async def generic_nation_link(ctx: Union[commands.Context, SlashContext, MenuContext], user: Union[discord.Member, str, None] = None):
        kwargs = {}

        if isinstance(ctx, commands.Context):
            if user == "me":
                user = ctx.message.author.id
            else:
                parsed_input = InputParser(ctx)
                user = await parsed_input.user_mention_id(user)
                if user is None:
                    return

        elif isinstance(ctx, SlashContext):
            if user is None:
                user = ctx.author_id
            else:
                user = user.id
                kwargs = {'hidden': True}

        elif isinstance(ctx, MenuContext):
            user = ctx.target_id
            kwargs = {'hidden': True}

        user_pnw = await PnWNation.get_or_none(discord_user_id=user)
        if user_pnw is None:
            await ctx.send("User with the given ID is not in the Database.", **kwargs)
            return
        else:
            await ctx.send(f"https://politicsandwar.com/nation/id={user_pnw.nation_id}", **kwargs)

    @commands.command(name="nation_link", aliases=['nl', 'nation'])
    async def normal_nation_link(self, ctx, user='f'):
        await self.generic_nation_link(ctx, user)

    @cog_slash(name="nation_link",
               description="Returns a user's nation if they are linked.",
               guild_ids=guild_ids,
               options=[
                   create_option(
                       name="user",
                       description="The user to return a nation link from, yours if empty.",
                       option_type=SlashCommandOptionType.USER,
                       required=False
                   )
               ])
    async def slash_nation_link(self, ctx: SlashContext, user=None):
        await self.generic_nation_link(ctx, user)

    @cog_context_menu(target=ContextMenuType.USER, name="Nation Link", guild_ids=guild_ids)
    async def context_nation_link(self, ctx: MenuContext):
        await self.generic_nation_link(ctx)

    @commands.command(aliases=['du', 'au'])
    async def associated_user(self, ctx, nation_id="f"):
        try:
            int(nation_id)
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

    @commands.command(aliases=['mili'])
    async def militarization(self, ctx, alliance_id=None):
        from random import randint
        if not alliance_id:
            alliance_id = self.bot.AA_ID
        else:
            try:
                alliance_id = int(alliance_id)
            except ValueError:
                await ctx.send("Invalid alliance ID.")
                return

        async with aiohttp.request('GET', f"https://checkapi.bsnk.dev/getChart?allianceID={alliance_id}") as response:
            if response.status != 200:
                await ctx.send("Alliance with given ID not found.")
                return
            else:
                pass

            chart_file_name = f"{randint(1, 1000000)}.png"
            chart_file_path = f"{directory}/militarization/{chart_file_name}"
            async with aiofiles.open(chart_file_path, "wb") as f:
                await f.write(await response.read())

        async with aiohttp.request('GET', f"http://politicsandwar.com/api/alliance/id={alliance_id}&key={self.PNW_API_KEY}") as response:
            json_response = await response.json()
            try:
                json_response['success']
            except KeyError:
                await ctx.send("Something went wrong")
                return
            else:
                pass

        image_file = discord.File(chart_file_path, filename=chart_file_name)

        militarization_embed = discord.Embed(title=json_response['name'], url=f"https://politicsandwar.com/alliance/id={json_response['allianceid']}", colour=discord.Colour(self.bot.COLOUR))
        militarization_embed.set_thumbnail(url=json_response["flagurl"])
        militarization_embed.add_field(name="\u200b", value="**Militarization Chart:**")
        militarization_embed.set_image(url=f'attachment://{chart_file_name}')

        await ctx.send(file=image_file, embed=militarization_embed)

        os.remove(chart_file_path)

    @commands.command(aliases=['issuemmr'])
    async def incorrect_mmr(self, ctx, mmr):
        query = """
        {
          nations(alliance_id: 7452, first: 300, vmode: false) {
            data {
              id
              alliance_position
              cities {
                barracks
                factory
                airforcebase
                drydock        
              }
              soldiers
              tanks
              aircraft
              ships
            }
          }
        }
        """
        async with aiohttp.request('POST', f"https://api.politicsandwar.com/graphql?api_key={self.PNW_API_KEY}", json={'query': query}) as response:
            data = await response.json()
            imp_mmr_issue_list = []
            mmr_imp_list = ["barracks", "factory", "airforcebase", "drydock"]
            a_p_enum = {"NOALLIANCE": 0, "APPLICANT": 1, "MEMBER": 2, "OFFICER": 3, "HEIR": 4, "LEADER": 5}
            for nation in data["data"]["nations"]["data"]:
                if a_p_enum[nation["alliance_position"]] == 1:
                    continue
                imp_status = True
                for city in nation["cities"]:
                    for i, building_type in enumerate(city):
                        if int(city[mmr_imp_list[i]]) != int(mmr[i]):
                            imp_status = False
                            break
                    else:
                        continue
                    break
                if not imp_status:
                    imp_mmr_issue_list.append(nation["id"])

            msg = "**Incorrect MMR Users:**\n"
            for nation_id in imp_mmr_issue_list:
                user_pnw = await PnWNation.get_or_none(nation_id=int(nation_id))
                if user_pnw is None:
                    msg += f"Nation of ID \"{nation_id}\" has no associated user in the Database.\n"
                    # await ctx.send(f"Nation of ID \"{nation_id}\" has no associated user in the Database.")
                else:
                    msg += f"<@{user_pnw.discord_user_id}>\n"
                    # mentions = discord.AllowedMentions(users=False)
                    # await ctx.send(f"<@{user_pnw.discord_user_id}>", allowed_mentions=mentions)
            if not imp_mmr_issue_list:
                msg += "None"
            mentions = discord.AllowedMentions(users=False)
            await ctx.send(msg, allowed_mentions=mentions)

    # @commands.command(aliases=['rp'])
    # async def report(self, ctx, reference):
    #     pass

    # @commands.command(aliases=['mag', 'm', 'warinfo'])
    # async def magnify(self, ctx, nation_link):
    #     await self_delete(ctx)
    #
    #     parsed_input = InputParser(ctx)
    #     nation_id = await parsed_input.nation_link_validator(nation_link)
    #     if nation_id is None:
    #         return
    #
    #     async with aiohttp.request('GET', http://politicsandwar.com/api/nation/id={nation_id}&key={self.PNW_API_KEY}) as response:
    #         json_response = await response.json()
    #         try:
    #             success = json_response['success']
    #         except KeyError:
    #             await ctx.send("I was not able to fetch the nation data.\nRetry and make sure there is nothing but numbers after the `id=` parameter")
    #             return
    #         else:
    #             nation_name = json_response['name']
    #             color = json_response['color']
    #             war_policy = json_response['war_policy']
    #             alliance = json_response['alliance']
    #             flagurl = json_response['flagurl']
    #             leader_name = json_response['leadername']
    #             city_count = json_response['cities']
    #             nation_score = json_response['score']
    #             average_infra = json_response['totalinfrastructure'] / city_count
    #             if json_response['missilelpad'] == 1:
    #                 missile_capability = True
    #             if json_response['nuclearresfac'] == 1:
    #                 nuclear_capability = True
    #             open_slots = 3 - json_response['defensivewars']
    #
    #     war_info_embed = discord.Embed(title=f"Information on {leader_name}", colour=discord.Colour(self.bot.COLOUR))
    #     war_info_embed.set_thumbnail(url=flagurl)
    #
    #     # noinspection PyUnboundLocalVariable
    #     war_info_embed.add_field(name="Nation:",
    #                              value=f"[{nation_name}]({nation_link})",
    #                              inline=True)
    #
    #     war_info_embed.add_field(name="Cities:",
    #                              value=str(city_count),
    #                              inline=True)
    #
    #     war_info_embed.add_field(name="Score:",
    #                              value=str(nation_score),
    #                              inline=False)
    #
    #     embed.set_footer(text="Investigated by Mathias Sven", icon_url="https://cdn.discordapp.com/embed/avatars/0.png")
    #
    #     embed.add_field(name="Nation:", value="Nurmengard", inline=True)
    #     embed.add_field(name="Alliance:", value="Children of the Light", inline=True)
    #     embed.add_field(name="Cities:", value="11", inline=True)
    #     embed.add_field(name="Score:", value="2546.80", inline=True)
    #     embed.add_field(name="Avarage Infra:", value="1430.00", inline=True)
    #     embed.add_field(name="War Policy", value="Tactician", inline=True)
    #     embed.add_field(name="Army Values:", value="```222,222 💂| 20,000 ⚙| 1,200 ✈| 200 ⛵```", inline=True)
    #     embed.add_field(name="Declare Link:", value="Here", inline=True)
    #     embed.add_field(name="Open Slots:", value="2/3", inline=True)
    #
    #     declare_link = f"https://politicsandwar.com/nation/war/declare/id={nation_id}"
    #
    #
    #     war_info_embed.add_field(name=f"Declare Link:",
    #                              value=f"[Here]({declare_link})",
    #                              inline=True)
    #
    #     war_info_embed.add_field(name=f"Open Slots:",
    #                              value=f"{'None' if open_slots == 0 else f'{open_slots}/3'}",
    #                              inline=True)
    #
    #     war_info_embed = await ctx.send(embed=war_info_embed)
    #     await war_info_embed.add_reaction(EMOJI[':white_check_mark:'])


def setup(bot):
    bot.add_cog(Utils(bot))
