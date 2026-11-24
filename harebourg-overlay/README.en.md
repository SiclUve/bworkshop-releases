# Harebourg Overlay: user guide

An overlay for the fight against Count Harebourg (Clepsydra Tower, Frigost III, Dofus 3). The Count's *confusion*
rotates your spells around your character, so you no longer know where they will land. The overlay draws, on top of
the game:

- **your cell** (white, “YOU”);
- **the cell your mouse aims at** (blue) and a dotted line from you;
- **the cell where the spell really lands** (yellow, “LANDS HERE”) and a solid line;
- **warnings** under the aimed cell: wall or pit, outside the map, no line of sight.

A small **dial** in the control window shows the same thing: the black needle is where your spell goes, the cyan
marker is where you aim, the arc is how far the confusion turns it.

It never acts in the game: it does not click, does not send any key, does not read the game's memory and does not
touch the network or the game files.

## Install

Run `HarebourgOverlay-Setup.exe`, pick **English** in the first window and follow the wizard. It installs for your
user only (no administrator rights needed), adds a Start menu shortcut (and a desktop one if you tick the box) and
uninstalls cleanly from Windows' “Installed apps”. The game must run in **windowed** or **borderless windowed** mode:
an overlay cannot be shown over exclusive fullscreen.

Windows may show “Windows protected your PC” the first time, because the program is not signed: click “More info”,
then “Run anyway”.

## First use

1. **Open your fight** (the game on the screen chosen in Settings).
2. **The grid calibrates itself.** It does so when you launch the overlay and **each time you place yourself**
   (key **F6** with the mouse on your character, or the “Place me” button). The overlay finds the room on your screen
   from the colour of its tiles. It takes a second or two in the background: you are placed immediately, and the grid
   is corrected afterwards if it was offset. A cyan outline shows for 2 seconds so you can see it follows the edge
   of the tiles.
3. **Pick the right fight** in Settings (Count alone, + Nileza, + Klime, + Sylargh): the obstacles change.

If the room is not recognized (exclusive fullscreen, wrong screen, room hidden), a message says so and the
**by-hand calibration** opens (2 clicks, then make the cyan outline match the edge of the tiles). You can also open it
with the “By hand…” button. If the grid moves too much when you place yourself, **untick “Automatic calibration”**
in Settings: the grid then only moves when you click “Calibrate the grid”.

**What the overlay reads**: your mouse position, the clipboard when you copy a confusion line, and **a screenshot of
your screen, only to calibrate the grid** (at launch, on “Place me” and on “Calibrate”). It is analysed on your
computer and never stored or sent anywhere.

## Each turn

1. **Place yourself**: mouse on your cell + **F6**. Press **F3** before you move (it clears the cell and the lines),
   then F6 again once you arrived.
2. **Tell it your confusion**, whichever you prefer:
   - **copy** the line from the chat (“Confusion clockwise: 2 Pi/4”): it is picked up automatically;
   - or choose it in the **drop-down menu** (F7 goes to the next one);
   - or paste / type it in the field (“counter clockwise 6 Pi/4” is enough);
   - or click your **HP bracket** for the start of the turn (Settings > HP, used when no confusion is chosen).
3. **Melee**: press **F10** for each line of damage **you deal** in melee (a spell hitting 2 lines = 2 presses).
   Each line turns the confusion 90° counter-clockwise. If the game writes a new confusion line, copy it instead:
   it resets the lines to 0.
4. **F9 at the start of the next turn**: lines back to 0 and the confusion is cleared, so you pick it again.

The chat line is “Confusion clockwise: 2 Pi/4” = 90° clockwise, 4 Pi/4 = 180°, 6 Pi/4 = 90° counter-clockwise;
“counter clockwise” reverses the direction. The overlay also understands the French chat line.

## Shortcuts

| Key | Action |
|---|---|
| F6 | Place me: mouse on your cell |
| F3 | Clear my position (while you move) |
| F7 | Next confusion in the menu |
| F9 | New turn: lines back to 0, confusion cleared |
| F10 / F11 | +1 / -1 line of melee damage |
| F4 | Summon mode: you play a summon, **no confusion** (press again to leave) |
| F5 | Calibrate the grid (automatic) |
| F8 | Show / hide the overlay |
| Ctrl + Shift + C | Snap the grid to the cell under the mouse (the one the game outlines in white) |
| Ctrl + Shift + arrows | Shift the grid by 1 pixel (speeds up if you keep pressing) |
| Ctrl + Shift + Page Up / Down | Enlarge / shrink the grid around the mouse |

These are the default keys. **To change one**, open the “Shortcuts” card, click the key of an action, then press the
one you want (Esc = cancel, Del = no key). Avoid a bare letter: it would also trigger while you type in the chat.

**Fine-tuning the grid by hand (optional)**: when your mouse is over a cell, the game outlines it in white. If your
blue diamond does not sit exactly on that white one, put the mouse at the centre of the game's cell and press
**Ctrl + Shift + C**.

## Dreams mode (free grid)

In the Dreams (“Songes”) the room changes every time and the overlay does not know it. In **Settings > Fight**, pick
**Dreams (free grid)**:

- **No map**: no room outline, blocks, pits or “wall” warnings. Instead, **one big grid covers the whole screen**,
  always shown (the “Drawings” opacity slider makes it more discreet).
- **The grid never recalibrates on its own**: not at launch, not when you place yourself. Its size and position only
  change when you change them. No screenshot is taken in this mode.
- Everything else works the same: your cell, the aimed cell, the landing cell (even far away, the rotation does not
  depend on the room), the dial, the confusion, F6 / F9 / F10…
- **Set the grid once**: click “Calibrate the grid” and make it match the game's tiles: drag = move, wheel = size
  (around the mouse), arrows = 1 pixel (Shift = 10), Enter to confirm.
- To go back to the Count, pick another fight: automatic calibration comes back.

Limit: without a map there are no walls and no line of sight in this mode; only the rotation is computed.

## The window

- Each card (Confusion, Turn, HP, Position, Display, Settings, Shortcuts) folds by clicking its title.
- **–** (top right) switches to **mini mode** (just the small dial and the rotation); **+** brings everything back;
  **×** closes the overlay.
- **Resize it like any window**: drag an **edge** for the width or height, a **corner** for both (the little grip at
  the bottom right). When it is shorter than its content, the list scrolls. Its size and position are remembered.
- Grab it by any background, title or the dial to move it.
- Display card: window opacity (20 to 100 %), drawings opacity (10 to 100 %), grid.

## Language

The language is chosen in the installer. You can change it any time in **Settings > Langue / Language**; it applies
the next time you start the overlay. Everything is kept in `config.json`, next to the program.

## Limits

- Tested on screenshots and with simulated input: the maths (checked against the online simulator, 480 cases out of
  480), the calibration, the window, the shortcuts' logic. **Not tested on the live game**: display over Dofus, the
  global shortcuts and the screen capture.
- The chat line of the **English game client** could not be checked: the overlay accepts the likely forms
  (“Confusion clockwise : 2 Pi/4”, “Clockwise confusion: 2 Pi/4”, with “counter clockwise”). If your client writes it
  differently, use the drop-down menu or the field.
- “clockwise” is the simulator's convention. On your first throw, check that the yellow cell matches what happens.
- Dofus and Count Harebourg belong to Ankama.
