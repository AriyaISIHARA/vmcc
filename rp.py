"""reserve play"""

from math import ceil
import subprocess
import sys
import time


def _main(filename, tsstr='', after=''):
    ts = tsstr and float(tsstr)
    after = after and float(after) or 20.0
    command = ['vm_play', 'play', filename, '--no-variation', '--vibrato', 'VIBRATO']

    print("given ts", ts)
    current_time = time.time()
    if not ts or ts < current_time:
        ts = ceil(current_time) + after
        print("set ts", ts)
    time.sleep(ts - current_time)
    print("now", time.time())
    subprocess.call(command)


if __name__ == '__main__':
    _main(*sys.argv[1:])
