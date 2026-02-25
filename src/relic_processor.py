"""
Anchor-based relic clicker using asset images
"""

import time
import pydirectinput
import pygetwindow as gw
import cv2
import numpy as np
from pathlib import Path
import pyautogui
from ocr_total_artifacts_tesseract import capture_screen, preprocess_for_ocr, ocr_with_tesseract
from ocr_to_json import parse_relic_data, extract_relic_count
from resolution_bounds import RELIC_DATA_CUTOFFS_X
import json

def deduplicate_row_by_x(row, x_threshold=5):
    """
    Sorts a row by X and removes items that are too close to each other.
    """
    if not row:
        return []
    
    # Sort by x-coordinate
    row.sort(key=lambda c: c[0])
    
    cleaned_row = [row[0]]
    for i in range(1, len(row)):
        current_x = row[i][0]
        last_cleaned_x = cleaned_row[-1][0]
        
        # Only keep if it's further away than the threshold
        if abs(current_x - last_cleaned_x) > x_threshold:
            cleaned_row.append(row[i])
        else:
            print(f"  Removing duplicate/noise at X: {current_x} (too close to {last_cleaned_x})")
            
    return cleaned_row

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
            merged_rows.append(sorted(row, key=lambda c: c[0]))
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
            merged_rows.append(sorted(row, key=lambda c: c[0]))
    
    # Remove outlier rows that have too few items, in this case 2 or less, but always keep the last row even if it has fewer items since it may just be a shorter final row
    merged_rows = [row for row in merged_rows[:-1] if len(row) > 2] + [merged_rows[-1]] if merged_rows else []

    # Recalculate median_row_gap after merging rows
    row_gaps = [abs(merged_rows[i][0][1] - merged_rows[i-1][0][1]) for i in range(1, len(merged_rows))]
    median_row_gap = np.median(row_gaps) if row_gaps else 0

    # Adjust filtering to avoid discarding valid merged rows
    if len(merged_rows) > 1 and median_row_gap > 0:
        # Define threshold as 2x the median gap
        gap_threshold = 3
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
        merged_rows = filtered_rows

    # Limit the number of rows to max_rows
    if len(merged_rows) > max_rows:
        merged_rows = merged_rows[:max_rows]

    # Check for rows that need filling from previous rows
    filled_rows = []
    
    # First, find a complete row (with expected number of items) to use as reference
    reference_row = None
    for row in merged_rows:
        if len(row) == expected_per_row:
            reference_row = row
            break
    if reference_row:
        for i, row in enumerate(merged_rows):
            
            # If current row has fewer items than expected, try to fill from reference row
            if len(row) < expected_per_row:
                # Get x coordinates from current row
                current_x_coords = set(cx for cx, cy, cat in row)
                
                # Get x coordinates from reference row (if found)
                reference_x_coords = set(cx for cx, cy, cat in reference_row) if reference_row else set()
                
                # Find missing x coordinates from reference row that aren't already in current row
                missing_x_coords = reference_x_coords - current_x_coords
                
                # Filter out near misses (coordinates that are very close to existing ones)
                filtered_missing_x_coords = []
                for missing_x in missing_x_coords:
                    is_near_miss = False
                    for existing_x in current_x_coords:
                        if abs(missing_x - existing_x) <= 7:  # Near miss threshold
                            is_near_miss = True
                            break
                    if not is_near_miss:
                        filtered_missing_x_coords.append(missing_x)
                
                # If we have missing coordinates to add
                if filtered_missing_x_coords:                    
                    # Get the Y coordinate of the current row (all items in a row should have same Y)
                    current_row_y = row[0][1]
                    
                    # Create new row with filled coordinates
                    filled_row = row.copy()
                    for missing_x in filtered_missing_x_coords:
                        # Use the current row's Y coordinate, not the reference row's Y coordinate
                        y_coord = current_row_y
                        
                        filled_row.append((missing_x, y_coord, None))  # None for category
                
                    # Sort the filled row by x coordinate
                    filled_row.sort(key=lambda x: x[0])
                    filled_rows.append(filled_row)
                else:
                    filled_rows.append(row)
            else:
                filled_rows.append(row)

    processed_rows = []
    for row in filled_rows:
        # If the row is "too full", it's likely double-detections or noise
        if len(row) > expected_per_row:
            cleaned = deduplicate_row_by_x(row, x_threshold=5)
            processed_rows.append(cleaned)
        else:
            row.sort(key=lambda c: c[0])
            processed_rows.append(row)

    # Final validation: ensure all rows except the last have the expected number of items
    final_rows = []
    for i, row in enumerate(processed_rows):
        if i == len(processed_rows) - 1:  # Last row can have fewer items
            final_rows.append(row)
        elif len(row) == expected_per_row:  # Non-last rows should have expected number
            final_rows.append(row)
        else:  # If a non-last row has fewer items, we can't really do anything about it
            final_rows.append(row)

    return final_rows

