from datetime import datetime
import discord

from tortoise.models import Model
from tortoise import fields


class Reminder(Model):
    id = fields.IntField(pk=True)
    user_id = fields.IntField()
    reminder = fields.TextField()
    destination_channel_id = fields.IntField(null=True)
    date_due = fields.DatetimeField()

    date_created = fields.DatetimeField(auto_now=True)

    def destination_is_dm(self):
        if self.destination_channel_id is None:
            return True
        else:
            return False

    def duration(self):
        return (self.date_due - self.date_created).seconds


class PnWNation(Model):
    discord_user_id = fields.IntField(pk=True)
    nation_id = fields.IntField(unique=True)


class WarRoom(Model):
    def __init__(self, text_channel=None, **kwargs):
        self.text_channel = text_channel
        super().__init__(**kwargs)

    channel_id = fields.IntField(pk=True)
    last_renamed = fields.DatetimeField(auto_now_add=True)
    participants = fields.ManyToManyField('models.PnWNation')

    async def add(self, overwrites=None):
        await self.text_channel.edit(overwrites=overwrites)
        for overwrite in overwrites:
            if isinstance(overwrite, discord.Member):
                pnw_nation_instance = await PnWNation.get_or_none(discord_user_id=overwrite.id)
                await self.participants.add(pnw_nation_instance)

    async def exit(self, member: discord.Member):
        await self.text_channel.set_permissions(member, overwrite=None)
        pnw_nation_instance = await PnWNation.get_or_none(discord_user_id=member.id)
        await self.participants.remove(pnw_nation_instance)
        if await self.participants.all().count() == 0:
            await self.text_channel.delete()
            await self.delete()

    @classmethod
    async def w_get(cls, text_channel: discord.TextChannel):
        war_room_instance = await cls.get_or_none(channel_id=text_channel.id)
        if war_room_instance is None:
            return None
        war_room_instance.text_channel = text_channel
        return war_room_instance

    @classmethod
    async def w_create(cls, category_channel: discord.CategoryChannel, overwrites=None, **kwargs):
        war_room_channel = await category_channel.create_text_channel(overwrites=overwrites, topic="User \">wr add\" to add members to war room, "
                                                                                                   "\">wr exit\" to exit this war room and "
                                                                                                   "\">wr update\" to get a new participants embed.", **kwargs)
        war_room_instance = await cls.create(channel_id=war_room_channel.id)
        war_room_instance.text_channel = war_room_channel

        for overwrite in overwrites:
            if isinstance(overwrite, discord.Member):
                pnw_nation_instance = await PnWNation.get_or_none(discord_user_id=overwrite.id)
                await war_room_instance.participants.add(pnw_nation_instance)

        return war_room_channel