class AudioProcessService:
    def _advance_music(self, direction=1):
        """Refresh the uploaded library and play the next song, wrapping at the end."""
        current = self._music_file
        try:
            directory = safe_music_path(current).parent
            extensions = {
                ".mp3", ".wav", ".flac", ".ogg", ".oga", ".opus",
                ".m4a", ".aac", ".wma", ".aif", ".aiff", ".mp4", ".webm",
            }
            if self._music_had_samples:
                self._music_failed_files.discard(current)
            else:
                self._music_failed_files.add(current)
                logger.warning(f"Skipping music file with no decoded audio: {current}")

            songs = sorted(
                (p.name for p in directory.iterdir()
                 if p.is_file() and p.suffix.lower() in extensions),
                key=lambda name: (name.casefold(), name),
            )
            # Retain the alphabetical position even if the playing file was deleted.
            current_key = (current.casefold(), current)
            later = [name for name in songs if (name.casefold(), name) > current_key]
            earlier = [name for name in songs if (name.casefold(), name) <= current_key]
            ordered = later + earlier if direction > 0 else list(reversed([name for name in songs if (name.casefold(), name) < current_key])) + list(reversed([name for name in songs if (name.casefold(), name) >= current_key]))
            from libs.hnls_playlist import shuffle_order, shuffle_selected
            available = [name for name in songs if name not in self._music_failed_files]
            ordered = shuffle_order(self, available, current, direction, ordered)
            for filename in ordered:
                if filename in self._music_failed_files:
                    continue
                logger.info(f"Playlist advancing to: {filename}")
                if self._start_music(filename):
                    shuffle_selected(self, filename)
                    return
                self._music_failed_files.add(filename)

            logger.warning("Playlist stopped: no playable music files remain.")
        except Exception:
            logger.exception("Could not advance the music playlist.")
        self._cleanup_music()
        self._source_mode = "playlist_idle"
        self._publish_playback(True)
        write_status("stopped")
