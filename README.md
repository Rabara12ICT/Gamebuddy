# Game Buddy: Code Quest

An educational 2D Pygame adventure where players restore the Lost Code Kingdom through programming and technology challenges.

## Play on the web

Open [Game Buddy on GitHub Pages](https://rabara12ict.github.io/Gamebuddy/) on a phone or computer. On phones, use landscape orientation for the best view. Tap **Play Now** to start; guest progress is saved in that browser.

The site is rebuilt and published automatically when changes are pushed to `master`.

## Run locally

Requirements: Python 3.10 or newer.

```powershell
py -m pip install -r requirements.txt
py GameBuddy\game.py
```

On Windows, you can also run `GameBuddy\launch_game.bat`.

## Controls

- Move with the arrow keys or WASD
- Interact with the on-screen controls
- On phones, rotate to landscape and use the on-screen touch controls
- Use `Esc` to exit menus or the game
- Developer shortcuts are available only with `--dev`

## User data

Account and save files are created locally and are intentionally excluded from Git:

- `gamebuddy_accounts.json`
- `gamebuddy_saves.json`
