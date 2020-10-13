import contextlib
import typing

import tbot
from tbot.machine import channel, connector, linux, shell

GDB_PROMPT = b"GDB-ORRG65BNM5SGECQ "


class GDBShell(shell.Shell):
    """
    Shell implementation for GDB.

    This class implements CLI interaction with GDB.  You will most likely not
    use it directly but instead use a :py:class:`gdb.GDB() <tbot_contrib.gdb.GDB>`
    machine instead.
    """

    name = "gdb"

    @contextlib.contextmanager
    def _init_shell(self) -> typing.Iterator:
        with self.ch.with_prompt(GDB_PROMPT):
            try:
                self.ch.read_until_prompt("(gdb) ")

                streams_orig = self.ch._streams
                self.ch._streams = []

                self.ch.sendline(b"set prompt " + GDB_PROMPT, True)
                self.ch.read_until_prompt()

                self.ch.sendline("set confirm off")
                self.ch.read_until_prompt()

                self.ch.sendline("set pagination off")
                self.ch.read_until_prompt()

                # Disable styling so output is not clobbered with escape sequences
                self.ch.sendline("set style enabled off")
                self.ch.read_until_prompt()

                yield None
            finally:
                self.ch._streams = streams_orig

    def escape(self, *args: str) -> str:
        """
        Escape a string so it can be used safely on the GDB command-line.

        .. todo::

            At the moment, this is a noop because GDB escaping is very
            different from traditional escaping ... Use with care.
        """
        return " ".join(args)

    def exec(self, *args: str) -> str:
        """
        Run a GDB command (and wait for it to finish).

        **Example**:

        .. code-block:: python

            gdb.exec("break", "main")
            # Returns once the program hits a breakpoint
            gdb.exec("run")
            gdb.exec("backtrace")
        """
        cmd = self.escape(*args)

        with tbot.log_event.command(self.name, cmd) as ev:
            self.ch.sendline(cmd, read_back=True)
            with self.ch.with_stream(ev, show_prompt=False):
                out = self.ch.read_until_prompt()
            ev.data["stdout"] = out

        return out

    def interactive(self) -> None:
        """Drop into an interactive GDB session."""
        self.ch.sendline("set prompt (gdb) ", True)
        self.ch.read_until_prompt("(gdb) ")
        self.ch.sendline(" ")

        tbot.log.message(
            f"Entering interactive GDB shell ({tbot.log.c('CTRL+D to exit').bold}) ..."
        )
        self.ch.attach_interactive()

        self.ch.sendcontrol("C")
        self.ch.read_until_prompt("(gdb) ")
        self.ch.sendline(b"set prompt " + GDB_PROMPT, True)
        self.ch.read_until_prompt()


H = typing.TypeVar("H", bound=linux.LinuxShell)


class GDB(connector.Connector, GDBShell):
    """
    GDB Machine.

    This machine can be used to invoke GDB on a
    :py:class:`~tbot.machine.linux.LinuxShell` and interact with it.  The
    machine will live in a context like any other:

    .. code-block:: python

        from tbot_contrib import gdb

        with tbot.acquire_lab() as lh:
            with gdb.GDB(lh, "/usr/bin/echo") as g:
                # GDB active here
                ...

    You can then send commands to gdb using
    :py:meth:`gdb.exec() <tbot_contrib.gdb.GDB.exec>` or drop the user into an
    interactive GDB session with
    :py:meth:`gdb.interactive() <tbot_contrib.gdb.GDB.interactive>`:

    .. code-block:: python

        with gdb.GDB(lh, "/usr/bin/echo", "hello", "world") as g:
            # Break on the first getenv
            g.exec("break", "getenv")
            g.exec("run")

            # Not let the user take over and interact with GDB
            g.interactive()
    """

    def __init__(
        self,
        host: H,
        *args: typing.Union[str, linux.Path[H]],
        gdb: typing.Union[str, linux.Path[H], None] = None,
    ) -> None:
        if gdb is None:
            gdb = linux.Path(host, "gdb")
        elif isinstance(gdb, str):
            gdb = linux.Path(host, gdb)

        self._gdb = gdb
        self.name = f"{host.name} <{gdb.name}>"
        self._host = host
        self._args = args

    @contextlib.contextmanager
    def _connect(self) -> typing.Iterator[channel.Channel]:
        with self._host.run(self._gdb, "-nh", "-nx", *self._args) as ch:
            try:
                yield ch
            finally:
                tbot.log_event.command(self.name, "quit")
                ch.sendline("quit")
                ch.terminate0()

    def clone(self) -> typing.NoReturn:
        raise NotImplementedError("cannot clone a GDB machine")


@tbot.testcase
@tbot.with_lab
def selftest_gdb(lh: linux.LinuxShell) -> None:
    import re

    result_pattern = re.compile(r"\$\d+ = 0x[0-9a-f]+ (?:<.*> )?\"(.*)\"")

    program = lh.exec0("which", "echo").strip()

    with GDB(lh, program, "hello", "world") as gdb:
        gdb.exec("break", "getenv")
        gdb.exec("run")

        while True:
            # First argument is in RDI
            out = gdb.exec("print", "(char*)($rdi)").strip()
            match = result_pattern.match(out)
            if match is not None:
                val = match.group(1)
                tbot.log.message(f'{program}: getenv("{tbot.log.c(val).bold}")')
            else:
                tbot.log.warning(f"Got unparseable output:\n    {tbot.log.c(out).dark}")

            if "exited" in gdb.exec("continue"):
                break

    lh.exec0("echo", "back out of gdb!")
