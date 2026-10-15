# Tutti Frutti – Commodore Plus/4 in the browser

A fully client-side recreation of Shaun Southern's Commodore 16 / Plus/4 game.
All six maps, the character set, figure graphics and melody data come from
`tuttifrutti.prg`, included in this repository. The game interface and all
repository artifacts are in English, regardless of the language used in chat.

## Play and run locally

The complete website is in **[web/](web/)**. It uses no external JavaScript
libraries, fonts, image services, CDNs, accounts or server APIs. No build or
`npm install` is required to play.

From the project directory:

```sh
python3 -m http.server 8000 --directory web
```

Then open **http://localhost:8000**. Alternatively, open `web/index.html`
directly in your browser: the classic scripts require neither `fetch` nor a
module server. Whether high scores persist when using `file://` depends on
your browser's settings.

## Deploy to static web hosting

Copy the **contents** of `web/` into any directory on your web host.
`index.html` and the other seven files must be in the same directory. Relative
asset paths also support subdirectories such as `/games/tutti/`. No PHP,
Node.js, database, rewrite rules or internet connection after loading the files
is required.

Optionally, create a ready-to-upload archive:

```sh
python3 tools/package_web.py
```

This creates **`dist/tutti-frutti-web.zip`**, currently about 23 kB. Extract it on
your web host; the entry point is `index.html`. The PRG, analysis tools and tests
do not need to be uploaded to play the game.

## Controls

| Action | Keyboard / touch |
| --- | --- |
| Start / new game | Enter, Space or the Start button |
| Move | Arrow keys or WASD; directional pad on touch devices |
| Shoot | Space or F; Fire button on touch devices |
| Push / break a cherry block | Hold Fire and steer toward the block |
| Pause / resume | P, Escape or the Pause button |
| Sound on / off | M or the Sound button |
| Fullscreen | Fullscreen button, if supported by the browser |

Audio starts after an interaction. The game pauses when the window loses focus
or you switch tabs. The eight best scores from completed games and the sound
setting are stored only in the local browser. Blocking browser storage does not
prevent playing. A game in progress is not saved.

## Features

- Five lives, six repeating original maps, increasing enemy speed and additional
  reinforcements in later rounds.
- Maps 1/4: collect every cherry. Maps 2/5: also bring six apples to the bottom
  row. Maps 3/6: push four apple blocks into the four corners.
- Enemies move through excavated paths; the bouncing shot can be caught or
  recharged; apples fall and pushed blocks slide until they hit an obstacle.
- Defeating all enemies, including reinforcements, also completes a round.
- Score, bonus time limit, life loss, round transitions, game over and replay.
- Native 320 × 200 Canvas rendering with original character graphics, a
  responsive interface, and touch controls supporting simultaneous direction
  and Fire input.
- Original melody sequence and locally synthesized effects using Web Audio.

The rules were reconstructed from the disassembled program. This is not a
6502/TED emulator: the palette and sound generation are approximations rather
than cycle-accurate emulation. The unusual stack path in the original fall timer
has been replaced with a regular delay. Boundary collisions and resetting moving
objects after losing a life are stabilized in the browser recreation.

## Source code and verification

| File | Purpose |
| --- | --- |
| `web/engine.js` | Browser-independent game logic; fixed 50 ticks/s |
| `web/renderer.js` | Character set, figures and Canvas display |
| `web/audio.js` | Two locally synthesized audio voices |
| `web/app.js` | Keyboard/touch, DOM, pause, high scores and animation loop |
| `web/assets.js` | Maps, graphics and music data extracted from the PRG |
| `tools/extract_web_assets.py` | Reproducible asset-file generation |

Tests require only Node.js 18+; no npm packages need to be installed:

```sh
npm test
# Equivalent:
node tests/engine.test.cjs
```

The 14 checks cover comparison with the PRG data, player movement, score,
projectiles, enemies, falling and pushing, all three level goals, map cycling,
life loss, time limits, complete routes through both cherry-collection maps,
and longer deterministic games on all six maps.

`tests/browser-smoke.js` also contains a browser-executable test function.
Open the page with `?debug=1` and invoke the function from that file in your
browser's developer tools. It checks actual DOM and animation input, pause/help,
simultaneous touch input, high scores, replay, Canvas and local resources.
Verification covered Chromium at 1280 × 900, 390 × 844 and 320 × 740 pixels,
direct `file://` access, an HTTP subdirectory serving the extracted ZIP, and
playing without a network connection after loading. Fullscreen and the normal
view without a debug parameter were also checked. Debug access and manual
simulation timing are not enabled without that URL parameter.

## License

The original Tutti Frutti is by Mr. Chip Software, published by Mastertronic.
According to [this interview with a former Mastertronic executive](https://www.lemon64.com/page/anthony-guter-interview),
those games are now basically free.

## Readable reconstruction

[pseudocode.py](pseudocode.py) explains the program in English, using Python-like
pseudocode. It is intended for reading and is not an executable remake. Start
with the data model, `start()`, `frame_tick()` and `play_one_tick()`. Original
addresses and unresolved questions are included alongside the relevant code.

- [Extracted level maps](analysis/level_maps.txt)
- [Traced 6502 instructions](analysis/disassembly.txt), as a technical reference

The analysis tools require only Python 3 and run from the project directory:

```sh
python3 tools/extract_levels.py
python3 tools/trace_code.py
python3 tools/verify_analysis.py
```

The checks execute selected routines from the original file in a small CPU
runner. They do not replace a complete Plus/4 emulator run. An unusual stack
path in the fall timer is explicitly marked in the pseudocode.
