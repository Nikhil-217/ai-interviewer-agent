import json
import os
from app.loader import load_curriculum, build_focus_map
from app.main import get_system_prompt

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    curriculum_path = os.path.join(base_dir, "curriculum.json")
    candidates_path = os.path.join(base_dir, "candidates.json")
    
    curriculum = load_curriculum(curriculum_path)
    with open(candidates_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    candidates = data["candidates"]
    
    # 1. Sarah Johnson (CAND-001) - Struggling / Skipped focus
    sarah = next(c for c in candidates if c["member"]["id"] == "CAND-001")
    sarah_focus = build_focus_map(sarah, curriculum)
    sarah_day = sarah_focus["focus_days"][0]  # Day 29 (Skipped)
    
    print("======================================================================")
    print(f"CANDIDATE 1: {sarah['member']['name']} ({sarah['member']['jobRole']})")
    print(f"Focus Day: Day {sarah_day['day']} - {sarah_day['title']}")
    print(f"Reason   : {sarah_day['reason']}")
    print(f"Priority : {sarah_day['priority'].upper()}")
    print("----------------------------------------------------------------------")
    print("GENERATED SYSTEM PROMPT:")
    print(get_system_prompt(sarah_day, sarah))
    print("======================================================================\n")
    
    # 2. Emily Chen (CAND-003) - Master candidate (Passed first-try focus)
    emily = next(c for c in candidates if c["member"]["id"] == "CAND-003")
    emily_focus = build_focus_map(emily, curriculum)
    emily_day = emily_focus["focus_days"][0]  # Day 7 (Passed first try)
    
    print("======================================================================")
    print(f"CANDIDATE 2: {emily['member']['name']} ({emily['member']['jobRole']})")
    print(f"Focus Day: Day {emily_day['day']} - {emily_day['title']}")
    print(f"Reason   : {emily_day['reason']}")
    print(f"Priority : {emily_day['priority'].upper()}")
    print("----------------------------------------------------------------------")
    print("GENERATED SYSTEM PROMPT:")
    print(get_system_prompt(emily_day, emily))
    print("======================================================================")

if __name__ == "__main__":
    main()
