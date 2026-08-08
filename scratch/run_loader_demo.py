import json
import os
from app.loader import load_curriculum, build_focus_map

def main():
    # Resolve paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    curriculum_path = os.path.join(base_dir, "curriculum.json")
    candidates_path = os.path.join(base_dir, "candidates.json")
    
    print("Loading curriculum...")
    curriculum = load_curriculum(curriculum_path)
    
    print("Loading candidates...")
    with open(candidates_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Pick Sarah Johnson (CAND-001)
    candidate = data["candidates"][0]
    print(f"\n--- Focus Map for Candidate: {candidate['member']['name']} ({candidate['member']['jobRole']}) ---")
    
    focus_map = build_focus_map(candidate, curriculum)
    
    print("\nFOCUS DAYS (Probe Priority):")
    for idx, d in enumerate(focus_map["focus_days"], 1):
        print(f"{idx}. Day {d['day']}: {d['title']} (Module {d['module']})")
        print(f"   Priority: {d['priority'].upper()}")
        print(f"   Reason  : {d['reason']}")
        
    print("\nSTRONG DAYS (Deep Probing):")
    for idx, d in enumerate(focus_map["strong_days"], 1):
        print(f"{idx}. Day {d['day']}: {d['title']} (Module {d['module']})")
        print(f"   Priority: {d['priority'].upper()}")
        print(f"   Reason  : {d['reason']}")

if __name__ == "__main__":
    main()
