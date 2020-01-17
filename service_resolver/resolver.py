import asyncio
import functools
import logging
import operator
from dataclasses import dataclass
from typing import (
    Any,
    Optional,
    Set,
    Tuple, List)

import pycares

from . import exceptions
from .cache import TTLCache, acachedmethod

logger = logging.getLogger(__name__)


@dataclass
class Request:
    type: int
    query: str


class DNSResolver:
    EVENT_READ = 0
    EVENT_WRITE = 1
    A = pycares.QUERY_TYPE_A
    SRV = pycares.QUERY_TYPE_SRV
    SOCKET_BAD = pycares.ARES_SOCKET_BAD

    def __init__(
            self,
            maxsize: int = 32,
            ttl: int = 30,
            include_domains: bool = True,
            loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self._channel = pycares.Channel(sock_state_cb=self._sock_state_cb)
        self._timer: Optional[asyncio.TimerHandle] = None
        self._fds: Set[int] = set()
        self._include_domains = include_domains
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self.loop = loop or asyncio.get_event_loop()

    @staticmethod
    def _callback(fut: asyncio.Future, result: Any, error_no: int) -> None:
        if fut.cancelled():
            return
        if error_no is not None:
            fut.set_exception(exceptions.DNSError(error_no, pycares.errno.strerror(error_no)))
            return

        if not result:
            fut.set_exception(exceptions.DNSError(-1, 'No Rows Found'))

        if len(result) > 1:
            # TODO: maybe max priority
            logger.warning('Query return more than one result. Using only the first one')
        fut.set_result(result[0])

    def _send_request(self, query, _type) -> asyncio.Future:
        fut = asyncio.Future(loop=self.loop)
        cb = functools.partial(self._callback, fut)
        self._channel.query(query, _type, cb)
        return fut

    @acachedmethod(get_cache=operator.attrgetter('_cache'))
    async def resolve(self, host: str, protocol: str, service: str) -> Tuple[str, int]:
        requests: List[Request] = [
            Request(self.A, host),
            Request(self.SRV, f'_{service}._{protocol}.{host}'),
        ]
        futures = [self._send_request(request.query, request.type) for request in requests]

        try:
            a_record, srv_record = tuple(
                await asyncio.gather(*futures, loop=self.loop)
            )  # type: pycares.ares_query_a_result, pycares.ares_query_srv_result
        except asyncio.CancelledError:
            self._channel.cancel()
            raise
        else:
            return a_record.host, srv_record.port

    def _sock_state_cb(self, fd, readable, writable):
        if readable or writable:
            if readable:
                self.loop.add_reader(fd, self._process_events, fd, self.EVENT_READ)
            if writable:
                self.loop.add_writer(fd, self._process_events, fd, self.EVENT_WRITE)
            self._fds.add(fd)
            if self._timer is None:
                self._timer = self.loop.call_later(1.0, self._timer_cb)
        else:
            # socket is now closed
            self._fds.discard(fd)
            if not self._fds:
                self._timer.cancel()
                self._timer = None

    def _process_events(self, fd, event):
        if event == self.EVENT_READ:
            read_fd = fd
            write_fd = self.SOCKET_BAD
        elif event == self.EVENT_WRITE:
            read_fd = self.SOCKET_BAD
            write_fd = fd
        else:
            read_fd = write_fd = self.SOCKET_BAD
        self._channel.process_fd(read_fd, write_fd)

    def _timer_cb(self):
        self._channel.process_fd(self.SOCKET_BAD, self.SOCKET_BAD)
        self._timer = self.loop.call_later(1.0, self._timer_cb)
