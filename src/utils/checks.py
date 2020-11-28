from ..config import Config

config = Config()


def check_if_admin(ctx):
    return ctx.message.author.id == int(config.get("server", "ADMIN_ID"))
