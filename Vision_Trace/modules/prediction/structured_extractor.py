import json
import re
import os
import sys
from collections import Counter
from pathlib import Path
from app.paths import RESPONSES_DIR, RESULTS_DIR

class StructuredExtractor:
    def __init__(self, target_id: str, mode: str):
        self.target_id = target_id
        self.mode = mode 
        
        # Architecture-compliant path resolution
        if mode == 'twitter_only':
            self.base_resp = RESPONSES_DIR / f"twitter_only_{target_id}"
            self.base_results = RESULTS_DIR / f"twitter_only_{target_id}"
        else:
            self.base_resp = RESPONSES_DIR / target_id
            self.base_results = RESULTS_DIR / target_id
            
        os.makedirs(self.base_results, exist_ok=True)

    def _rank_and_filter(self, items: list, is_noisy: bool = False) -> list:
        """
        Calculates frequency, removes duplicates, and sorts by priority (highest count first).
        If is_noisy is True, elements that only appear once are permanently removed.
        """
        # Clean whitespace and build a frequency map
        counts = Counter([str(item).strip() for item in items if str(item).strip()])
        ranked_results = []
        
        # .most_common() automatically sorts by frequency descending
        for item, count in counts.most_common():
            # If the data type is prone to false positives (like regex names), drop single occurrences
            if is_noisy and count <= 1:
                continue 
            
            ranked_results.append({
                "value": item,
                "count": count
            })
            
        return ranked_results

    def _pattern_harvest(self, text_list: list) -> dict:
        """Forensic regex scanning for high-signal digital exhaust with frequency weighting."""
        blob = " ".join([str(t) for t in text_list if t])
        
        # --- 1. Names (Proper Noun Heuristic - VERY NOISY) ---
        proper = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', blob)
        
        # --- 2. Addresses (Street Pattern Heuristic) ---
        address_pattern = r'\b\d{1,5}\s+(?:[A-Z][a-z\.]+\s+){1,3}(?:St|Ave|Rd|Blvd|Ln|Dr|Way|Ct|Pl|Terrace|Square|Lane|Road|Avenue|Street|Drive)\.?\b'
        addresses = re.findall(address_pattern, blob)

        # Apply frequency ranking & filtering
        return {
            "identity_signals": {
                # Names are noisy; require count >= 2 to survive the filter
                "likely_names": self._rank_and_filter(proper, is_noisy=True),
                "likely_addresses": self._rank_and_filter(addresses, is_noisy=False),
                "dates_birthdays": self._rank_and_filter(re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', blob), is_noisy=False),
            },
            "contact": {
                "emails": self._rank_and_filter(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', blob), is_noisy=False),
                "phones": self._rank_and_filter(re.findall(r'\+?\d{10,12}', blob), is_noisy=False),
                "handles": self._rank_and_filter(re.findall(r'@\w+', blob), is_noisy=False),
            }
        }

    def run_full_extraction(self):
        print(f"🔬 Raw Aggregation & Frequency Ranking: {self.target_id} ({self.mode} mode)")
        
        # Load identity context
        owner_data = {}
        owner_file = self.base_resp / "owner_detection.json"
        if owner_file.exists():
            with open(owner_file, 'r') as f:
                owner_data = json.load(f)

        master_profile = {
            "metadata": {"target": self.target_id, "mode": self.mode},
            "identity_resolution": owner_data,
            "intelligence_stream": [],
            "deterministic_signals": {}
        }

        all_text_blobs = []

        # 1. Instagram / Hybrid Stream
        if self.mode in ['insta', 'hybrid']:
            vision_path, aws_path = self.base_resp / "vision", self.base_resp / "aws"
            
            if vision_path.exists():
                aws_files = {f.name: f for f in aws_path.glob("*.json")} if aws_path.exists() else {}
                
                for v_file in vision_path.glob("*.json"):
                    # --- GOOGLE VISION (RAW) ---
                    v_raw = {}
                    with open(v_file, 'r') as f:
                        v_raw = json.load(f)
                    
                    # Extract Text for Regex
                    if 'responses' in v_raw:
                        for resp in v_raw['responses']:
                            text_ann = resp.get('textAnnotations', [])
                            if text_ann:
                                all_text_blobs.append(text_ann[0].get('description', ''))

                    # --- AWS REKOGNITION (RAW) ---
                    aws_raw = {}
                    if v_file.name in aws_files:
                        with open(aws_files[v_file.name], 'r') as f:
                            aws_raw = json.load(f)
                            # Extract Text
                            all_text_blobs.extend([t.get('text', '') for t in aws_raw.get('text_clues', [])])
                    
                    # --- SAVE EVERYTHING ---
                    master_profile["intelligence_stream"].append({
                        "file": v_file.name,
                        "vision": v_raw, 
                        "aws": aws_raw   
                    })

        # 2. Twitter Stream
        if self.mode in ['twitter_only', 'hybrid']:
            filename = "twitter_analysis.json" if self.mode == 'hybrid' else "tweet_analysis.json"
            t_path = self.base_resp / filename
            if t_path.exists():
                with open(t_path, 'r') as f:
                    t_nlp = json.load(f)
                    all_text_blobs.append(str(t_nlp))
                    master_profile["twitter_intelligence"] = t_nlp

        # 3. Harvest Patterns
        master_profile["deterministic_signals"] = self._pattern_harvest(all_text_blobs)

        # 4. Save
        save_path = self.base_results / "structured_profile.json"
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(master_profile, f, indent=2, ensure_ascii=False)

        print(f"✅ Frequency-Ranked Profile saved → {save_path}")
        return master_profile

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n❌ Error: No target provided.")
        sys.exit(1)

    target = sys.argv[1]
    
    # Auto-detect Mode
    if (RESPONSES_DIR / f"twitter_only_{target}").exists():
        mode = "twitter_only"
    elif (RESPONSES_DIR / target / "twitter_analysis.json").exists():
        mode = "hybrid"
    else:
        mode = "insta"

    ext = StructuredExtractor(target, mode=mode)
    ext.run_full_extraction()
