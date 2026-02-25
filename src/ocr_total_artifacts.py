import re
import sys
from pathlib import Path
import argparse
import time

try:
    import pyautogui
    from PIL import Image, ImageOps
    import numpy as np
    import cv2
    from paddleocr import PaddleOCR
except Exception as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install pyautogui pillow opencv-python numpy paddleocr")
    sys.exit(1)


def enhance_for_ocr(pil_img):
    """Basic preprocessing: grayscale, blur, adaptive threshold (returns PIL.Image)."""
    gray = ImageOps.grayscale(pil_img)
    arr = np.array(gray)
    arr = cv2.GaussianBlur(arr, (3, 3), 0)
    th = cv2.adaptiveThreshold(arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 11, 2)
    return Image.fromarray(th)


def capture_screen(save_path: Path = None, delay: float = 0.0):
    """Capture entire screen, optionally save, and return a PIL.Image."""
    if delay > 0:
        time.sleep(delay)
    img = pyautogui.screenshot()
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(save_path)
    return img


def ocr_with_paddle(pil_img, ocr_model=None):
    """Run PaddleOCR on a PIL image and return concatenated text."""
    if ocr_model is None:
        # single global init (en English)
        ocr_model = PaddleOCR(use_angle_cls=True, lang="en")
    # PaddleOCR expects numpy array (BGR)
    arr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    result = ocr_model.ocr(arr, cls=True)
    lines = []
    for line in result:
        # result format: [[(box), (text, confidence)], ...] or nested for line groups
        if isinstance(line, list):
            for item in line:
                if len(item) >= 2 and isinstance(item[1], (list, tuple)):
                    lines.append(str(item[1][0]))
                elif len(item) >= 2:
                    lines.append(str(item[1]))
        elif isinstance(line, tuple) or isinstance(line, dict):
            # fallback
            try:
                txt = line[1][0]
                lines.append(str(txt))
            except Exception:
                pass
    return "\n".join(lines), ocr_model


def find_total_artifacts(text):
    """Search OCR text for patterns like '123/1500' or '/1500'."""
    m = re.search(r'(\d{1,4})\s*/\s*1500', text)
    if m:
        return int(m.group(1))
    if '/1500' in text:
        tokens = re.findall(r'(\d{1,4})', text)
        if tokens:
            return int(tokens[-1])
    return None


def main():
    parser = argparse.ArgumentParser(description="Capture screen and OCR to find total artifacts (e.g. '123/1500') using PaddleOCR.")
    parser.add_argument("-o", "--output", type=str, default="screenshots/ocr_capture.png", help="Path to save the captured image")
    parser.add_argument("-d", "--delay", type=float, default=0.0, help="Delay before capture (seconds)")
    parser.add_argument("--no-enhance", action="store_true", help="Skip image preprocessing")
    args = parser.parse_args()

    outp = Path(args.output)
    img = capture_screen(outp, delay=args.delay)
    proc_img = img if args.no_enhance else enhance_for_ocr(img)

    text, _ = ocr_with_paddle(proc_img)
    total = find_total_artifacts(text)

    print("OCR raw text:")
    print("----------------")
    print(text.strip())
    print("----------------")
    if total is not None:
        print(f"Detected total artifacts: {total} / 1500")
    else:
        print("Did not find a '/1500' pattern in OCR output.")

    print(f"Saved capture to: {outp.resolve()}")


if __name__ == "__main__":
    main()