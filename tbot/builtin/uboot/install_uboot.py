""" Testcase for installing uboot """
import os
import collections
import tbot


@tbot.testcase
def install_uboot_to_tftp(tb, additional=None):
    """ Install uboot files into tftp folder """
    if not tb.shell.shell_type[0] == "sh":
        raise "Need an sh shell"

    if additional is None:
        additional = list()

    build_dir = os.path.join(
        tb.config.workdir,
        f"u-boot-{tb.config.board_name}")
    tftpdir = os.path.join(
        tb.config.get("tftp.rootdir"),
        tb.config.get("tftp.boarddir"),
        tb.config.get("tftp.tbotsubdir"))

    # Make sure tftpdir exists
    tb.shell.exec0(f"mkdir -p {tftpdir}")

    def tfile(f):
        """ Return path inside tftp directory for f """
        return os.path.join(tftpdir, f)

    def sfile(f):
        """ Return path inside source directory for f """
        return os.path.join(build_dir, f)

    files = [".config",
             "u-boot.bin",
             "System.map",
             "boot.bin"]
    collections.deque(map(lambda f:
                          tb.shell.exec0(f"cp {sfile(f)} {tfile(f)}"), files),
                      maxlen=0)

    tb.shell.exec0(f"""\
cp {sfile(os.path.join('spl', 'u-boot-spl.bin'))} {tfile('u-boot-spl.bin')}""")
    tb.shell.exec0(f"""\
cp {sfile(os.path.join('spl', 'u-boot-spl.map'))} {tfile('u-boot-spl.map')}""")

    # Copy additional files
    collections.deque(map(lambda f:
                          tb.shell.exec0(f"cp {f[0]} {tfile(f[1])}"),
                          additional), maxlen=0)