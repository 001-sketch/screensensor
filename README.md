# Screen Sensor

A lightweight Windows prototype that uses the webcam to control the mouse with one hand:

- Move your index finger to move the cursor.
- Move your pinky finger up or down to scroll.
- Pinch your index finger and thumb, then release to click. This can open a desktop shortcut or app when the cursor is over it.
- Press `P` to pause/resume control.
- Press `R` to record pinky movement samples locally. While recording, press `U` while demonstrating scroll-up, `D` while demonstrating scroll-down, and `S` to stop the current label. Press `R` again to save a CSV in `recordings`.
- Press `Q` or `Esc` to quit.

## Setup

Install Python 3.10-3.12, then open PowerShell in this folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py screen_scroller.py
```

If PowerShell blocks activation, run the script through the environment directly:

```powershell
.\.venv\Scripts\python.exe screen_scroller.py
```

## Tips

Use bright, even lighting and keep your hand about 40-80 cm from the camera. The green rectangle is the control area. Start with a normal desktop window and test scrolling before using pinch-to-click. Keep the mouse near a screen corner if you need to stop the app using PyAutoGUI's failsafe.

The app intentionally controls only one hand and uses a low-complexity tracking model so it can run on an older dual-core laptop.

The recording mode saves landmark coordinates only; it does not save camera video or upload anything.

Author: Lime.
