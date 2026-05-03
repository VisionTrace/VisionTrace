import json
import os
import sys
from pathlib import Path
from google import genai
from google.genai import types
from app.paths import RESPONSES_DIR, RESULTS_DIR, CONFIG_DIR
from dotenv import load_dotenv

# Load environment variables
load_dotenv(CONFIG_DIR / "env")

class ProfileEngine:
    def __init__(self, target_id: str, mode: str):
        self.target_id = target_id
        self.mode = mode
        
        # Define Input/Output Paths
        if mode == 'twitter_only':
            self.input_dir = RESPONSES_DIR / f"twitter_only_{target_id}"
            self.results_path = RESULTS_DIR / f"twitter_only_{target_id}"
        else:
            self.input_dir = RESPONSES_DIR / target_id
            self.results_path = RESULTS_DIR / target_id
            
        os.makedirs(self.results_path, exist_ok=True)
        
        # AI Configuration
        self.models = ["gemini-2.5-pro", "gemini-1.5-pro", "gemini-2.0-flash"] 
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def _load_clean_evidence(self):
        """
        INGESTION ENGINE:
        Loads the pre-processed structured profile to grab high-frequency verified names
        and constructs a clean, flattened text context to avoid JSON hallucinations.
        """
        structured_file = self.results_path / "structured_profile.json"
        
        if not structured_file.exists():
            raise FileNotFoundError(f"Missing {structured_file}. Run structured_extractor.py first.")
            
        with open(structured_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"📂 Loaded structured evidence from: {structured_file}")
        
        clean_text_blocks = []
        
        # Flatten vision/aws text
        for stream in data.get("intelligence_stream", []):
            vision = stream.get("vision", {})
            if "responses" in vision:
                for resp in vision["responses"]:
                    text_ann = resp.get("textAnnotations", [])
                    if text_ann:
                        clean_text_blocks.append(text_ann[0].get("description", ""))
                        break # First index is the full text blob
            
            aws = stream.get("aws", {})
            for text_clue in aws.get("text_clues", []):
                clean_text_blocks.append(text_clue.get("text", ""))

        # Add Twitter
        if "twitter_intelligence" in data:
            clean_text_blocks.append(str(data["twitter_intelligence"]))
            
        # Extract the verified names from the new frequency-ranked dictionary format
        likely_names_data = data.get("deterministic_signals", {}).get("identity_signals", {}).get("likely_names", [])
        
        verified_names = []
        for item in likely_names_data:
            if isinstance(item, dict) and "value" in item:
                verified_names.append(item["value"])
            elif isinstance(item, str):
                # Fallback just in case old data is present
                verified_names.append(item)

        return "\n---\n".join(clean_text_blocks)[:120000], verified_names

    def _verify_ground_truth(self, generated_matrix, verified_names):
        """
        TRUTH VERIFICATION LAYER:
        Ensures names strictly match the high-frequency proper nouns.
        """
        valid_entries = []
        verified_names_lower = [name.lower() for name in verified_names]
        
        print(f"\n🕵️  Verifying {len(generated_matrix)} detected users against high-priority signals...")
        
        for person in generated_matrix:
            name = person.get("name", "").strip()
            if not name or name.lower() == self.target_id.lower():
                continue
                
            # Strict Check: Name must exist in our regex-harvested proper noun list
            name_parts = name.lower().split()
            # Check if any part of the generated name matches our verified high-frequency proper nouns
            if any(part in v_name for part in name_parts for v_name in verified_names_lower):
                valid_entries.append(person)
            else:
                print(f"  🚫 Removed Hallucination/Low-Confidence: '{name}'")
                
        print(f"  ✅ Confirmed {len(valid_entries)} real, high-priority relationships.")
        return valid_entries

    def generate_report(self):
        # --- STEP 1: LOAD CLEAN CONTEXT ---
        full_context, verified_names = self._load_clean_evidence()
        
        # --- STEP 2: PASS 1 - TEXT REPORT ---
        report_prompt = f"""
        ACT AS: Senior OSINT & Cybersecurity Forensics Analyst.
        TARGET USER: {self.target_id}
        INPUT DATA: Extracted text from images and social media posts.
        DATA CONTEXT: {full_context}
        
        *** MISSION: GENERATE DIGITAL FOOTPRINT VULNERABILITY REPORT ***
        Analyze the text data to construct a detailed threat assessment.
        
        *** FORMAT REQUIREMENTS (STRICT MARKDOWN) ***
        **TO:** {self.target_id}
        **FROM:** OSINT & Cybersecurity Forensics Division
        **SUBJECT:** Digital Footprint Vulnerability Report
        
        **EXECUTIVE SUMMARY:**
        [Brief summary of findings and high-level threat assessment.]
        
        ---
        
        ### **TASK 1: DIGITAL FOOTPRINT VULNERABILITY REPORT**
        
        #### **1. THE STALKER'S NARRATIVE (Reconstructed Routine)**
        * **Methodology:** Predict routines based on location data.
        * **Hypothetical Routine for {self.target_id}:**
            * **Weekdays:** [Infer work/study].
            * **Evenings/Weekends:** [Infer hobbies/hangouts].
        
        #### **2. SENSITIVE INFORMATION LEAKS**
        * **License Plates/IDs:** [List specifics].
        * **Home/Location:** [Specific landmarks/cities].
        * **Personal Data:** [Birthdays, full names, numbers].
        
        #### **3. SOCIAL ENGINEERING (Phishing Hooks)**
        * **Hobbies & Interests:** [Specific interests].
        * **Connections:** [Friends who could be impersonated].
        
        #### **4. PHYSICAL ASSET LOG**
        * **Vehicles:** [Make/Model].
        * **Electronics:** [Devices seen].
        
        ---
        
        ### **TASK 2: SOCIAL NETWORK RECONSTRUCTION**
        
        ## 🤝 ASSOCIATES & CONNECTIONS
        Detail the connections between the target and all identified users. Create a Markdown Table detailing:
        * **Name/Handle:** [Identified User]
        * **Relationship:** [e.g., Partner, Best Friend, Family, Associate]
        * **Evidence:** [Quote the specific comment, tag, or context connecting them to the target]
        
        ## 📅 TIMELINE & LOCATION
        * **[Date]:** [Event Description] ([Location])
        * Sort chronological (Newest to Oldest).
        """

        # --- STEP 3: PASS 2 - JSON MATRIX ---
        matrix_prompt = f"""
        Extract a list of relationships from the following text data for the target user {self.target_id}.
        Return ONLY a JSON array of objects.
        
        Rules for Roles:
        - "Partner": "love", "hubby", "wifey", ❤️, 💍.
        - "Best Friend": "bestie", "main", "day 1".
        - "Family": "bro", "sis", "mom".
        - "Associate": Neutral interactions.
        
        DATA CONTEXT:
        {full_context}
        """

        used_model = None
        report_text = None
        matrix_data = []

        # Common configuration for zero hallucinations
        safety_config = types.GenerateContentConfig(
            temperature=0.0, 
            top_p=0.8
        )
        
        json_config = types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json" 
        )

        for model_name in self.models:
            try:
                print(f"🤖 Generating Text Report with {model_name}...")
                report_resp = self.client.models.generate_content(
                    model=model_name, 
                    contents=report_prompt, 
                    config=safety_config
                )
                report_text = report_resp.text
                
                print(f"🤖 Extracting JSON Matrix with {model_name}...")
                matrix_resp = self.client.models.generate_content(
                    model=model_name, 
                    contents=matrix_prompt, 
                    config=json_config
                )
                matrix_data = json.loads(matrix_resp.text)
                
                used_model = model_name
                break # Success, break out of fallback loop
            except Exception as e:
                print(f"⚠️ {model_name} failed: {e}")

        if not report_text:
            raise RuntimeError("❌ Intelligence synthesis failed.")

        # --- STEP 4: VERIFY & SAVE ---
        # Verify JSON Matrix
        clean_matrix = self._verify_ground_truth(matrix_data, verified_names)
        
        matrix_path = self.results_path / "relationship_matrix.json"
        with open(matrix_path, "w", encoding="utf-8") as f:
            json.dump(clean_matrix, f, indent=2)
        print(f"✅ RELATIONSHIP MATRIX SAVED → {matrix_path}")

        # Save Text Report
        report_path = self.results_path / "final_report.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_text)
            
        print(f"✅ REPORT GENERATED ({used_model}) → {report_path}")
        return report_text

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n❌ Error: No target provided.")
        sys.exit(1)

    target = sys.argv[1]
    
    # Auto-detect mode
    mode = "twitter_only" if (RESPONSES_DIR / f"twitter_only_{target}").exists() else "insta"
    
    engine = ProfileEngine(target, mode=mode)
    engine.generate_report()
