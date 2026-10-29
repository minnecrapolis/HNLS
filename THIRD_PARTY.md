# Provenance and licensing

This extension contains modifications to Music LED Strip Control by TobKra96 and contributors:
https://github.com/TobKra96/music_led_strip_control

The supplied source snapshot did not include the upstream license, dependency manifests or an upstream revision identifier. The upstream README identifies an MIT license, but the exact license file, notices and matching revision still need to be obtained before public release. Direct source-file retrieval was unavailable during preparation. This document does not grant a new license or replace upstream notices. Before public distribution, obtain the applicable upstream license and notices for the matching source revision and preserve them in the repository. Record that revision and review bundled web assets under their original terms. Do not claim the whole project is newly authored or apply an invented license to inherited source.

FSEQ interoperability is based on the published Falcon Player sequence format:
https://github.com/FalconChristmas/fpp/blob/master/docs/FSEQ_Sequence_File_Format.txt

Pi output depends on rpi_ws281x installed in the user's existing MLSC environment:
https://github.com/jgarff/rpi_ws281x

Audio uses external ffmpeg and ALSA tools from the existing installation. Dependency source is not vendored here. No music recordings are included.

## HNLS consolidation
New HNLS interface, song preparation, cue and networking work is included alongside inherited code. No exact upstream copyright notice is fabricated and no missing dependency license is waived. Review vendor CSS/fonts/images separately. HourNerd branding does not remove upstream notice obligations. The release remains a private review candidate until provenance is reconciled.
