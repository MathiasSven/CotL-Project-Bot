import os
import aiohttp
import json

import discord
from discord.ext import commands, tasks

from emoji import EMOJI_ALIAS_UNICODE as EMOJI

from src.config import Config

from src.models import PnWNation

directory = os.path.dirname(os.path.realpath(__file__))
config = Config()


class Tasks(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.PNW_API_KEY = config.get("server", "PNW_API_KEY")
        self.AA_ID = config.get("server", "AA_ID")

        self.post_latest_aa_wars.start()

    @commands.Cog.listener()
    async def on_ready(self):
        print('Tasks Cog is loaded')

    @tasks.loop(minutes=5)
    async def post_latest_aa_wars(self):
        async with aiohttp.request('GET', f"http://politicsandwar.com/api/wars/500&alliance_id={self.AA_ID}&key={self.PNW_API_KEY}") as response:
            try:
                json_response = json.loads(await response.text())
            except json.JSONDecodeError:
                await self.bot.MILCON_BOT_CHANNEL.send(f"<@{self.bot.ADMIN_ID}> There was a problem.")
                with open(f'{directory}/problem.json', 'w', encoding='utf-8') as f:
                    f.write(await response.text())
                    self.post_latest_aa_wars.stop()
                    return
            active_wars = {"wars": [war for war in json_response["wars"] if war["status"] == "Active"]}

            try:
                with open(f'{directory}/alliancewars.json', 'r', encoding='utf-8') as f:
                    try:
                        previous_active_wars = json.load(f)
                    except json.decoder.JSONDecodeError:
                        previous_active_wars = None
            except IOError:
                previous_active_wars = None

            with open(f'{directory}/alliancewars.json', 'w+', encoding='utf-8') as f:
                if previous_active_wars:
                    difference = {"wars": [war for war in active_wars["wars"] if war["warID"] not in [war["warID"] for war in previous_active_wars["wars"]]]}
                else:
                    difference = active_wars
                json.dump(active_wars, f, ensure_ascii=False, indent=4)

        class CreateEmbed:
            def __init__(self, war: dict, main_nation: dict, attacker: bool, rival_nation: dict, cog_instance: Tasks, user_pnw):
                war_type = "New" + (" Offensive " if attacker else " Defensive ") + "War"
                if user_pnw:
                    self.user_pnw = f"<@{user_pnw.discord_user_id}>"
                else:
                    self.user_pnw = "Not Found"
                self.cog_instance = cog_instance
                self.embed = discord.Embed(description=f"[{main_nation['alliance']}](https://politicsandwar.com/alliance/id={main_nation['allianceid']}) - "
                                                       f"[{war_type}](https://politicsandwar.com/nation/war/timeline/war={war['warID']})",
                                           colour=discord.Colour(self.cog_instance.bot.COLOUR))

                self.add_fields(main_nation, True, attacker)
                self.add_fields(rival_nation, False, not attacker)

            def add_fields(self, nation, main: bool, attacker: bool):

                self.embed.add_field(name=f"{'Attacking' if attacker else 'Defending'} Nation",
                                     value=f"[{nation['name']}](https://politicsandwar.com/nation/id={nation['nationid']}) - "
                                           f"[{nation['leadername']}](https://politicsandwar.com/inbox/message/receiver={nation['leadername'].replace(' ', '%20')})")

                if main:
                    self.embed.add_field(name="Discord User", value=self.user_pnw)

                self.embed.add_field(name="Alliance", value=f"[{nation['alliance']}](https://politicsandwar.com/alliance/id={nation['allianceid']})"
                                                            f"{' - This Nation is an Applicant!' if nation['allianceposition'] == '1' else ''}", inline=False)
                self.embed.add_field(name="Score", value=f"{nation['score']}", inline=True)
                self.embed.add_field(name=f"Cities", value=f"{nation['cities']} {EMOJI[':cityscape:']}", inline=True)
                self.embed.add_field(name="War Policy", value=f"{nation['war_policy']} {self.cog_instance.war_policy_emoji[nation['war_policy'].lower()]}", inline=True)
                self.embed.add_field(name="War Range", value=f"Defensive {'{:.2f}'.format(0.57143 * float(nation['score']))} - {'{:.2f}'.format(1.33333 * float(nation['score']))}\n"
                                                             f"Offensive {'{:.2f}'.format(0.75000 * float(nation['score']))} - {'{:.2f}'.format(1.75000 * float(nation['score']))}", inline=False)
                self.embed.add_field(name="Open Slots", value=f"{5 - nation['offensivewars']} {EMOJI[':crossed_swords:']} / {3 - nation['defensivewars']} {EMOJI[':shield:']}", inline=True)
                self.embed.add_field(name="Missiles", value=f"{nation['missiles']}", inline=True)
                self.embed.add_field(name="Nukes", value=f"{nation['nukes']}", inline=True)
                self.embed.add_field(name="Army Values",
                                     value=f"```{'{:,.2f}'.format(int(nation['soldiers']))} 💂| "
                                           f"{'{:,.2f}'.format(int(nation['tanks']))} ⚙| "
                                           f"{'{:,.2f}'.format(int(nation['aircraft']))} ✈| "
                                           f"{'{:,.2f}'.format(int(nation['ships']))} ⛵```",
                                     inline=False)

            @property
            def result(self):
                return self.embed

        for war in difference["wars"]:
            async with aiohttp.request('GET', f"http://politicsandwar.com/api/nation/id={war['attackerID']}&key={self.PNW_API_KEY}") as response:
                attacker_nation = json.loads(await response.text())
            async with aiohttp.request('GET', f"http://politicsandwar.com/api/nation/id={war['defenderID']}&key={self.PNW_API_KEY}") as response:
                defender_nation = json.loads(await response.text())

            if str(attacker_nation["allianceid"]) == self.AA_ID:
                _user_pnw = await PnWNation.get_or_none(nation_id=attacker_nation['nationid'])
                embed = CreateEmbed(war=war, main_nation=attacker_nation, attacker=True, rival_nation=defender_nation, cog_instance=self, user_pnw=_user_pnw).result
                embed.set_thumbnail(url="https://images.emojiterra.com/twitter/v13.0/512px/2694.png")
            else:
                _user_pnw = await PnWNation.get_or_none(nation_id=defender_nation['nationid'])
                embed = CreateEmbed(war=war, main_nation=defender_nation, attacker=False, rival_nation=attacker_nation, cog_instance=self, user_pnw=_user_pnw).result
                embed.set_thumbnail(url="https://images.emojiterra.com/twitter/v13.0/512px/1f6e1.png")

            await self.bot.MILCON_BOT_CHANNEL.send(embed=embed)

    # noinspection PyAttributeOutsideInit
    @post_latest_aa_wars.before_loop
    async def before_tasks(self):
        print('Tasks are waiting...')
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
            'arcane': self.bot.get_emoji(int(config.get("emoji", "arcane")))
        }


def setup(bot):
    bot.add_cog(Tasks(bot))
