#!/usr/bin/env python3
"""Correct RGB integer packing; the configured driver handles physical GRB order."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess
import sys

OLD = '''            g = np.left_shift(output_array[1][:].astype(int), 16)
            r = np.left_shift(output_array[0][:].astype(int), 8)
            b = output_array[2][:].astype(int)'''
NEW = '''            # Pack logical RGB; rpi_ws281x applies the configured wire order.
            g = np.left_shift(output_array[1][:].astype(int), 8)
            r = np.left_shift(output_array[0][:].astype(int), 16)
            b = output_array[2][:].astype(int)'''


def patched(source):
    if source.count(OLD) == 1:
        return source.replace(OLD, NEW, 1)
    if source.count(NEW) == 1 and OLD not in source:
        return source
    raise ValueError('Unexpected output driver version; no changes made.')


def clear_cache(target):
    for path in (target.parent/'__pycache__').glob(target.stem+'.*.pyc'):
        path.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('/share/music_led_strip_control'))
    parser.add_argument('--restore', type=Path, help='Restore the backup file printed by this script')
    parser.add_argument('--no-service', action='store_true', help='Offline verification only')
    args = parser.parse_args()
    if not args.no_service and os.geteuid() != 0:
        raise SystemExit('Run with sudo. No changes made.')
    target = args.root.resolve()/'server/libs/outputs/output_raspi.py'
    original = target.read_text()
    replacement = args.restore.read_text() if args.restore else patched(original)
    compile(replacement, str(target), 'exec')
    if replacement == original:
        print('Color packing is already correct; no changes made.')
        return
    backup = target.with_name(target.name+'.before-color-fix-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    shutil.copy2(target, backup)
    if not args.no_service:
        subprocess.run(['systemctl','stop','mlsc'], check=True)
    temporary = target.with_suffix('.color-fix.tmp')
    try:
        shutil.copy2(target, temporary)
        temporary.write_text(replacement)
        temporary.replace(target)
        clear_cache(target)
        if not args.no_service:
            subprocess.run(['systemctl','start','mlsc'], check=True)
    except Exception:
        shutil.copy2(backup, target)
        clear_cache(target)
        temporary.unlink(missing_ok=True)
        if not args.no_service:
            subprocess.run(['systemctl','start','mlsc'], check=False)
        raise
    print('Previous driver restored.' if args.restore else 'Color packing corrected. Keep LED Strip Type set to ws2811_strip_grb for your GRB lights.')
    print('Only the output driver changed. Audio, GPIO, LED counts and settings were retained.')
    print('Test pure red, green and blue, then orange #FF8000 in Song Show.')
    print('Backup:', backup)
    print('Rollback: sudo python3', Path(__file__).resolve(), '--root', args.root.resolve(), '--restore', backup)


if __name__ == '__main__':
    main()
