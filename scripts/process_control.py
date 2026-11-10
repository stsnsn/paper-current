"""Bound a collector and terminate its entire process group before reading checkpoints."""
import os
import signal
import subprocess


def run_bounded(command, seconds):
    process=subprocess.Popen(command,start_new_session=True)
    try:
        return process.wait(timeout=seconds),False
    except subprocess.TimeoutExpired:
        # The collector may have children; killing only its parent leaves writers alive.
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        process.wait()
        return process.returncode,True
    except BaseException:
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        process.wait()
        raise
