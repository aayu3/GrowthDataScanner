import re
import os
import sys
import time
import argparse
from pathlib import Path
from ocr_to_json import parse_relic_data
try:
    import pyautogui
    from PIL import Image, ImageOps
    import numpy as np
    import cv2
    import pytesseract  # Swapped from easyocr
    import pygetwindow as gw
except Exception as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install pytesseract pyautogui pillow opencv-python numpy pygetwindow")
    sys.exit(1)

# --- WINDOWS CONFIGURATION ---
# Resolve Tesseract path: works both when bundled by PyInstaller and when run from source
if getattr(sys, 'frozen', False):
    # Running as a PyInstaller bundle — Tesseract-OCR is next to the exe in _MEIPASS
    _base = Path(sys._MEIPASS)
else:
    # Running from source — Tesseract-OCR is a sibling of this script
    _base = Path(__file__).parent
pytesseract.pytesseract.tesseract_cmd = str(_base / 'Tesseract-OCR' / 'tesseract.exe')
os.environ.setdefault('TESSDATA_PREFIX', str(_base / 'Tesseract-OCR' / 'tessdata'))

def preprocess_for_ocr(pil_img):
    """
    Standardizes image to high-contrast Black text on White background.
    """
    # 1. Grayscale
    gray = ImageOps.grayscale(pil_img)
    arr = np.array(gray)
    
    # 2. Upscale (Kept this as it is vital for small game UI numbers)
    arr = cv2.resize(arr, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    # 3. Black and White (Otsu's Binarization)
    # This turns light text -> 255 (white) and dark background -> 0 (black)
    _, th = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 4. Invert
    # Flips it: Text becomes 0 (black), Background becomes 255 (white)
    inverted = cv2.bitwise_not(th)
    
    return inverted


def find_gfl_window():
    for w in gw.getAllWindows():
        title = (w.title or "").upper()
        if any(k in title for k in ("EXILIUM", "GFL2", "GFL")):
            return w
    return None


def capture_screen(delay: float = 0.0, crop_box=None, save_path: Path = None, window=None, x_start_offset=None):
    if delay > 0:
        time.sleep(delay)

    win = window or find_gfl_window()
    
    if win:
        # win.left is Absolute (Monitor)
        # x_start_offset is Relative (Game Window)
        
        # 1. Calculate the Absolute X (where the click/capture actually starts on your monitor)
        abs_x = win.left + (x_start_offset or 0)
        
        # 2. Calculate the width remaining from that point to the end of the window
        abs_width = (win.left + win.width) - abs_x
        
        # Sanity check: Ensure we aren't starting outside the window
        if abs_width <= 0:
            print(f"Warning: x-start offset {x_start_offset} is larger than window width. Using full window.")
            region = (win.left, win.top, win.width, win.height)
        else:
            region = (abs_x, win.top, abs_width, win.height)
            
        print(f"Capturing Region: Left={region[0]}, Top={region[1]}, Width={region[2]}, Height={region[3]}")
        img = pyautogui.screenshot(region=region)
    else:
        # Fallback for full screen
        img = pyautogui.screenshot()
        if x_start_offset is not None:
            img = img.crop((x_start_offset, 0, img.width, img.height))

    # Standard PIL crop (Relative to the captured image)
    if crop_box:
        img = img.crop(crop_box)
        
    if save_path:
        img.save(save_path)
        
    return img


def ocr_with_tesseract(img_arr):
    # Allow uppercase, lowercase, numbers, and the slash for your artifact count
    # Note: If you only need numbers and the slash, remove the letters to make it even more accurate.
    whitelist = "0123456789/abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXY-Z "
    
    custom_config = f'--oem 3 --psm 6 -c tessedit_char_whitelist={whitelist}'
    
    text = pytesseract.image_to_string(img_arr, config=custom_config)
    return text

def find_total_artifacts(text):
    m = re.search(r'(\d{1,4})\s*/\s*1500', text)
    if m:
        return int(m.group(1))
    if '/1500' in text:
        tokens = re.findall(r'(\d{1,4})', text)
        if tokens:
            return int(tokens[-1])
    return None

def main():
    parser = argparse.ArgumentParser(description="Capture screen and OCR using Tesseract.")
    parser.add_argument("-d", "--delay", type=float, default=0.5, help="Delay before capture")
    parser.add_argument("-e", "--enhance", action="store_true", help="Enable preprocessing")
    parser.add_argument("--crop", type=int, nargs=4, metavar=('L','T','R','B'), help="Optional crop box")
    parser.add_argument("-x", "--x-start", type=int, help="Start capturing from x coordinate")
    args = parser.parse_args()

    crop_box = tuple(args.crop) if args.crop else None
    
    # We pass Path("debug_capture.png") to save the raw crop
    img = capture_screen(
        delay=args.delay, 
        crop_box=crop_box, 
        x_start_offset=args.x_start,
        save_path=Path("debug_capture.png")
    )
    print(f"Raw capture saved to debug_capture.png")

    if args.enhance:
        proc_arr = preprocess_for_ocr(img)
        proc = Image.fromarray(proc_arr)
        # Save the B&W inverted version so you can see what the OCR is reading
        #proc.save("debug_processed.png")
        #print(f"Processed image saved to debug_processed.png")
    else:
        proc = img

    # Get text from Tesseract
    text = ocr_with_tesseract(proc)

    # Clean up and print
    print("\n--- OCR RAW OUTPUT ---")
    print(text.strip())
    print("======================")
    print("--- PARSED JSON ---")
    print(parse_relic_data(text.strip()))

if __name__ == "__main__":
    main()
