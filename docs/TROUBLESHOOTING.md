# Troubleshooting

- No UI: inspect `sudo systemctl status mlsc --no-pager -l` and `sudo journalctl -u mlsc -n 100 --no-pager`. Confirm browser address and network reachability.
- No receiver lights: inspect `mlsc-receiver`, web pairing/status, LED count/order and GPIO21/physical40. A startup line saying waiting for pairing is not a current connection-status check.
- Wrong colors: test low-brightness pure red, green and blue. Check RGB/GRB settings and logical packing. Orange can appear yellow on a particular strip; do not compensate for a channel-order error with palette changes.
- Pixels do not resume after a cue: inspect reserve, overlapping cues, active Song Show and playback position. Confirm output base frames cover the full configured strip. Avoid assuming a cue is stuck from sparse music effects alone.
- Freeze on white: stop the show and inspect LED power delivery before replaying. `vcgencmd get_throttled` helps diagnose Pi supply conditions but 0x0 does not prove LED wiring has adequate capacity.
- Distorted analog sound: retain working direct ALSA routing and buffer settings; test the same file and cable independently. Avoid changing PWM GPIO and audio settings together.
- Configuration validation: use the supplied recovery utility only after reading its options and creating a private backup. It validates against the installed schema; do not remove arbitrary fields blindly.
- Analysis slow: background preparation competes for CPU on smaller Pis. Wait for cache progress and compare with preparation idle before diagnosing rendering performance.

When reporting bugs, include OS/Python version, service names, counts/backends, reproduction steps and redacted logs. Never attach music, keys or full private configuration to a public issue.

For the reservation/all-on freeze report, rc.4 removes two software hazards: realtime empty-then-blocking queue races and abandoned shared playback locks. It also prevents delayed cue clocks from exposing automatic effects. The reservation save route itself writes cue data without restarting services. These fixes require a real-Pi check; an all-on/cycling symptom alone does not establish whether the process crashed, the OS rebooted or LED power delivery failed. If it persists after updating, collect `sudo journalctl -u mlsc -n 150 --no-pager` and `vcgencmd get_throttled`, and note whether SSH remains responsive.
