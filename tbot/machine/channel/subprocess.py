# tbot, Embedded Automation Tool
# Copyright (C) 2019  Harald Seiler
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import fcntl
import os
import pty
import select
import struct
import subprocess
import termios
import time
import typing

import tbot.error
from . import channel

READ_CHUNK_SIZE = 4096


class SubprocessChannelIO(channel.ChannelIO):
    __slots__ = ("pty_master", "p")

    def __init__(self) -> None:
        self.pty_master, pty_slave = pty.openpty()

        self.p = subprocess.Popen(
            ["bash", "--norc", "--noprofile", "-i"],
            stdin=pty_slave,
            stdout=pty_slave,
            stderr=pty_slave,
            start_new_session=True,
        )

        flags = fcntl.fcntl(self.pty_master, fcntl.F_GETFL)
        flags = flags | os.O_NONBLOCK
        fcntl.fcntl(self.pty_master, fcntl.F_SETFL, flags)

    def write(self, buf: bytes) -> int:
        if self.closed:
            raise channel.ChannelClosedException()

        channel._debug_log(self, buf, True)
        bytes_written = os.write(self.pty_master, buf)
        if bytes_written == 0:
            raise channel.ChannelClosedException
        return bytes_written

    def read(self, n: int, timeout: typing.Optional[float] = None) -> bytes:
        if not self.closed:
            # If the process is still running, wait
            # for one byte or the timeout to arrive
            r, _, _ = select.select([self.pty_master], [], [], timeout)
            if self.pty_master not in r:
                raise TimeoutError()

        try:
            return channel._debug_log(self, os.read(self.pty_master, n))
        except (BlockingIOError, OSError):
            raise channel.ChannelClosedException

    def close(self) -> None:
        if self.closed:
            raise channel.ChannelClosedException()

        sid = os.getsid(self.p.pid)
        self.p.kill()
        os.close(self.pty_master)
        self.p.wait()

        # Wait for all processes in the session to end.  Most of the time
        # this will return immediately, but in some cases (eg. a serial session
        # with picocom) we have to wait a bit until we can continue.  To be as
        # quick as possible this is implemented as exponential backoff and will
        # give up after 1 second (1.27 to be exact) and emit a warning.
        for t in range(7):
            if (
                subprocess.call(
                    ["ps", "-s", str(sid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                != 0
            ):
                break
            time.sleep(2 ** t / 100)
        else:
            raise tbot.error.TbotException("some subprocess(es) did not stop")

    def fileno(self) -> int:
        return self.pty_master

    @property
    def closed(self) -> bool:
        self.p.poll()
        return self.p.returncode is not None

    def update_pty(self, columns: int, lines: int) -> None:
        s = struct.pack("HHHH", lines, columns, 0, 0)
        fcntl.ioctl(self.pty_master, termios.TIOCSWINSZ, s, False)


class SubprocessChannel(channel.Channel):
    def __init__(self) -> None:
        super().__init__(SubprocessChannelIO())
