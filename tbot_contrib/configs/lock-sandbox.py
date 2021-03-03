from tbot.machine import connector, board, linux, channel
from tbot.tc import uboot
import tbot_contrib.locking


class SandboxUBootBuilder(uboot.UBootBuilder):
    name = "sandbox"
    defconfig = "sandbox_defconfig"
    toolchain = "x86_64"


class SandboxBoard(
    connector.ConsoleConnector,
    board.PowerControl,
    board.Board,
    tbot_contrib.locking.PooledMachineLock,
):
    name = "sandbox"

    lock_expiry = 10
    lock_pool_max = 2

    available_machines = [f"sandbox-{i:02}" for i in range(lock_pool_max)]

    def poweron(self) -> None:
        pass

    def poweroff(self) -> None:
        # Paths can make this cleaner than using cat
        if self.pidfile.is_file():
            # I recommend storing variables always as the type that makes most
            # sense for them.  E.g. here an int is best for the pid instead of
            # storing the string value.
            pid = int(self.pidfile.read_text())

            # Use exec0 whenever possible to catch unexpected failures
            self.host.exec0("rm", self.pidfile)
            self.host.exec0("kill", str(pid))

    def connect(self, mach: linux.LinuxShell) -> channel.Channel:
        # Let's use a variable for the pidfile
        if hasattr(self, "selected_machine"):
            suffix = getattr(self, "selected_machine")
        if hasattr(self, "lock_name"):
            suffix = getattr(self, "lock_name")
        self.pidfile = self.host.workdir / "uboot-sandbox" / f"PID-{suffix}"

        # Move commands into separate exec calls instead
        # of chaining with linux.Then if possible :)
        mach.exec0("stty", "intr", "undef")
        mach.exec0("cd", mach.workdir / "uboot-sandbox")

        # "--norc", "--noprofile" is not needed when passing a command directly
        cmd = mach.escape(
            "echo",
            linux.Raw("$$"),
            linux.RedirStdout(self.pidfile),
            linux.Then,
            "exec",
            "./u-boot",
            "-d",
            "arch/sandbox/dts/test.dtb",
        )
        return mach.open_channel(
            "while", "true", linux.Then, "do", "bash", "-c", cmd, linux.Then, "done",
        )


class SandboxUBoot(board.Connector, board.UBootAutobootIntercept, board.UBootShell):
    name = "sandbox-u-boot"
    prompt = "=> "
    build = SandboxUBootBuilder()


BOARD = SandboxBoard
UBOOT = SandboxUBoot
