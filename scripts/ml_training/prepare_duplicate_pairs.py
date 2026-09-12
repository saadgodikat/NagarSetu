"""
Constructs a comprehensive, grounded duplicate pair benchmark dataset
for evaluating NagarIQ duplicate detection models (Jaccard, TF-IDF, Semantic Sentence-Transformers).
"""

import json
import os
import random
from pathlib import Path

random.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
INPUT_DATA_PATH = BASE_DIR / "data" / "processed" / "text_test.json"
OUTPUT_PAIRS_PATH = BASE_DIR / "data" / "processed" / "duplicate_benchmark_pairs.json"

PARAPHRASE_TEMPLATES = {
    "pothole": [
        ("Huge pothole on main road causing severe traffic hazard", "Deep crater in asphalt roadway creating dangerous driving conditions"),
        ("Dangerous road cave-in and potholes near chowk", "Asphalt surface damaged with open ditch causing accidents"),
        ("Crater on the street damaging vehicles and slowing traffic", "Severe road damage with large holes affecting commuting"),
        ("Multiple potholes on the lane needing immediate tar work", "Road surface completely broken down with hazardous pits"),
    ],
    "garbage": [
        ("Garbage heap rotting and dumping waste near corner", "Piles of uncollected trash and rotting refuse accumulating by roadside"),
        ("Overflowing dustbin and scattered waste creating stink", "Municipal trash bin full to the brim with rubbish spread everywhere"),
        ("Illegal waste disposal site emitting foul smell", "Decaying garbage discarded openly causing severe odor and unhygienic conditions"),
        ("Litter and organic waste dumped on walkway", "Debris and food waste blocking pedestrian path without clearing"),
    ],
    "drainage": [
        ("Overflowing sewage water from clogged drain line", "Black wastewater backing up and flooding street from choked gutter"),
        ("Open manhole and blocked gutter overflowing onto road", "Sewer drain completely choked causing dirty water to spill on walkway"),
        ("Stagnant dirty sewer water breeding mosquitoes", "Filthy drain backup standing in street creating health hazard"),
        ("Underground pipeline choked leading to wastewater inundation", "Clogged stormwater drain overflowing with noxious sludge"),
    ],
    "streetlight": [
        ("Streetlight not functioning, area in complete darkness", "Road lamps broken and out of order making neighborhood pitch black"),
        ("Flickering and dead pole light causing safety hazard", "Public lighting failed on street creating unsafe dark stretch at night"),
        ("Municipal street lamp broken for over a week", "Electric light pole not turning on leaving the entire corner dark"),
        ("Dark street prone to theft due to non working lights", "No illumination on public road because lampposts are extinguished"),
    ],
    "water_leakage": [
        ("Drinking water pipeline burst wasting fresh water", "Main supply pipe ruptured with thousands of liters of clean water leaking"),
        ("Municipal tap leaking continuously on the lane", "Water distribution line broken and flooding the residential street"),
        ("Contaminated muddy water coming from municipal tap", "Dirty tap supply with foul discolored drinking water reaching homes"),
        ("Heavy water gushing out from cracked main valve", "Major leakage in municipal supply conduit causing clean water wastage"),
    ],
    "other": [
        ("Fallen tree branch blocking walkway in public park", "Large tree limb collapsed across footpath obstructing pedestrians"),
        ("Stray animal menace near community garden", "Aggressive packs of stray dogs wandering and causing danger to residents"),
        ("Illegal commercial banner hanging dangerously low", "Unauthorized hoarding structure loose and posing hazard to commuters"),
        ("Broken park bench and damaged public playground equipment", "Public park infrastructure broken and hazardous for children"),
    ],
}

TRANSLITERATED_MARATHI_PAIRS = [
    ("Huge pothole on main road near Tuljapur Naka", "Tuljapur Naka javal rastyavar motha gadda padla ahe", "pothole"),
    ("Road broken with deep pits near Solapur Station", "Solapur station javal rasta kharab jhala ahe gaadi chalavta yet nahi", "pothole"),
    ("Garbage heap rotting and emitting foul smell", "Kachra khup divasapasun saachla ahe aani khup ghan vas yet ahe", "garbage"),
    ("Waste not picked up by municipal truck", "Kachryachi gaadi aali nahi kachra rastyavar padla ahe", "garbage"),
    ("Overflowing sewage drain flooding road", "Gatar che paani rastyavar vahat ahe aani ghan ahe", "drainage"),
    ("Clogged gutter water entering houses", "Gatar saaf kele nahi paani gharat shirat ahe", "drainage"),
    ("Streetlight not working, street is dark", "Pathdive band ahet rastyavar khup andhar ahe", "streetlight"),
    ("Pole light broken near hospital", "Hospital javalche light kharab ahe chori chi bhiti vatate", "streetlight"),
    ("Clean drinking water pipe burst", "Pinycha panyachi pipeline phutli ahe khup paani vaya jat ahe", "water_leakage"),
    ("Tap water is contaminated and brown", "Nalache paani kharab aani gadul yet ahe", "water_leakage"),
    ("Stray dog menace near school", "Shalejaval bhatki kutri khup ahet mulana tras hoto", "other"),
    ("Fallen tree blocking the pathway", "Mothe jhaad padle ahe rasta band jhala ahe", "other"),
]

LANDMARK_LOCATIONS = [
    "near Solapur Railway Station",
    "at Navi Peth Market",
    "near Tuljapur Naka Chowk",
    "around Park Chowk",
    "near Vijapur Road Signal",
    "by Saat Rasta Junction",
    "near Solapur Municipal Corporation Head Office",
    "outside Market Yard Gate 2",
    "near Government Civil Hospital",
    "at Hotgi Road Chowk",
]


