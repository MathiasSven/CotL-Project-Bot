from ..config import Config

config = Config()


def check_if_admin(ctx):
    return ctx.message.author.id == int(config.get("server", "ADMIN_ID"))


async def is_war_room(ctx):
    if ctx.channel.category_id != int(config.get("utils", "WAR_ROOMS_CATEGORY_ID")):
        await ctx.send("This is not a war room.")
        return False
    else:
        return True