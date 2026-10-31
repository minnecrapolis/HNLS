# Architecture

The controller runs Python services for music playback/analysis, device management, effects, output and the web UI. Device configurations define counts, color orders and output transports. Effect workers generate automatic base frames; song_moments overlays active song-specific cues on copies before output. Cue pixels must never feed back into the automatic trail state.

Shared song position/token and monotonic clocks drive cues. Playback epochs and readiness enforce blackouts during transitions. Analysis caches whole-song and local section energy/tempo/onset information. Playlist settings persist independently from per-pass shuffle history.

The native output layer packs logical RGB; rpi_ws281x applies physical wire ordering. Remote output authenticates and chunks frames; the receiver checks ordering/session data and uses a watchdog. This is HNLS's own remote protocol, not a claim of FPP MultiSync compatibility.

The web layout is server-rendered templates with JavaScript controls. The small tools window uses same-origin messaging to navigate the main window; both talk to the same backend. The optional private ChatGPT bridge is deliberately excluded from this product distribution.

Source layout: src/controller/server, src/receiver, maintenance for scoped updates, tools for packaging/export, docs for operator/developer guidance. Existing legacy identifiers are compatibility details rather than product branding.

ShowSchedule runs in the webserver process as a single APScheduler interval job (about two seconds). It persists independent settings under /share/.mlsc/show_schedule.json. It evaluates aware local time with zoneinfo and a date/time-zone window key, avoiding duplicate starts in the repeated DST hour. ScheduleActions uses existing effect/play queues; the receiver has no separate clock job.

Designer effects render an entire selected RGB range and explicitly black animation gaps. Cue rendering is stateless in song position, so seek/replay reproduces the same pattern. Runtime cue rows are normalized defensively and cached with song tokens. The overlay uses a nonblocking shared-clock snapshot and never alters automatic trail/base arrays. Paused clock heartbeats prevent animation from drifting during a pause. Realtime frame queues have nonblocking reads and bounded drains; playback shared state is recreated after worker termination rather than reusing locks a killed worker may have held.

Color-range settings are independent of timing/cue groups. The native/UDP Output classes call prepare_frame immediately before backend packing/transport, with a cached device ID. Physical order compensation occurs once after all logical effects and cue overlays, on a copy only when necessary. A small mtime-based cache reloads the separate mapping document, and unlisted ranges pass through. Invalid/out-of-frame rows cannot index outside the array; unsupported base/RGBW after a settings change blacks mapped ranges rather than making up an order. Device deletion clears its mapping before its ID can be reused.