def drag_point_to_point(window, size, from_pt, to_pt, duration=1.5, hold_after=0.35):
    """Perform a single smooth drag using pyautogui: hold the button for the entire move and
    keep it held for a short 'brake' at the end before releasing."""
    abs_from_x = window.left + int(from_pt[0])
    abs_from_y = window.top + int(from_pt[1])
    abs_to_x = window.left + int(to_pt[0])
    abs_to_y = window.top + int(to_pt[1])
    offset = {"720": 15, "1080": 25, "1440": 30, "2160": 50}
    # Move to start, press and hold, perform timed move, pause, then release
    pyautogui.moveTo(abs_from_x, abs_from_y)
    time.sleep(0.01)
    pyautogui.mouseDown()
    time.sleep(0.01)
    pyautogui.moveTo(abs_to_x, abs_to_y-offset[size], duration=duration)
    time.sleep(hold_after)
    pyautogui.mouseUp()
    time.sleep(0.01)

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
    import argparse
    parser = argparse.ArgumentParser(description="Anchor clicker: specify a category or leave blank for all")
    parser.add_argument("-t",  "--type", choices=["bulwark", "sentinel", "support", "vanguard"], help="Specific category to scan (default: all)")
    parser.add_argument("-n", "--num", type=int, help="Limit processing to a specific number of relics (e.g., 80)")
    args = parser.parse_args()
    selected_type = args.type


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
    print("Waiting 2 seconds to let you position the window...")
    time.sleep(2)

    per_category = {}
    combined_centers = []  # tuples: (cx, cy, category)

    for cat in categories:
        # If a specific type was requested, skip other categories but still include them in summary as empty
        if selected_type and cat != selected_type:
            per_category[cat] = []
            continue

        img_path = asset_folder / f"{cat}.png"
        if not img_path.exists():
            per_category[cat] = []
            continue

        matches = find_image_in_window(gfl_window, str(img_path), confidence=0.7)
        per_category[cat] = []
        if matches:
            for (x, y, w, h) in matches:
                cx = x + w // 2
                cy = y + h // 2
                per_category[cat].append({'x': x, 'y': y, 'w': w, 'h': h, 'cx': cx, 'cy': cy})

    # Rebuild combined_centers from per-category lists (no dedupe)
    combined_centers = [(it['cx'], it['cy'], cat) for cat in categories for it in per_category.get(cat, [])]

    # Sort all centers top-left -> bottom-right
    combined_centers.sort(key=lambda t: (t[1], t[0]))
    print(f"\nTotal combined matches: {len(combined_centers)}")

    # Build rows by detecting y jumps
    rows = build_rows_from_centers(combined_centers, expected_per_row=9)

    # Grab Total relics
    img = preprocess_for_ocr(capture_screen(window=gfl_window))
    detected_total = extract_relic_count(ocr_with_tesseract(img))

    if args.num:
        # If user provides -n 80, but OCR says there are only 50, use 50.
        if detected_total:
            num_relics = min(detected_total, args.num)
        else:
            num_relics = args.num
    else:
        num_relics = detected_total if detected_total else 9999

    processed_count = 0
    relic_data_list = []
    
    if num_relics is None:
        num_relics = 9999 

    # Get the X-cutoff for the OCR panel based on resolution
    x_offset = RELIC_DATA_CUTOFFS_X.get(resolution_folder, 1200)

    # --- Main Processing Loop ---
    is_last_page = False
    skip_first_row = False  # To avoid re-clicking the top row after a scroll

    while processed_count < num_relics and not is_last_page:
        # A. Find anchors on current screen
        combined_centers = []
        for cat in categories:
            img_path = asset_folder / f"{cat}.png"
            if img_path.exists():
                matches = find_image_in_window(gfl_window, str(img_path), confidence=0.7)
                for (x, y, w, h) in matches:
                    combined_centers.append((x + w // 2, y + h // 2, cat))
        
        if not combined_centers:
            break

        # B. Group into rows
        rows = build_rows_from_centers(combined_centers, expected_per_row=9)
        
        # Check if this is the final page (any row except the last is incomplete)
        if len(rows[-1]) < 9:
            is_last_page = True

        # C. Process Row by Row
        items_to_process = []
        is_inventory_end = (detected_total and (detected_total - processed_count) < 54) and skip_first_row

        if is_inventory_end:
            remaining_inv = detected_total - processed_count
            print(f"End of inventory reached. Processing the last {remaining_inv} items directly to accommodate scroll offset.")
            flat_all = [item for row in rows for item in row]
            items_to_process = flat_all[-remaining_inv:]
            
            # Further truncate if -n requires fewer items
            if (num_relics - processed_count) < len(items_to_process):
                items_to_process = items_to_process[:(num_relics - processed_count)]
        else:
            for row_idx, row in enumerate(rows):
                if skip_first_row and row_idx == 0:
                    print("Skipping already processed top row.")
                    continue
                for item in row:
                    items_to_process.append(item)
                    if len(items_to_process) >= (num_relics - processed_count):
                        break
                if len(items_to_process) >= (num_relics - processed_count):
                        break

        for cx, cy, cat in items_to_process:
            if processed_count >= num_relics:
                break

            # 1. Move and Click
            abs_x = gfl_window.left + cx
            abs_y = gfl_window.top + cy
            pydirectinput.click(abs_x, abs_y)
                
            # 2. Wait for UI to update side panel
            time.sleep(0.25) 

            # 3. Capture and OCR the Data Panel
            # We use the relative x_offset to ignore the relic grid
            relic_img = capture_screen(window=gfl_window, x_start_offset=x_offset)
            relic_text = ocr_with_tesseract(preprocess_for_ocr(relic_img))
            
            # 4. Convert to JSON
            relic_json = parse_relic_data(relic_text)
            relic_data_list.append(relic_json)
            
            processed_count += 1
            print(f"[{processed_count}/{num_relics}] Processed: {relic_json['type']} | {relic_json['rarity']}")

        # D. Scroll Logic
        if processed_count < num_relics and not is_last_page:
            print("Finished page. Scrolling...")
            
            # Identify scroll points: Bottom-Left to Top-Left
            # We use the actual detected centers to ensure the drag stays within the grid
            all_points = [(cx, cy) for r in rows for (cx, cy, _) in r]
            bl_x = min(x for x, y in all_points)
            bl_y = max(y for x, y in all_points)
            tl_x = bl_x # Keep it vertical
            tl_y = min(y for x, y in all_points)
            
            drag_point_to_point(gfl_window, resolution_folder, (bl_x, bl_y), (tl_x, tl_y))
            
            # After scrolling, the bottom row of the PREVIOUS screen 
            # is now the top row of the NEW screen.
            skip_first_row = True
            time.sleep(1.0) # Wait for scroll animation to settle
        else:
            print("Processing complete or reached the end of the inventory.")
            break

    # Final Output
    print(f"\nSuccessfully logged {len(relic_data_list)} relics.")
    # You could save to file here: json.dump(r
    json.dump(relic_data_list, open('inventory.json', 'w'))
if __name__ == "__main__":
    main()
