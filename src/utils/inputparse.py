import re


class InputParser:
    def __init__(self, ctx):
        self.ctx = ctx

    async def user_mention_id(self, user):

        regex = re.compile(r'^<@!?(?P<id>\d*)>$')
        regex_match = regex.match(user)

        if regex.match(user) is None:
            try:
                return int(user)
            except ValueError:
                await self.ctx.send("Invalid user ID.")
                return None
        else:
            return regex_match.group("id")