def generate_benchmark_dataset():
    with open(INPUT_DATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    pairs = []
    pair_id = 1

    # 1. Exact Duplicates (100 pairs)
    for i in range(100):
        rec = records[i % len(records)]
        base_text = rec["text"]
        # Same issue, slightly different user ref or exact copy
        pairs.append({
            "pair_id": f"EXACT_{pair_id:04d}",
            "type": "exact_duplicate",
            "text_a": base_text,
            "text_b": base_text,
            "category": rec["category"],
            "is_duplicate": True,
            "distance_meters": round(random.uniform(5.0, 50.0), 1),
            "age_diff_hours": round(random.uniform(0.5, 24.0), 1),
            "notes": "Exact duplicate wording from multiple citizen submissions"
        })
        pair_id += 1

    # 2. Semantic Paraphrases (150 pairs)
    for i in range(150):
        category = random.choice(list(PARAPHRASE_TEMPLATES.keys()))
        t_a, t_b = random.choice(PARAPHRASE_TEMPLATES[category])
        loc = random.choice(LANDMARK_LOCATIONS)
        full_a = f"{t_a} {loc}."
        full_b = f"{t_b} {loc}."
        pairs.append({
            "pair_id": f"PARA_{pair_id:04d}",
            "type": "semantic_paraphrase",
            "text_a": full_a,
            "text_b": full_b,
            "category": category,
            "is_duplicate": True,
            "distance_meters": round(random.uniform(10.0, 150.0), 1),
            "age_diff_hours": round(random.uniform(1.0, 48.0), 1),
            "notes": "Same underlying civic issue described using varied synonyms and syntax"
        })
        pair_id += 1

    # 3. Transliterated Marathi / English Pairs (100 pairs)
    for i in range(100):
        t_eng, t_mar, cat = random.choice(TRANSLITERATED_MARATHI_PAIRS)
        loc = random.choice(LANDMARK_LOCATIONS)
        pairs.append({
            "pair_id": f"MAR_{pair_id:04d}",
            "type": "code_mixed_marathi",
            "text_a": f"{t_eng} ({loc}).",
            "text_b": f"{t_mar} ({loc}).",
            "category": cat,
            "is_duplicate": True,
            "distance_meters": round(random.uniform(15.0, 180.0), 1),
            "age_diff_hours": round(random.uniform(2.0, 72.0), 1),
            "notes": "Bilingual/transliterated pair representing identical civic problem"
        })
        pair_id += 1

    # 4. Hard Negative Landmark Distractors (150 pairs)
    # Different complaints sharing the same location/landmark words
    categories = list(PARAPHRASE_TEMPLATES.keys())
    for i in range(150):
        cat_a, cat_b = random.sample(categories, 2)
        t_a = random.choice(PARAPHRASE_TEMPLATES[cat_a])[0]
        t_b = random.choice(PARAPHRASE_TEMPLATES[cat_b])[0]
        loc = random.choice(LANDMARK_LOCATIONS)
        pairs.append({
            "pair_id": f"DISTRACT_{pair_id:04d}",
            "type": "landmark_distractor_negative",
            "text_a": f"{t_a} {loc}.",
            "text_b": f"{t_b} {loc}.",
            "category_a": cat_a,
            "category_b": cat_b,
            "is_duplicate": False,
            "distance_meters": round(random.uniform(20.0, 200.0), 1),
            "age_diff_hours": round(random.uniform(1.0, 96.0), 1),
            "notes": "Different civic problems occurring near the exact same landmark"
        })
        pair_id += 1

    # 5. Random Unrelated Negatives (100 pairs)
    for i in range(100):
        rec_a = random.choice(records)
        rec_b = random.choice(records)
        while rec_a["text"] == rec_b["text"]:
            rec_b = random.choice(records)
        pairs.append({
            "pair_id": f"RANDOM_{pair_id:04d}",
            "type": "random_negative",
            "text_a": rec_a["text"],
            "text_b": rec_b["text"],
            "category_a": rec_a["category"],
            "category_b": rec_b["category"],
            "is_duplicate": False,
            "distance_meters": round(random.uniform(350.0, 5000.0), 1),
            "age_diff_hours": round(random.uniform(24.0, 240.0), 1),
            "notes": "Completely unrelated complaints across distant wards"
        })
        pair_id += 1

    os.makedirs(OUTPUT_PAIRS_PATH.parent, exist_ok=True)
    with open(OUTPUT_PAIRS_PATH, "w", encoding="utf-8") as f:
        json.dump(pairs, f, indent=2, ensure_ascii=False)

    total_pairs = len(pairs)
    positives = sum(1 for p in pairs if p["is_duplicate"])
    negatives = sum(1 for p in pairs if not p["is_duplicate"])

    print(f"============================================================")
    print(f"[+] Generated {total_pairs} Duplicate Benchmark Pairs")
    print(f"[*] Saved to: {OUTPUT_PAIRS_PATH}")
    print(f"------------------------------------------------------------")
    print(f"  - Exact Duplicates:             100 (Positive)")
    print(f"  - Semantic Paraphrases:         150 (Positive)")
    print(f"  - Code-mixed Marathi/English:   100 (Positive)")
    print(f"  - Landmark Distractor Negatives:150 (Negative)")
    print(f"  - Random Dissimilar Negatives:  100 (Negative)")
    print(f"  - Total Positives:              {positives} (58.3%)")
    print(f"  - Total Negatives:              {negatives} (41.7%)")
    print(f"============================================================")


if __name__ == "__main__":
    generate_benchmark_dataset()
