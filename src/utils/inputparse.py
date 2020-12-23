import re
import validators


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

    async def nation_link_validator(self, nation_link):
        if validators.url(nation_link):
            nation_id = nation_link.split("politicsandwar.com/nation/id=")
            if nation_link != nation_id[0]:
                nation_id = nation_id[1]
                return nation_id
            else:
                await self.ctx.send("The nation link provided is not valid.")
                return None
        else:
            await self.ctx.send("The nation link provided is not valid.")
            return None
