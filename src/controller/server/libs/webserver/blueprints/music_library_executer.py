import math
from libs.music_library import list_music_files, read_status, safe_music_path
from libs.notification_enum import NotificationEnum
from libs.notification_item import NotificationItem
from libs.webserver.executer_base import ExecuterBase


class MusicLibraryExecuter(ExecuterBase):
    def get_library(self) -> dict:
        return {
            "files": list_music_files(),
            "status": read_status(),
        }

    def play(self, filename: str) -> dict:
        path = safe_music_path(filename)
        if not path.is_file():
            raise FileNotFoundError(filename)
        self.notification_queue_out.put(
            NotificationItem(NotificationEnum.music_play, "all_devices", {"file": filename})
        )
        return {"ok": True, "command": "play", "file": filename}

    def pause(self) -> dict:
        self.notification_queue_out.put(
            NotificationItem(NotificationEnum.music_pause, "all_devices")
        )
        return {"ok": True, "command": "pause"}

    def resume(self) -> dict:
        self.notification_queue_out.put(
            NotificationItem(NotificationEnum.music_resume, "all_devices")
        )
        return {"ok": True, "command": "resume"}

    def stop(self) -> dict:
        self.notification_queue_out.put(
            NotificationItem(NotificationEnum.music_stop, "all_devices")
        )
        return {"ok": True, "command": "stop"}

    def control(self, data) -> dict:
        if not isinstance(data, dict):
            raise ValueError('Expected a music control object')
        action = data.get('action')
        if action not in ('next', 'previous', 'replay', 'seek', 'seek_relative', 'delete'):
            raise ValueError('Unknown music control')
        payload = {'action': action}
        if action in ('seek', 'seek_relative'):
            value = data.get('seconds')
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError('Seek seconds must be a number')
            if (action == 'seek' and not 0 <= value <= 604800) or (action == 'seek_relative' and not -3600 <= value <= 3600):
                raise ValueError('Seek time is outside the supported range')
            payload['seconds'] = value
        if action == 'delete':
            filename = data.get('file')
            path = safe_music_path(filename)
            if not path.is_file():
                raise FileNotFoundError(filename)
            payload['file'] = filename
        self.notification_queue_out.put(NotificationItem(NotificationEnum.music_play, 'all_devices', payload))
        return {'ok': True, 'command': action, 'queued': True}
