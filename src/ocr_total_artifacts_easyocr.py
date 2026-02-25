import re
import sys
import time
import argparse
from pathlib import Path

try:
    import pyautogui
    from PIL import Image, ImageOps
    import numpy as np
    import cv2
    import easyocr
    import pygetwindow as gw
except Exception as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install easyocr pyautogui pillow opencv-python numpy pygetwindow")
    sys.exit(1)


def preprocess_for_ocr(pil_img):
    gray = ImageOps.grayscale(pil_img)
    arr = np.array(gray)
    arr = cv2.GaussianBlur(arr, (3, 3), 0)
    _, th = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th  # numpy array (grayscale/binary)


def find_gfl_window():
    """Return the first window whose title contains EXILIUM / GFL2 / GFL (case-insensitive), or None."""
    for w in gw.getAllWindows():
        title = (w.title or "").upper()
        if any(k in title for k in ("EXILIUM", "GFL2", "GFL")):
            return w
    return None


def capture_screen(delay: float = 0.0, crop_box=None, save_path: Path = None, window=None):
    """Capture the GFL window if found (or full screen otherwise)."""
    if delay > 0:
        time.sleep(delay)

    win = window or find_gfl_window()
    if win:
        # pygetwindow window geometry: left, top, width, height
        region = (win.left, win.top, win.width, win.height)
        img = pyautogui.screenshot(region=region)
    else:
        img = pyautogui.screenshot()

    if crop_box:
        img = img.crop(crop_box)
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(save_path)
    return img


def ocr_with_easyocr(pil_img, reader=None):
    if reader is None:
        reader = easyocr.Reader(['en'], gpu=False)
    img_arr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    results = reader.readtext(img_arr, detail=1)  # list of (bbox, text, conf)
    texts = [r[1] for r in results if r and len(r) >= 2]
    return "\n".join(texts), reader


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
    parser = argparse.ArgumentParser(description="Capture screen and OCR to find total artifacts (e.g. '123/1500') using EasyOCR.")
    parser.add_argument("-d", "--delay", type=float, default=0.5, help="Delay before capture (seconds)")
    parser.add_argument("-e", "--enhance", action="store_true", help="Enable preprocessing (default: off)")
    parser.add_argument("--crop", type=int, nargs=4, metavar=('L','T','R','B'), help="Optional crop box (left top right bottom)")
    args = parser.parse_args()

    crop_box = tuple(args.crop) if args.crop else None
    img = capture_screen(delay=args.delay, crop_box=crop_box)

    # Use raw capture by default; run preprocessing only if --enhance is provided
    if args.enhance:
        proc_arr = preprocess_for_ocr(img)
        proc = Image.fromarray(proc_arr)
    else:
        proc = img

    text, _ = ocr_with_easyocr(proc)

    # Only output detected text (single line)
    print(text.strip())


if __name__ == "__main__":
    main()