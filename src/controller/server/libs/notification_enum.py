from enum import Enum


class NotificationEnum(Enum):
    config_refresh = 1
    config_refresh_finished = 2
    config_refresh_failed = 3
    process_stop = 4
    process_pause = 5
    process_continue = 6
    music_play = 7
    music_pause = 8
    music_resume = 9
    music_stop = 10
    song_show_refresh = 11
    studio_takeover = 12
    studio_release = 13
