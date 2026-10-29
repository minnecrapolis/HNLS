# Architecture

The controller runs Python services for music playback/analysis, device management, effects, output and the web UI. Device configurations define counts, color orders and output transports. Effect workers generate automatic base frames; song_moments overlays active song-specific cues on copies before output. Cue pixels must never feed back into the automatic trail state.

Shared song position/token and monotonic clocks drive cues. Playback epochs and readiness enforce blackouts during transitions. Analysis caches whole-song and local section energy/tempo/onset information. Playlist settings persist independently from per-pass shuffle history.

The native output layer packs logical RGB; rpi_ws281x applies physical wire ordering. Remote output authenticates and chunks frames; the receiver checks ordering/session data and uses a watchdog. This is HNLS's own remote protocol, not a claim of FPP MultiSync compatibility.

The web layout is server-rendered templates with JavaScript controls. The small tools window uses same-origin messaging to navigate the main window; both talk to the same backend. The optional private ChatGPT bridge is deliberately excluded from this product distribution.

Source layout: src/controller/server, src/receiver, maintenance for scoped updates, tools for packaging/export, docs for operator/developer guidance. Existing legacy identifiers are compatibility details rather than product branding.
