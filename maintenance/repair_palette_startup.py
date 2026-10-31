"""Repair only the exact HNLS palette future-import ordering error."""
from pathlib import Path
import shutil
import time


def repair(path):
    source = path.read_text()
    bad = 'from libs.show_palettes import EXTRA_COLORS, SHOW_MODES, PALETTE_IDS\nfrom __future__ import annotations\n'
    good = 'from __future__ import annotations\n\nfrom libs.show_palettes import EXTRA_COLORS, SHOW_MODES, PALETTE_IDS\n'
    if source.startswith(good):
        compile(source, str(path), 'exec')
        print('Import order is already corrected.')
        return
    if not source.startswith(bad):
        raise SystemExit('Unexpected file contents; nothing changed. Capture the service log instead.')
    fixed = source.replace(bad, good, 1)
    compile(fixed, str(path), 'exec')
    backup = path.with_name(path.name + '.before-import-fix-' + str(time.time_ns()))
    shutil.copy2(path, backup)
    temporary = path.with_name(path.name + '.import-fix-tmp')
    try:
        temporary.write_text(fixed)
        shutil.copystat(path, temporary)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    print('Import order repaired. Backup:', backup)


if __name__ == '__main__':
    repair(Path('/share/music_led_strip_control/server/libs/webserver/schemas/config_validator_service.py'))
