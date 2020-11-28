import asyncio
import datetime

import discord
from discord.ext import commands
from src.models import Reminder
from src.utils.timers import Timer


class Reminders(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        bot.loop.create_task(self.startup())

    async def startup(self):
        await self.bot.wait_until_ready()
        _reminders = await Reminder.all()
        for object in _reminders:
            if object.date_due < datetime.datetime.utcnow():
                await object.delete()
                continue
            Timer(self.bot, "reminder", object.date_due, args=(object.id,)).start()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{__class__.__name__} Cog is loaded')

    @commands.command(aliases=["remind_me"])
    async def remindme(self, ctx, time, *, reminder=None):
        if not isinstance(ctx.channel, discord.abc.PrivateChannel):
            await asyncio.sleep(0.5)
            await ctx.message.delete()

        user = ctx.message.author

        async def error_embed(error):
            embed_dict = {'color': discord.Colour(self.bot.COLOUR).value, 'type': 'rich', 'description': error}
            error_message = await ctx.send(embed=discord.Embed.from_dict(embed_dict))
            await asyncio.sleep(5)
            await error_message.delete()

        seconds = 0

        min_duration = 1
        max_duration = 2678400  # 31 Days

        if reminder is None:
            await error_embed("**Please specify what you want me to remind you about.**")
            return
        # true_max = 1971
        if len(reminder) > 1900:
            await error_embed("**Your reminder can not be longer then 1900 characters**")
            return
        counter = ""
        if time.lower().endswith("d"):
            seconds += int(time[:-1]) * 60 * 60 * 24
            counter = f"{seconds // 60 // 60 // 24} days"
        if time.lower().endswith("h"):
            seconds += int(time[:-1]) * 60 * 60
            counter = f"{seconds // 60 // 60} hours"
        elif time.lower().endswith("m"):
            seconds += int(time[:-1]) * 60
            counter = f"{seconds // 60} minutes"
        elif time.lower().endswith("s"):
            seconds += int(time[:-1])
            counter = f"{seconds} seconds"
        if seconds == 0:
            await error_embed("**Please specify a proper duration.**")
            return
        elif seconds < min_duration:
            await error_embed(f"**You have specified a too short duration!\nMinimum duration is {min_duration // 60} minutes.**")
            return
        elif seconds > max_duration:
            await error_embed(f"**You have specified a too long duration!\nMaximum duration is {max_duration // 60 // 60 // 24} days.**")
            return
        else:
            success_embed = discord.Embed(description=f"**Alright, I will message you the reminder below in {counter}.**\n"
                                                      f"```{reminder}```", colour=discord.Colour(self.bot.COLOUR))
            await user.send(embed=success_embed)

            reminder_due_date = datetime.datetime.utcnow() + datetime.timedelta(0, seconds)
            object = await Reminder.create(user_id=ctx.author.id, reminder=reminder, date_due=reminder_due_date)

            Timer(self.bot, "reminder", reminder_due_date, args=(object.id,)).start()
            return

    @commands.Cog.listener()
    async def on_reminder(self, id_):
        object = await Reminder.get(id=id_)
        if object.destination_is_dm:
            user = self.bot.get_user(object.user_id)
            reminder_embed = discord.Embed(description=f"**Reminder:**\n"
                                                       f"```{object.reminder}```", colour=discord.Colour(self.bot.COLOUR))
            await user.send(embed=reminder_embed)
        else:
            channel = self.bot.get_channel(object.destination_channel_id)
            pass

        await Reminder.filter(id=id_).delete()


def setup(bot):
    bot.add_cog(Reminders(bot))
