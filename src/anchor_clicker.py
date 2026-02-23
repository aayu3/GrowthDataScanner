"""
Anchor-based relic clicker using asset images
"""

import time
import pydirectinput
import pygetwindow as gw
import cv2
import numpy as np
import os
from pathlib import Path
import pyautogui
import argparse

def find_gfl_window():
    """Find the GFL2 window"""
    try:
        # Look for GFL2 windows
        windows = gw.getWindowsWithTitle('EXILIUM')
        if not windows:
            windows = gw.getWindowsWithTitle('GFL2')
        if not windows:
            windows = gw.getWindowsWithTitle('GFL')
        
        if windows:
            window = windows[0]  # Get the first window
            print(f"Found GFL window: {window.title}")
            print(f"Window position: {window.left}, {window.top}")
            print(f"Window size: {window.width} x {window.height}")
            return window
        else:
            print("No GFL window found")
            return None
    except Exception as e:
        print(f"Error finding window: {e}")
        return None

def take_window_screenshot(window):
    """Take screenshot of a specific window"""
    try:
        # Use pyautogui to capture window area
        screenshot = pyautogui.screenshot(
            region=(window.left, window.top, window.width, window.height)
        )
        return screenshot
    except Exception as e:
        print(f"Error taking screenshot: {e}")
        return None

