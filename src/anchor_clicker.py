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

def build_rows_from_centers(centers, expected_per_row=9, max_rows=7, y_gap_threshold=5):
    """Build rows from centers, merging rows with close y-coordinates and filtering out invalid rows."""
    if not centers:
        return []

    # Sort centers by y-coordinate, then x-coordinate
    centers.sort(key=lambda c: (c[1], c[0]))

    ys = [c[1] for c in centers]
    ady = [ys[i+1] - ys[i] for i in range(len(ys)-1)] or [0]
    median_dy = int(np.median(ady)) if ady else 0

    if y_gap_threshold is None:
        y_gap_threshold = int(median_dy * 1.5)  # Allow some tolerance

    rows = []
    cur_row = [centers[0]]
    prev_y = centers[0][1]

    for cx, cy, cat in centers[1:]:
        if abs(cy - prev_y) > y_gap_threshold:
            # Start a new row if the y-gap exceeds the threshold
            rows.append(cur_row)
            cur_row = []
        cur_row.append((cx, cy, cat))
        prev_y = cy

    if cur_row:
        rows.append(cur_row)

    # Merge rows with close y-coordinates
    merged_rows = []
    for row in rows:
        if not merged_rows:
            merged_rows.append(row)
            continue
        last_row = merged_rows[-1]
        if abs(row[0][1] - last_row[0][1]) <= y_gap_threshold:  # Compare first y-coords of consecutive rows
            # Merge the current row into the last row
            merged_rows[-1].extend(row)
            # Remove duplicates based on x-coordinate only (since y-values are already close)
            seen_x = set()
            unique_row = []
            for cx, cy, cat in merged_rows[-1]:
                if cx not in seen_x:
                    seen_x.add(cx)
                    unique_row.append((cx, cy, cat))
            merged_rows[-1] = unique_row
            merged_rows[-1].sort(key=lambda c: c[0])  # Sort by x-coordinate
        else:
            seen_x = set()
            unique_row = []
            for cx, cy, cat in row:
                if cx not in seen_x:
                    seen_x.add(cx)
                    unique_row.append((cx, cy, cat))
            merged_rows.append(sorted(unique_row, key=lambda c: c[0]))

    # Recalculate median_row_gap after merging rows
    row_gaps = [abs(merged_rows[i][0][1] - merged_rows[i-1][0][1]) for i in range(1, len(merged_rows))]
    median_row_gap = np.median(row_gaps) if row_gaps else 0

    # Adjust filtering to avoid discarding valid merged rows
    if len(merged_rows) > 1 and median_row_gap > 0:
        # Define threshold as 2x the median gap
        gap_threshold = 10 
        filtered_rows = []
        for i, row in enumerate(merged_rows):
            if i == 0:
                # Always keep the first row
                filtered_rows.append(row)
            else:
                # Check if gap from previous kept row is within threshold
                prev_kept_row_y = filtered_rows[-1][0][1]
                current_row_y = row[0][1]
                gap = abs(current_row_y - prev_kept_row_y)
                if abs(median_row_gap - gap) <= gap_threshold:
                    filtered_rows.append(row)
                else:
                    print(f"Skipping row {i+1} due to large gap ({gap} > {gap_threshold})")
        merged_rows = filtered_rows

    # Limit the number of rows to max_rows
    if len(filtered_rows) > max_rows:
        filtered_rows = filtered_rows[:max_rows]

    return filtered_rows

def drag_point_to_point(window, size, from_pt, to_pt, duration=1.5, hold_after=0.35):
    """Perform a single smooth drag using pyautogui: hold the button for the entire move and
    keep it held for a short 'brake' at the end before releasing."""
    abs_from_x = window.left + int(from_pt[0])
    abs_from_y = window.top + int(from_pt[1])
    abs_to_x = window.left + int(to_pt[0])
    abs_to_y = window.top + int(to_pt[1])
    offset = {"720": 15, "1080": 25, "1440": 35, "2160": 50}
    # Move to start, press and hold, perform timed move, pause, then release
    pyautogui.moveTo(abs_from_x, abs_from_y)
    time.sleep(0.025)
    pyautogui.mouseDown()
    time.sleep(0.025)
    pyautogui.moveTo(abs_to_x, abs_to_y-offset[size], duration=duration)
    time.sleep(hold_after)
    pyautogui.mouseUp()
    time.sleep(0.04)

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

def find_image_in_window(window, image_path, confidence=0.6, nms_radius=50):
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

