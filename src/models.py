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