def find_image_in_window(window, image_path, confidence=0.8, nms_radius=None):
    """Find an image within the window area using template matching with peak suppression (NMS).
    Returns list of (x, y, w, h) (top-left coords relative to window)."""
    try:
        screenshot = take_window_screenshot(window)
        if not screenshot:
            return []

        # Convert PIL -> OpenCV BGR then to gray
        img_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        template = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            print(f"Template not found or unreadable: {image_path}")
            return []

        # Grayscale the screenshot
        if len(img_cv.shape) == 3:
            img_gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        else:
            img_gray = img_cv.copy()

        th, tw = template.shape[:2]

        # matchTemplate -> result (rows = H-th+1, cols = W-tw+1)
        result = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        res = result.copy()

        # NMS radius: default = half of template size if not provided
        if nms_radius is None:
            nms_h = max(1, th // 2)
            nms_w = max(1, tw // 2)
        else:
            nms_h = nms_w = int(nms_radius)

        matches = []
        while True:
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            if max_val < confidence:
                break
            mx, my = max_loc  # x=col, y=row -> top-left in image coords
            matches.append((mx, my, tw, th))

            # suppress a neighborhood around the detected peak to avoid duplicates
            y1 = max(0, my - nms_h)
            y2 = min(res.shape[0], my + nms_h)
            x1 = max(0, mx - nms_w)
            x2 = min(res.shape[1], mx + nms_w)
            res[y1:y2, x1:x2] = 0.0

        return matches

    except Exception as e:
        print(f"Error in find_image_in_window: {e}")
        return []

def dedupe_items(items, threshold=5):
    """Remove items whose centers are within `threshold` pixels of an already-kept item.
    Items expected as dicts with 'cx' and 'cy' keys. Preserves top-left -> bottom-right order."""
    items_sorted = sorted(items, key=lambda it: (it['y'], it['x']))
    kept = []
    for it in items_sorted:
        cx, cy = it['cx'], it['cy']
        too_close = False
        for k in kept:
            dx = cx - k['cx']
            dy = cy - k['cy']
            if (dx * dx + dy * dy) ** 0.5 <= threshold:
                too_close = True
                break
        if not too_close:
            kept.append(it)
    return kept

def main():
    print("GFL2 Anchor-based Clicker")
    print("=" * 25)
    print("This script uses asset images to find and click relic locations")
    print()

    parser = argparse.ArgumentParser(description="Anchor clicker: specify a category or leave blank for all")
    parser.add_argument("-t", "--type", choices=["bulwark", "sentinel", "support", "vanguard"], help="Specific category to scan (default: all)")
    parser.add_argument("-a", "--all", action="store_true", help="Click all found matches instead of only first and last")
    args = parser.parse_args()
    selected_type = args.type
    click_all = args.all

    # Check if required libraries are available
    try:
        import pygetwindow
        import cv2
        import pyautogui
        print("✓ Required libraries available")
    except ImportError as e:
        print(f"✗ Missing library: {e}")
        print("Install with: pip install pygetwindow opencv-python pyautogui")
        return

    # Find GFL window
    gfl_window = find_gfl_window()

    if not gfl_window:
        print("Could not find GFL window")
        return

    # Check for asset folder
    asset_folder = Path("assets")
    if not asset_folder.exists():
        print("Assets folder not found. Creating...")
        asset_folder.mkdir(exist_ok=True)
        print("Please add your bulwark icon image as 'bulwark.png' in the assets folder")
        return

    categories = ["bulwark", "sentinel", "support", "vanguard"]
    if selected_type:
        print(f"Scanning only category: {selected_type}")
    else:
        print(f"Looking for categories: {categories}")
    print("Waiting 5 seconds to let you position the window...")
    time.sleep(5)

    per_category = {}
    combined_centers = []  # tuples: (cx, cy, category)

    for cat in categories:
        # If a specific type was requested, skip other categories but still include them in summary as empty
        if selected_type and cat != selected_type:
            per_category[cat] = []
            continue

        img_path = asset_folder / f"{cat}.png"
        if not img_path.exists():
            print(f"Asset missing: {img_path.name} (skipping)")
            per_category[cat] = []
            continue

        print(f"Searching for {img_path.name} in window...")
        matches = find_image_in_window(gfl_window, str(img_path), confidence=0.7)
        per_category[cat] = []
        if matches:
            for (x, y, w, h) in matches:
                cx = x + w // 2
                cy = y + h // 2
                per_category[cat].append({'x': x, 'y': y, 'w': w, 'h': h, 'cx': cx, 'cy': cy})
            print(f"  Found {len(matches)} match(es) for {img_path.name}")
        else:
            print(f"  No matches for {img_path.name}")

    # Remove duplicates / near-duplicates within each category (threshold in pixels)
    # Deduplication disabled per request — keep raw matches for now
    # DEDUPE_THRESHOLD = 5
    # for cat in categories:
    #     per_category[cat] = dedupe_items(per_category.get(cat, []), threshold=DEDUPE_THRESHOLD)

    # Rebuild combined_centers from per-category lists (no dedupe)
    combined_centers = [(it['cx'], it['cy'], cat) for cat in categories for it in per_category.get(cat, [])]

    # Print per-category summary (counts + first/last)
    print("\nPer-category summary:")
    for cat in categories:
        items = per_category.get(cat, [])
        if not items:
            print(f"- {cat}: 0")
            continue
        # sort by top-left -> bottom-right (y then x)
        items_sorted = sorted(items, key=lambda it: (it['y'], it['x']))
        first = items_sorted[0]
        last = items_sorted[-1]
        first_abs = (gfl_window.left + first['cx'], gfl_window.top + first['cy'])
        last_abs = (gfl_window.left + last['cx'], gfl_window.top + last['cy'])
        print(f"- {cat}: {len(items)}; first (window): ({first['cx']}, {first['cy']}) -> absolute: {first_abs}; last (window): ({last['cx']}, {last['cy']}) -> absolute: {last_abs}")

    if not combined_centers:
        print("No matches found across selected categories.")
        return

    # Sort all centers top-left -> bottom-right and click first & last overall
    combined_centers.sort(key=lambda t: (t[1], t[0]))
    print(f"\nTotal combined matches: {len(combined_centers)}")
    if click_all:
        print("Clicking all matched locations")
        to_click = combined_centers[:]
    else:
        to_click = [combined_centers[0]] if len(combined_centers) == 1 else [combined_centers[0], combined_centers[-1]]

    for idx, (cx, cy, cat) in enumerate(to_click, start=1):
        abs_x = gfl_window.left + cx
        abs_y = gfl_window.top + cy
        print(f"Clicking {idx}/{len(to_click)} category '{cat}' at window coords ({cx}, {cy}) -> absolute ({abs_x}, {abs_y})")
        pydirectinput.moveTo(abs_x, abs_y)
        time.sleep(0.3)
        pydirectinput.click(abs_x, abs_y)
        time.sleep(0.4)

    print("Clicks completed!")

if __name__ == "__main__":
    main()