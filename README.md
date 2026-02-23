# GFL2-Exilium-Scanner 🎯

An automated data-mining tool for **Girls' Frontline 2: Exilium** that captures and digitizes attachment/equipment stats from the PC client. This tool bridges the gap between the game client and community-driven optimizers.

---

## 📖 Overview

Unlike traditional scanners that rely on network interception (which can be prone to encryption changes or bans), this scanner uses **Computer Vision (CV)** and **AI-powered Optical Character Recognition (OCR)** to read data directly from the screen—exactly as a human would.

### Why this approach?

* **Safe:** No memory injection or packet modification.
* **Reliable:** Works independently of game-server encryption.
* **Flexible:** Easily adaptable to new game UI updates.

---

## ✨ Key Features

* **Window Awareness:** Automatically detects the GFL2 process and scales coordinate mapping to your resolution.
* **ROI Focusing:** Only processes specific regions (Name, Main Stat, Substats) to maximize speed and accuracy.
* **Intelligent Correction:** Uses Levenshtein distance matching against a GFL2-specific dictionary to fix OCR typos (e.g., "Attock" ➔ "ATK").
* **JSON Export:** Generates structured data compatible with web-based optimizers.

---

## 🚀 The Tech Stack

| Component | Technology | Role |
| --- | --- | --- |
| **Language** | Python 3.10+ | Core logic and scripting. |
| **Vision** | OpenCV (`cv2`) | Image thresholding, grayscaling, and UI anchor detection. |
| **OCR** | PaddleOCR | High-speed, AI-driven text recognition (optimized for stylized fonts). |
| **Automation** | PyDirectInput | Hardware-level mouse/keyboard simulation for inventory scrolling. |
| **Capture** | BetterCam | Low-latency Windows screen capture. |

---

## 🛠️ Project Structure

```text
GFL2-Scanner/
├── src/
│   ├── capture.py      # Window detection and screenshot logic
│   ├── processor.py    # OpenCV filtering (Grayscale, Thresholding)
│   ├── ocr_engine.py   # PaddleOCR implementation & result cleaning
│   └── dictionary.py   # Valid GFL2 stats & names for error correction
├── assets/
│   └── anchors/        # Reference images for UI button detection
├── output/             # Scanned JSON data files
└── main.py             # Entry point: The scanning loop

```

---

## ⚙️ How It Works (The Pipeline)

1. **Locate:** Uses OpenCV `matchTemplate` to find a UI "anchor" (like the Warehouse icon) to establish .
2. **Capture:** Snaps the equipment detail panel.
3. **Clean:** Applies a binary threshold to isolate white text from the semi-transparent background.
4. **Read:** PaddleOCR converts the "clean" image into raw text.
5. **Validate:** The script checks the text against `dictionary.py`.
6. **Next:** `PyDirectInput` clicks the next item in the grid and repeats.

---

## 📋 Requirements

* GFL2: Exilium PC Client (Windowed Mode recommended)
* Python 3.10+
* `pip install opencv-python paddleocr paddlepaddle pydirectinput bettercam`

---

## 🛡️ Disclaimer

This project is for educational and personal use only. While it does not modify game files, always be aware of the game's Terms of Service regarding automation. Use at your own risk.

---

## Flower/Growth Data/Relic Overview

There are four types of Relics with distinct icons in the top left
Blue - Bulwark
Purple- Vanguard
Green - Support
Red - Sentinel

Furthermore there are different rarities for artifacts, there are Yellow for the highest, purple for the middle and blue for the lowest

Each relic can have up to three skills, 1 main skill and up to 2 auxillary skills. These skills also have categories, corresponding to the four types of relics, Bulwark, Vanguard, Support, and Sentinel. The main skill of a relic always corresponds to the type of the relic.

Finally each skill has a max possible level main skills always have a max level of 6, I will list all possible skills now
There are some relic skills that are elemental, in that case they will be denoted with {Element}, e.g. "{Element} resistance"
Here is a list of elements:
- Physical
- Burn
- Electric
- Freeze
- Corrosion
- Hydro

Bulwark Skills
- Main:
    - Pinpoint Defense
    - Annular Defense
    - Defense Boost
    - HP Boost
- Auxillary:
    - Lone Rider Countermeasures - 5
    - Breakout Countermeasures - 5
    - {Element} Resistance - 5
    - Lex Talionis - 3
    - Boss Countermeasures - 2

Vanguard Skills
- Main:
    - Smite Boost
    - Beheading Blade
    - Precision Blow
    - Area Smite
- Auxillary:
    - Ambush Mastery - 5
    - Onslaught Mastery - 5
    - {Element} Smite - 5
    - CQC Elite - 3
    - Bloodthirst - 3
    - Shock and Awe - 2

Support Skills
- Main:
    - Attack Unity
    - HP Unity
    - Healing Boost
    - Fighting Spirit
- Auxillary:
    - Ichor Resonance - 5
    - Ichor Conversion - 5
    - {Element} Unity - 5
    - Purification Feedback - 3
    - Life Recovery - 3
    - Equilibrium Recovery - 2

Sentinel Skills
- Main:
    - Attack Boost
    - Thronebreaker
    - Pinpoint Specialization
    - Area Specialization
- Auxillary:
    - Raid Stance - 5
    - Onslaught Stance - 5
    - {Element} Boost - 5
    - Critical Boost - 3
    - Follow-Up Strike - 2