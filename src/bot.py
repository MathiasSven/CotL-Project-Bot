import os
import discord
from discord.ext import commands, tasks

intents = discord.Intents.all()


class MyBot(commands.Bot):

    def __init__(self, **options):
        super().__init__(command_prefix=os.getenv('PREFIX'), intents=intents)
        self.GUILD_ID = int(os.getenv('GUILD_ID'))
        self.AUTO_ROLE_ID = int(os.getenv('AUTO_ROLE_ID'))
        self.APPLICATION_CHANNEL_ID = int(os.getenv('APPLICATION_CHANNEL_ID'))

    # noinspection PyAttributeOutsideInit,PyTypeChecker
    async def on_ready(self):
        self.GUILD = self.get_guild(self.GUILD_ID)
        self.AUTO_ROLE = self.GUILD.get_role(self.AUTO_ROLE_ID)
        self.SYSTEM_CHANNEL = self.GUILD.system_channel
        self.APPLICATION_CHANNEL = self.GUILD.get_channel(self.APPLICATION_CHANNEL_ID)

        # self.test.start()

        print("Bot is Ready!")

    async def on_member_join(self, member):
        await member.add_roles(self.AUTO_ROLE, reason="Testing", atomic=True)
        await self.SYSTEM_CHANNEL.send(
            f"Salutations {member.mention}, welcome to **Children of the Light**! If you wish to Join please follow the instructions in {self.APPLICATION_CHANNEL.mention}. "
            f"For any of your FA concerns please speak with Keegoz or LeftBehind.\n\nPraise be! For the light has shined upon you!")

    async def on_member_remove(self, member):
        pass

    async def on_member_update(self, before, after):
        pass

    # @tasks.loop(seconds=10)
    # async def test(self):
    #     print("test")

    def run_bot(self):
        self.run(os.getenv('TOKEN'))


MyBot().run_bot()
