import collections.abc
import datetime

from .utils import chunked_sleep


class ChildTimer:
    """A slimmed down timer class meant for internal use."""

    def __init__(self, name, expires, args=None, kwargs=None):
        if not isinstance(args, collections.abc.Iterable) and args is not None:
            raise TypeError("args must be an iterable, got {0!r}".format(args.__class__.__name__))

        if kwargs is not None and not isinstance(kwargs, dict):
            raise TypeError("kwargs must be of type dict, got {0!r}".format(kwargs.__class__.__name__))

        if kwargs is not None:
            if not all(isinstance(key, str) for key in kwargs.keys()):
                raise TypeError("kwargs keys must all be str")

        self._expires = self._convert_to_expires(expires)

        self.name = name
        self._args = args or tuple()
        self._kwargs = kwargs or {}

    @staticmethod
    def _convert_to_expires(expires):
        if isinstance(expires, (float, int)):
            return datetime.datetime.utcnow() + datetime.timedelta(seconds=expires)
        elif isinstance(expires, datetime.timedelta):
            return datetime.datetime.utcnow() + expires
        elif isinstance(expires, datetime.datetime):
            return expires
        else:
            raise TypeError(
                "expires must be one of int, float, datetime.datetime or datetime.timedelta. Got {0!r}".format(
                    expires.__class__.__name__
                )
            )


class Timer(ChildTimer):
    """A timer that spawns his own task.
    Parameters
    ----------
    bot: :class:`discord.Client`
        A discord.py client instance.
    name: :class:`str`.
    expires: Union[:class:`float`, :class:`int`, :class:`datetime.datetime`, :class:`datetime.timedelta`].
    args: :class:`~collections.abc.Iterable`.
    kwargs: Mapping[:class:`str`, Any].
    """

    def __init__(self, bot, name, expires, args=None, kwargs=None):
        super().__init__(name, expires, args, kwargs)

        self._bot = bot
        self._task = None

    async def internal_task(self):
        await chunked_sleep((self._expires - datetime.datetime.utcnow()).total_seconds())

        self._bot.dispatch(self.name, *self._args, **self._kwargs)

    @property
    def done(self):
        """::class:`bool` Whether the timer is done."""
        return self._task is not None and self._task.done()

    def start(self):
        """Start the timer.
        Returns
        -------
        :class:`Timer`
            The Timer started."""
        self._task = self._bot.loop.create_task(self.internal_task())

        return self

    def _check_task(self):
        if self._task is None:
            raise RuntimeError("Timer was never started.")
        if self._task.done():
            raise RuntimeError("Timer is already done.")

    def cancel(self):
        """Cancel the timer.
        Raises
        ------
        RuntimeError
            The timer was not launched or is already done."""
        self._check_task()

        self._task.cancel()

    @property
    def remaining(self):
        """::class:`int` The amount of seconds before the timer is done."""
        return (self._expires - datetime.datetime.utcnow()).total_seconds()

    async def join(self):
        """Wait until the timer is done.
        Raises
        ------
        RuntimeError
            The timer was not launched or is already done."""
        self._check_task()

        await self._task