def build_pages_from_rows(rows, window_height, margin=60):
    """Group consecutive rows into pages based on window_height minus margin.
    rows: list of rows (each row is list of (cx,cy,cat)), sorted by y."""
    if not rows:
        return []

    pages = []
    i = 0
    while i < len(rows):
        page = [rows[i]]
        top_y = min(r[1] for r in rows[i])
        j = i + 1
        while j < len(rows):
            # representative y for candidate row
            row_y = min(r[1] for r in rows[j])
            if row_y - top_y <= (window_height - margin):
                page.append(rows[j])
                j += 1
            else:
                break
        pages.append(page)
        i = j
    return pages

def get_resolution_folder(window_width, window_height):
    """Determine the largest resolution folder smaller or equal to the window height."""
    resolutions = [
        (2160, "2160"),
        (1440, "1440"),
        (1080, "1080"),
        (720, "720"),
    ]
    # Iterate through resolutions in descending order
    for res, folder in resolutions:
        if window_height >= res:
            return folder
    return "720"  # Default to the smallest folder if no match

def main():
    """Entry point (updated: adds -s/--scroll-only to perform only the single scroll)."""
    import argparse
    parser = argparse.ArgumentParser(description="Anchor clicker: specify a category or leave blank for all")
    parser.add_argument("-t", "--type", choices=["bulwark", "sentinel", "support", "vanguard"], help="Specific category to scan (default: all)")
    parser.add_argument("-a", "--all", action="store_true", help="Click all found matches instead of only first and last")
    parser.add_argument("-s", "--scroll-only", action="store_true", help="Perform the single scroll only (no clicking); useful for testing scrolling")
    args = parser.parse_args()
    selected_type = args.type
    click_all = args.all
    scroll_only = args.scroll_only

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

    # Determine the resolution folder
    resolution_folder = get_resolution_folder(gfl_window.width, gfl_window.height)
    asset_folder = Path("assets") / resolution_folder
    print(f"Using assets from resolution folder: {resolution_folder}")

    if not asset_folder.exists():
        print(f"Assets folder for resolution '{resolution_folder}' not found. Creating...")
        asset_folder.mkdir(parents=True, exist_ok=True)
        print(f"Please add your assets to the '{asset_folder}' folder.")
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

    # Sort all centers top-left -> bottom-right
    combined_centers.sort(key=lambda t: (t[1], t[0]))
    print(f"\nTotal combined matches: {len(combined_centers)}")

    # Build rows by detecting y jumps
    rows = build_rows_from_centers(combined_centers, expected_per_row=9)
    print(f"Detected {len(rows)} row(s).")
    for ri, row in enumerate(rows, start=1):
        print(f" Row {ri}: {len(row)} items. Xs: {[r[0] for r in row]} Ys (sample): {[r[1] for r in row][:3]}")

    # If user requested scroll-only, perform a single drag from bottom-left -> top-left of detected list and exit
    if scroll_only:
        print("Scroll-only mode: performing a single scroll (no clicks).")
        if len(rows) <= 1:
            print("Not enough rows to scroll (need >1). Exiting.")
            return
        all_points = [(cx, cy) for r in rows for (cx, cy, _) in r]
        bl_x = min(x for x, y in all_points)
        bl_y = max(y for x, y in all_points)
        tl_x = min(x for x, y in all_points)
        tl_y = min(y for x, y in all_points)
        bl = (bl_x, bl_y)
        tl = (tl_x, tl_y)
        print(f" Performing single scroll: drag from bottom-left {bl} to top-left {tl}")
        drag_point_to_point(gfl_window, resolution_folder, bl, tl)
        print("Scroll-only action completed.")
        return

    # ...existing code that handles clicking (first/last or all) ...
    if click_all:
        print("Clicking all matched locations (single pass), then performing one scroll for testing.")
        # click every detected item once (top->bottom, left->right)
        for row in rows:
            for cx, cy, cat in row:
                abs_x = gfl_window.left + cx
                abs_y = gfl_window.top + cy
                print(f" Clicking {cat} at ({abs_x}, {abs_y})")
                pydirectinput.moveTo(abs_x, abs_y)
                time.sleep(0.10)
                pydirectinput.click(abs_x, abs_y)
                time.sleep(0.12)

        # perform a single scroll (drag) from bottom-left of the detected list to top-left
        if len(rows) > 1:
            all_points = [(cx, cy) for r in rows for (cx, cy, _) in r]
            bl_x = min(x for x, y in all_points)
            bl_y = max(y for x, y in all_points)
            tl_x = min(x for x, y in all_points)
            tl_y = min(y for x, y in all_points)
            bl = (bl_x, bl_y)
            tl = (tl_x, tl_y)
            print(f" Scrolling once: drag from bottom-left {bl} to top-left {tl}")
            drag_point_to_point(gfl_window, bl, tl)

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
