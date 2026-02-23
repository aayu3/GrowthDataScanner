"""
Window selection test script for GFL2 with delay
"""

import time
import pydirectinput
import pygetwindow as gw
import sys

def find_gfl_window():
    """Find the GFL2 window"""
    try:
        # Look for GFL2 windows
        windows = gw.getWindowsWithTitle('EXILIUM')
        if not windows:
            windows = gw.getWindowsWithTitle('EXILIUM')
        
        if windows:
            window = windows[0]  # Get the first window
            print(f"Found GFL window: {window.title}")
            print(f"Window position: {window.left}, {window.top}")
            print(f"Window size: {window.width} x {window.height}")
            return window
        else:
            print("No GFL2 window found")
            return None
    except Exception as e:
        print(f"Error finding window: {e}")
        return None

def main():
    print("GFL2 Window Click Test")
    print("=" * 25)
    print("This script tests clicking in GFL2 window")
    print()
    print("Instructions:")
    print("1. Make sure GFL2 is running in Windowed Mode")
    print("2. Tab to the GFL2 window to make it active")
    print("3. Press Enter when GFL2 window is active")
    print("4. The script will wait 5 seconds then click at a relative position")
    print()
    
    # Wait for user to activate the window
    input("Press Enter after activating the GFL2 window...")
    
    # Check if required libraries are available
    try:
        import pygetwindow
        print("✓ pygetwindow available")
    except ImportError:
        print("✗ pygetwindow not available. Install with: pip install pygetwindow")
        print("This is needed to find the GFL window")
        sys.exit(1)
    
    # Find GFL window
    gfl_window = find_gfl_window()
    
    if gfl_window:
        print(f"\nGFL window found at: {gfl_window.left}, {gfl_window.top}")
        print("Window size: {} x {}".format(gfl_window.width, gfl_window.height))
        
        # Wait a moment for user to see the window info
        print("\nWaiting 5 seconds before clicking...")
        print("Make sure the GFL2 window is active and in focus")
        time.sleep(5)
        
        # Test clicking in the window
        print("\nClicking in the GFL window...")
        # Click at position 100, 100 relative to window
        x = gfl_window.left + 100
        y = gfl_window.top + 100
        
        print(f"Moving mouse to ({x}, {y})")
        pydirectinput.moveTo(x, y)
        time.sleep(0.5)
        
        print("Clicking...")
        pydirectinput.click(x, y)
        print("Click successful in GFL window!")
        print("If you see this message, the click worked!")
        
    else:
        print("\nCould not find GFL window. Please:")
        print("1. Make sure GFL2 is running")
        print("2. Make sure it's in Windowed Mode")
        print("3. Try running this script again")

if __name__ == "__main__":
    main()