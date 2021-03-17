import asyncio
import os
import random
from concurrent import futures

import discord
from discord.ext import commands
from captcha.image import ImageCaptcha

directory = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class Fun(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(self.startup())

    # noinspection PyAttributeOutsideInit
    async def startup(self):
        await self.bot.wait_until_ready()
        self.GUILD = self.bot.get_guild(self.bot.GUILD_ID)

    @commands.Cog.listener()
    async def on_ready(self):
        print('Fun Cog is loaded')

    @commands.command()
    async def captcha(self, ctx):
        # characters = string.ascii_uppercase + "123456789123456789123456789"
        characters = "0123456789"
        captcha_result = ''.join(random.choice(characters) for _ in range(5))

        image = ImageCaptcha()
        image.generate(captcha_result)
        image.write(captcha_result, f'{directory}/captchas/{captcha_result}.png')
        image_file = discord.File(f'{directory}/captchas/{captcha_result}.png', filename=f'{captcha_result}.png')

        verify_embed = discord.Embed(description="Complete the captcha below to verify your simple captcha solving abilities.\n"
                                                 "**Note:** Only **Numbers** and **No Spaces**", colour=discord.Colour(self.bot.COLOUR))
        verify_embed.set_image(url=f'attachment://{captcha_result}.png')

        await ctx.send(file=image_file, embed=verify_embed)

        os.remove(f'{directory}/captchas/{captcha_result}.png')

        def check_captcha(m):
            return m.channel == ctx.channel and m.author == ctx.author

        wrong_memes = ["https://memegenerator.net/img/instances/27866174/wrong.jpg",
                       "https://www.memesmonkey.com/images/memesmonkey/s_d6/d62b8247947ac39891f17d0c220ffc02.jpeg",
                       "https://media.makeameme.org/created/youre-wrong-rcpkeo.jpg",
                       "https://i.pinimg.com/originals/48/8e/77/488e779fe6c0cbd6ad177308f4ab72ab.jpg",
                       "https://i.pinimg.com/originals/49/cc/51/49cc51e8da081440a2994e16cc4ddce3.jpg"]

        for i in range(5):
            try:
                captcha_attempt = await self.bot.wait_for('message', check=check_captcha, timeout=120.0)
            except (asyncio.TimeoutError, futures.TimeoutError):
                await ctx.send(f'You took too long...')
                break
            else:
                if captcha_attempt.content == captcha_result:
                    first = " on your first try 👏" if i == 0 else f" with {i + 1} attempts."
                    await ctx.send(f'You have correctly answered the captcha{first}')
                    break
                else:
                    if i == 4:
                        await ctx.send(wrong_memes[i])
                        await ctx.send(
                            f'You have **incorrectly** answered the captcha **5** times. You should be disappointed with yourself')
                    elif i == 3:
                        await ctx.send(wrong_memes[i])
                        await ctx.send(f'You have **{4 - i}** attempt left.')
                    else:
                        await ctx.send(wrong_memes[i])
                        await ctx.send(f'You have **{4 - i}** attempts left.')


def setup(bot):
    bot.add_cog(Fun(bot))
