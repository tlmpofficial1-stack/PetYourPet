PetYourPet
A small desktop pet for Windows. Add your own PNG character and pet it by hovering your cursor over it. No needs to manage, no mini-games.
Quick Start
Requirements: Windows 10 (version 1809 or later) or Windows 11 (64-bit). 
• Single EXE: Simply run `PetYourPet.exe`. No Python installation required. 
• Portable ZIP: Extract the entire archive and run `PetYourPet.exe` from the folder. The `_internal` folder must remain in the same directory. 
• Click "Open PNG..." to select an image, or drag and drop one onto the checkered canvas. 
• Adjust the size. Click "Adjust Hand Position" and drag the marker to the top of your character's head. 
• Click "Move Pet," drag it to your preferred spot on the desktop, and confirm the position. 
• Click "Done" to save your settings and minimize the app to the system tray.
Hover your cursor over any non-transparent part of your character to pet it. When "move mode" is disabled, mouse clicks pass through the pet.
The PetYourPet icon near the system clock provides access to settings. Right-click the icon to hide/show the pet, move it, bring it back to the screen, or exit the application. Windows may automatically move the icon into the hidden icons menu. If the system tray is unavailable, the app will keep the settings window open; closing this window will exit the program.
Settings
• Pet size, hand size, compression strength, and animation speed. 
• Drag-and-drop positioning for the hand in the preview window; light and dark background options to check your PNG. • Additional options: mirroring, crisp pixels (pixel-art scaling), monitor selection, and language (Russian/English).
• The "Hide when covered by a window" mode takes the active window into account. The "Always on top" mode keeps the pet visible. A separate toggle allows you to exclude full-screen applications.
• Windows autostart is disabled by default. This setting only takes effect after clicking "Done."
• Canceling or pressing the Esc key reverts settings to their previously saved state, including the pet's position.
When importing, the program creates its own copy of the PNG file and crops any transparent margins; the original file remains unchanged. Moving or deleting the source image will not remove the pet. A transparent background is recommended, though opaque backgrounds are also supported and will remain visible. The program accepts PNG files up to 32 MB, 16 MP, and 8192 pixels per side. Larger images are automatically resized to 2048 pixels along their longest side. Only one active character is supported; this version does not include a library or animation import features.
Data and Uninstallation
By default, data is stored in `%LOCALAPPDATA%\PetYourPet\PetYourPet`, containing `settings.json`, a `characters/` folder, and an error log (`app.log`). Images remain on your computer; the application does not upload them to the internet, check for updates, or use telemetry. Communication between multiple instances of the app occurs locally via Qt LocalServer.
To transfer your settings, close the application and copy the entire data folder to another computer. To uninstall, first disable autostart and click "Done," then exit the application via the system tray and delete the program folder. The data folder can be deleted separately. After moving the EXE file to a different folder, disable and re-enable the autostart feature to update the path. If the character goes missing after a monitor is disconnected, select "Bring back to screen" from the system tray menu.
Running from source code
Python 3.12 x64 is recommended. On Windows, from the project folder, run:
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe run.py
Resources and fonts are already included; there is no need to install the fonts on Windows. This version uses the same concept as the original "DesktopPet"—relying on a PNG file and five frames for the hand—but features a new, separate implementation for animations and the user interface. Existing settings from the previous version will not be migrated automatically; to transition, simply import your original PNG file. If the old version of the pet is already running, please close it via the system tray to avoid having two characters on your screen.
Testing and building
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\build.py
The output will be generated in the `release/` directory, containing an EXE file, a portable ZIP archive, a source code archive, and SHA-256 checksums. The build process is performed on Windows using PyInstaller. Windows x64 is the only platform supported in this release. Registry access and window detection are handled via the WinAPI; support for Linux/macOS would require additional development.
To test the application without affecting your current settings, use:
.\.venv\Scripts\python.exe run.py --test-mode --data-dir .qa\manual
The `--test-mode` flag prevents any changes to the autostart configuration, while `--data-dir` isolates the single-instance check. To verify the build:
.\release\PetYourPet.exe --test-mode --data-dir .qa\exe --smoke-output .qa\exe.json
English quick guide
Run PetYourPet.exe, choose Open PNG…, adjust the pet size, and use Position the hand to drag the contact point onto your character's head. Hover over the preview to test petting. Use Move your pet to place the pet on your desktop, then Done to save. Cancel / Escape restores saved settings.
English is selected on first launch. Use More options → Language to switch between English and Russian. The language choice is saved. The tray icon near the clock opens settings, hides the pet or quits the app. The pet passes mouse clicks through to the desktop unless you are moving it. PNG files are copied into local app data and are never uploaded. No Python is required for the compiled release. Extract the whole portable ZIP if using it.
Credits and licenses
Code: MIT. Default character Rufus: supplied by the project owner for use and distribution with this application. Fonts: Press Start 2P and IBM Plex Mono, SIL Open Font License. See THIRD_PARTY.md.
The character used in the original personal DesktopPet is credited to @bruce_bronze. That image is not included in this public source/release; the sample character is separate. Users retain rights to their imported artwork.
