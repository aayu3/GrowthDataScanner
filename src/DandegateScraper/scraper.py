import requests
import json
import re
import os
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
BASE_API_URL = "https://api.dandegate.net/api/dolls?limit=all"
BASE_REMOLD_URL = "https://dandegate.net/dolls/{doll_name}/remolding"

# Output file
OUTPUT_FILE = "dolls.json"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_all_dolls():
    """Fetches the list of all dolls from the Dandegate API."""
    print("Fetching doll list...")
    response = requests.get(BASE_API_URL, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    if 'data' in data:
        return [d['name'] for d in data['data']]
    return []

def extract_remold_data(doll_name, soup):
    """Parses HTML soup for bonues and allowed slots."""
    result = {
        "allowed_slots": {},
        "bonuses": []
    }

    # 1. Parse 'allowed_slots' from images
    # Example src: https://cdn.dandegate.net/remold/RemoldGrowthDataRelic_Support.png
    images = soup.find_all('img')
    slots = {}
    for img in images:
        src = img.get('src', '')
        match = re.search(r'RemoldGrowthDataRelic_([a-zA-Z]+)\.png', src)
        if match:
            slot_type = match.group(1)
            slots[slot_type] = slots.get(slot_type, 0) + 1
            
    # The relic images are rendered twice in the DOM (perhaps mobile vs desktop view)
    # We divide the counts by 2 to get the actual number
    for slot_type in slots:
        slots[slot_type] = slots[slot_type] // 2
    
    result["allowed_slots"] = slots

    # 2. Parse 'bonuses' from the remolding table
    # Table headers are: ["Stage", "Level", "Requirements", "Effect"]
    target_table = None
    for table in soup.find_all('table'):
        headers = [th.text.strip() for th in table.find_all('th')]
        if len(headers) >= 4 and "Effect" in headers and "Requirements" in headers:
            target_table = table
            break
            
    if target_table:
        # Find index of Requirements and Effect
        req_idx = headers.index("Requirements")
        eff_idx = headers.index("Effect")
        
        rows = target_table.find_all('tr')
        tier = 1
        for row in rows[1:]: # Skip headers
            cols = row.find_all('td')
            if len(cols) > max(req_idx, eff_idx):
                effect_col = cols[eff_idx]
                req_col = cols[req_idx]
                
                # Extract effect text
                effect_text = effect_col.text.strip()
                
                # If there's no effect text, skip this tier (sometimes lines are blank)
                if not effect_text:
                    continue
                
                bonus_entry = {
                    "tier": tier,
                    "description": effect_text
                }
                
                # Extract requirements from images within the Requirements column
                for img in req_col.find_all('img'):
                    src = img.get('src', '')
                    alt = img.get('alt', '')
                    match = re.search(r'Remold(?:Material)?_?([a-zA-Z]+)\.png', src, re.IGNORECASE)
                    
                    # Some images might not use RemoldMaterial prefix but rather ImagoFactor
                    if not match:
                        match = re.search(r'ImagoFactor_([a-zA-Z]+)\.png', src, re.IGNORECASE)
                    
                    req_name = alt or (match.group(1) if match else "Unknown")
                    
                    # Next sibling is usually the text or paragraph tag with the count
                    next_sibling_text = None
                    # find parent or next sibling to get the count
                    # usually it is inside a <p> or <span> immediately following the <img> in a common parent div
                    parent_div = img.parent
                    if parent_div:
                        count_tag = parent_div.find(['p', 'span'])
                        if count_tag:
                            next_sibling_text = count_tag.text.strip()
                            
                    if next_sibling_text and next_sibling_text.isdigit():
                        bonus_entry[req_name] = int(next_sibling_text)
                    
                result["bonuses"].append(bonus_entry)
                tier += 1

    return result

def main():
    dolls = get_all_dolls()
    print(f"Loaded {len(dolls)} dolls from API.")
    
    output_data = {}
    
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                output_data = json.load(f)
        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for doll in dolls:
            url = BASE_REMOLD_URL.format(doll_name=doll.lower().replace(" ", "-"))
            print(f"Scraping {doll} at {url}...")
            try:
                page.goto(url, wait_until="networkidle")
                # wait for tables to appear, timeout after 10s
                page.wait_for_selector('table', timeout=10000)
                
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                doll_data = extract_remold_data(doll, soup)
                
                if doll_data["bonuses"]:
                    output_data[doll] = doll_data
                    print(f"Successfully extracted {len(doll_data['bonuses'])} tiers for {doll}")
                else:
                    print(f"No bonuses found for {doll}")
                    
            except Exception as e:
                print(f"Failed to scrape {doll}: {e}")
                
            time.sleep(0.5) # Be nice to the server
            
        browser.close()

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
        
    print(f"Saved results to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
