# License and attribution notices

## Music LED Strip Control

HNLS is derived from Music LED Strip Control by TobKra96 and contributors:
https://github.com/TobKra96/music_led_strip_control

The original uploaded archive records baseline commit adcc5fdbc55e438396231360ebbc4bff62bae39c. The captured working install supplied the same original MIT notice, retained verbatim in root LICENSE and src/controller/LICENSE:
Copyright (c) 2019-2021 TobKra96.

HNLS product branding does not replace upstream credit or notices. This file does not assert exclusive authorship of inherited code or relicense third-party assets.

## Included web assets

Original copyright/license comments in JS/CSS are preserved. Inventory and published licensing references:

| Asset | Notice / licensing reference |
| --- | --- |
| Bootstrap | MIT; https://github.com/twbs/bootstrap/blob/main/LICENSE |
| jQuery and jQuery UI | MIT; https://jquery.org/license/ |
| Font Awesome Free 6.1.1 | Icons CC BY 4.0, fonts SIL OFL 1.1, code MIT; https://fontawesome.com/license/free |
| Animate.css | MIT, Daniel Eden; embedded notice retained |
| Pickr | MIT; https://github.com/simonwep/pickr/blob/master/LICENSE |
| Datta Able / AppSeed / CodedThemes | Inherited interface assets and notices; https://github.com/app-generator/flask-datta-able |
| Quicksand and inherited icon fonts | Retained from upstream; preserve applicable font notices and review exact asset versions before repackaging separately |

The new HNLS interface replaces the old navigation/layout but retains some shared vendor assets for controls and compatibility. Asset retention is not a claim of original HNLS authorship.

## Runtime dependencies and formats

rpi_ws281x: https://github.com/jgarff/rpi_ws281x
Scott Lawson audio-reactive work (credited upstream): https://github.com/scottlawsonbc/audio-reactive-led-strip
FSEQ format: https://github.com/FalconChristmas/fpp/blob/master/docs/FSEQ_Sequence_File_Format.txt
Python dependencies: requirements/controller.txt and requirements/receiver.txt; source and license terms belong to their respective projects. ffmpeg, ALSA and OS components are installed externally and not vendored in the source release. No music recordings are included or licensed by HNLS.
