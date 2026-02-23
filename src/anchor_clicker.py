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

def find_image_in_window(window, image_path, confidence=0.8):
    """Find an image within the window area"""
    try:
        # Take screenshot of the window
        screenshot = take_window_screenshot(window)
        if not screenshot:
            return None
            
        # Convert PIL to OpenCV format
        import PIL.Image
        import io
        img_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # Load template image
        template = cv2.imread(image_path, 0)
        if template is None:
            print(f"Could not load template image: {image_path}")
            return None
            
        # Convert to grayscale if needed
        if len(img_cv.shape) == 3:
            img_gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        else:
            img_gray = img_cv
            
        # Perform template matching
        result = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        
        # Find locations where match exceeds confidence threshold
        locations = np.where(result >= confidence)
        
        if len(locations[0]) > 0:
            # Return the first match
            loc = list(zip(*locations[::-1]))
            return loc[0]  # Return first match coordinates
        else:
            return None
            
    except Exception as e:
        print(f"Error in find_image_in_window: {e}")
        return None

def main():
    print("GFL2 Anchor-based Clicker")
    print("=" * 25)
    print("This script uses asset images to find and click relic locations")
    print()
    
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
    
    # Look for bulwark icon
    bulwark_path = asset_folder / "bulwark.png"
    if not bulwark_path.exists():
        print("bulwark.png not found in assets folder")
        print("Please add your bulwark icon image as 'bulwark.png' in the assets folder")
        return
    
    print(f"Looking for bulwark icon at: {bulwark_path}")
    print("Waiting 5 seconds to let you position the window...")
    time.sleep(5)
    
    # Try to find the bulwark icon
    print("Searching for bulwark icon in window...")
    match_location = find_image_in_window(gfl_window, str(bulwark_path), confidence=0.8)
    
    if match_location:
        x, y = match_location
        # Convert to absolute screen coordinates
        abs_x = gfl_window.left + x
        abs_y = gfl_window.top + y
        
        print(f"Found bulwark icon at window coordinates ({x}, {y})")
        print(f"Converted to absolute coordinates ({abs_x}, {abs_y})")
        
        # Move and click
        print("Moving mouse and clicking...")
        pydirectinput.moveTo(abs_x, abs_y)
        time.sleep(0.5)
        pydirectinput.click(abs_x, abs_y)
        print("Click successful!")
    else:
        print("Bulwark icon not found in window")
        print("Try adjusting the confidence threshold or check your image")

if __name__ == "__main__":
    main()