import typing
from tbot.machine import connector, linux
import tbot_contrib.locking

Self = typing.TypeVar("Self", bound="LocalLabAndBuilder")


class LocalLabAndBuilder(
    connector.SubprocessConnector,
    linux.Bash,
    linux.Lab,
    linux.Builder,
    tbot_contrib.locking.LockManager,
):
    name = "locallabbuilder"
    lock_checkpid = True

    @property
    def toolchains(self) -> dict:
        return {
            "x86_64": linux.build.DistroToolchain("x86_64", ""),
        }

    def build(self: Self) -> Self:
        return self.clone()


LAB = LocalLabAndBuilder
