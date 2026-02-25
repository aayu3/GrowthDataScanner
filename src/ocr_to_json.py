import re
from relic_data import RELIC_TYPES, ELEMENTS, DOLL_NAMES

def get_rarity(total_lv):
    if total_lv >= 5:
        return "Yellow"
    elif total_lv >= 3:
        return "Purple"
    elif total_lv >= 1:
        return "Blue"
    
def extract_relic_count(text):
    """
    Extracts the current number from strings like '622/1500', 
    'Own622/1500', or 'Count: 622 / 1500'.
    """
    # Pattern explanation:
    # (\d+)      : Capture one or more digits (this is our current count)
    # \s* : Allow for optional spaces
    # /          : The literal slash separator
    # \s* : Allow for more optional spaces
    # 1500       : The hardcoded maximum limit
    match = re.search(r'(\d+)\s*/\s*1500', text)
    
    if match:
        return int(match.group(1))
    
    # Fallback: If 1500 is mangled but the slash exists
    # Find digits immediately preceding a slash
    fallback = re.search(r'(\d+)/', text)
    if fallback:
        return int(fallback.group(1))
        
    return None

def clean_equipped_text(raw_text):
    """
    Directly extracts doll name from the raw text. 
    partial_ratio excels at finding 'Yoohee' inside 'YooheeAlreadyEquipped'.
    """
    # Focus only on the last chunk of text where doll names live
    search_area = raw_text[-100:] 
    
    # scorer=fuzz.partial_ratio is key for substrings
    match = process.extractOne(search_area, DOLL_NAMES, scorer=fuzz.partial_ratio)
    
    if match and match[1] > 85:
        return match[0]
    return None

import re

def parse_relic_data(raw_text):
    # 1. Normalize OCR text: Remove newlines and extra spaces to create one long string
    # We leave case as-is for now, but usually, it's safer to .lower() everything
    flat_text = "".join(raw_text.split())
    
    # 2. Extract Levels using Regex
    # We find all "Lv" followed by a number
    # e.g., 'Lv2AttackUnity' -> ('2', 'AttackUnity')
    lv_pattern = r"Lv\.?(\d)"
    lv_matches = list(re.finditer(lv_pattern, raw_text))
    
    extracted_skills = []
    
    # For each 'Lv' found, look at the text immediately following it (approx 30 chars)
    for i, match in enumerate(lv_matches):
        start = match.end()
        # Look ahead to the next 'Lv' or the end of the string
        end = lv_matches[i+1].start() if i+1 < len(lv_matches) else len(raw_text)
        chunk = "".join(raw_text[start:end].split()) # The "dirty" skill name
        
        # Check this chunk against our master skill list
        found_skill = None
        
        # We need a flat list of all possible skill names (Support, Vanguard, etc.)
        for r_type, r_data in RELIC_TYPES.items():
            # Combine Main and Aux for searching
            possible_names = r_data["main_skills"] + list(r_data["aux_skills"].keys())
            
            for name in possible_names:
                # Handle {Element} logic
                if "{Element}" in name:
                    for el in ELEMENTS:
                        real_name = name.replace("{Element}", el)
                        if real_name.replace(" ", "") in chunk:
                            found_skill = real_name
                            break
                # Handle standard names
                elif name.replace(" ", "") in chunk:
                    found_skill = name
                
                if found_skill: break
            if found_skill: break
            
        if found_skill:
            extracted_skills.append({
                "name": found_skill,
                "level": int(match.group(1))
            })

    # 3. Categorize Skills and Determine Relic Type
    main_skill = None
    aux_skills = []
    relic_type = "Unknown"

    for s in extracted_skills:
        for r_name, r_data in RELIC_TYPES.items():
            if s["name"] in r_data["main_skills"]:
                main_skill = s
                relic_type = r_name
                break
        else:
            if s not in aux_skills:
                aux_skills.append(s)

    # 4. Doll Detection (Equipped)
    # Search for doll names in the flattened text
    equipped = None
    for doll in DOLL_NAMES:
        if doll.replace(" ", "") in flat_text:
            equipped = doll
            break

    # 5. Rarity and Totals
    total_lv = sum(s["level"] for s in extracted_skills)
    
    # Rarity logic: 5-6=Legendary, 3-4=Epic, else Rare
    if total_lv >= 5: rarity = "Legendary"
    elif total_lv >= 3: rarity = "Epic"
    else: rarity = "Rare"

    return {
        "type": relic_type,
        "total_level": total_lv,
        "rarity": rarity,
        "main_skill": main_skill,
        "aux_skills": aux_skills,
        "equipped": equipped
    }