# GrowthDataScanner

Desktop scanner for **Girls' Frontline 2: Exilium** relic data.

The app scans relics from the game window using OpenCV + Tesseract OCR and exports a JSON inventory file.

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/N4N51V6NN9)

## Important

- Supported game window resolutions are currently limited to `1080p`, `1440p`, and `2160p`.

## v1.0.0 Installation (Windows, Recommended)

Use the prebuilt `dist_slim` zip release.

1. Download `GrowthDataScanner-v1.0.0-dist_slim.zip` from the release assets.
2. Right-click the zip and choose **Extract All**.
3. Open the extracted folder and run `GrowthDataScanner.exe`.
4. If Windows SmartScreen appears, click **More info** -> **Run anyway**.
5. Keep the extracted folder structure intact (`_internal` must stay next to `GrowthDataScanner.exe`).

## How To Use

1. Open GFL2 and navigate to your Growth Data inventory.
2. Launch `GrowthDataScanner.exe`.
3. Configure:
- `Output File` (default: `inventory.json`)
- `Start Delay (s)`
- `Scan Delay (s)`
- `Max Relics` (blank = scan all detected relics)
- `Category` (`All`, `bulwark`, `sentinel`, `support`, `vanguard`)
4. Click **Start Scan** and switch to the game window before the delay finishes.
5. Press **F8** any time to cancel gracefully and save partial results.

## Output Format

Scanner output is JSON, e.g.:

```json
{
  "type": "Vanguard",
  "total_level": 6,
  "rarity": "T4",
  "main_skill": { "name": "Smite Boost", "level": 3 },
  "aux_skills": [{ "name": "Burn Smite", "level": 3 }],
  "equipped": "Sharkry"
}
```

## Build From Source (Optional)

Requirements:
- Windows
- Python 3.13+

Install and build:

```powershell
pip install -r requirements.txt
cd src
pyinstaller --clean --noconfirm gui.spec
```

Build output:
- `src/dist/GrowthDataScanner/GrowthDataScanner.exe`

## Notes

- This tool automates input and OCR. Use at your own risk and review game Terms of Service.
- Best results are achieved when the game UI is stable and unobstructed during scanning.
