import json
import os
from typing import Dict, List, Any

def load_curriculum(filepath: str) -> Dict[int, Dict[str, Any]]:
    """
    Loads curriculum.json and indexes days 1 to 31.
    Each day is mapped to its details and module information.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Curriculum file not found at: {filepath}")
        
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Map day numbers to module info
    day_to_module = {}
    for mod in data.get("modules", []):
        start_day, end_day = mod.get("days", [0, 0])
        for d in range(start_day, end_day + 1):
            day_to_module[d] = {
                "module_num": mod.get("n"),
                "module_title": mod.get("title")
            }
            
    # Index days by day number
    indexed_days = {}
    for day_data in data.get("days", []):
        day_num = day_data.get("day")
        if not day_num:
            continue
            
        mod_info = day_to_module.get(day_num, {"module_num": None, "module_title": None})
        indexed_days[day_num] = {
            "day": day_num,
            "title": day_data.get("title", ""),
            "type": day_data.get("type", ""),
            "tools": day_data.get("tools", []),
            "objectives": day_data.get("objectives", []),
            "module_num": mod_info["module_num"],
            "module_title": mod_info["module_title"]
        }
        
    return indexed_days

def build_focus_map(candidate: Dict[str, Any], curriculum: Dict[int, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Analyzes the candidate's learning history against the curriculum to build:
    1. An ordered list of focus (high-risk) days to probe.
    2. A separate list of strong days to test deep understanding.
    
    Guarantees that focus_days contains at least 4 days covering at least 3 modules if possible.
    """
    missions = candidate.get("missions", [])
    
    scored_days = []
    for day_num, day_info in curriculum.items():
        # Find matching mission
        mission = next((m for m in missions if m.get("day") == day_num), None)
        
        status = "implicit_pass"
        risk_score = 1
        strength_score = 5
        reason = "No cohort progress recorded for this day."
        priority = "low"
        
        if mission is not None:
            if mission.get("skipped") is True:
                status = "skipped"
                risk_score = 1
                strength_score = 0
                reason = "Candidate skipped this mission."
                priority = "high"
            elif mission.get("passed") is False:
                status = "failed"
                risk_score = 1
                strength_score = 0
                attempts = mission.get("attempts", 1)
                reason = f"Candidate failed this mission after {attempts} attempt(s)."
                priority = "high"
            else:
                # Mission was passed, check attempts count
                attempts = mission.get("attempts", 1)
                if attempts >= 3:
                    status = "struggled"
                    risk_score = 10
                    strength_score = 2
                    reason = f"Passed, but struggled (required {attempts} attempts)."
                    priority = "high"
                elif attempts == 2:
                    status = "struggled_slightly"
                    risk_score = 8
                    strength_score = 4
                    reason = "Passed on the second attempt."
                    priority = "medium"
                else:
                    status = "passed_first_try"
                    risk_score = 6
                    strength_score = 8
                    reason = "Passed on the first attempt."
                    priority = "low"
                    
        scored_days.append({
            "day": day_num,
            "title": day_info["title"],
            "module_num": day_info["module_num"],
            "module_title": day_info["module_title"],
            "status": status,
            "risk_score": risk_score,
            "strength_score": strength_score,
            "reason": reason,
            "priority": priority
        })
        
    # --- Focus Days Selection Strategy (Min 4 days, Min 3 modules) ---
    
    # 1. Group scored days by module
    module_groups: Dict[int, List[Dict[str, Any]]] = {}
    for sd in scored_days:
        m_num = sd["module_num"]
        if m_num not in module_groups:
            module_groups[m_num] = []
        module_groups[m_num].append(sd)
        
    # 2. Find the highest risk day in each module
    module_representatives = []
    for m_num, days in module_groups.items():
        # Sort days in module by risk desc, then day asc
        sorted_m_days = sorted(days, key=lambda x: (-x["risk_score"], x["day"]))
        module_representatives.append(sorted_m_days[0])
        
    # 3. Sort module representatives by risk desc
    module_representatives = sorted(module_representatives, key=lambda x: (-x["risk_score"], x["day"]))
    
    # 4. Pick representatives from top 3 modules
    selected_focus_days = []
    selected_modules = set()
    
    # Take first 3 representatives (covering up to 3 modules)
    for rep in module_representatives[:3]:
        selected_focus_days.append(rep)
        selected_modules.add(rep["module_num"])
        
    # 5. Fill remaining slots to get to at least 4 focus days using overall sorted risk
    all_sorted_by_risk = sorted(scored_days, key=lambda x: (-x["risk_score"], x["day"]))
    for sd in all_sorted_by_risk:
        if len(selected_focus_days) >= 4:
            break
        # Skip if already selected
        if any(f["day"] == sd["day"] for f in selected_focus_days):
            continue
        selected_focus_days.append(sd)
        selected_modules.add(sd["module_num"])
        
    # Final sort of focus days: highest risk first
    selected_focus_days = sorted(selected_focus_days, key=lambda x: (-x["risk_score"], x["day"]))
    
    # --- Strong Days Selection Strategy (High strength, Low risk) ---
    # Filter out days already selected as focus days
    strong_candidates = [
        sd for sd in scored_days
        if not any(f["day"] == sd["day"] for f in selected_focus_days)
    ]
    # Sort by strength desc, risk asc, day asc
    sorted_strong = sorted(strong_candidates, key=lambda x: (-x["strength_score"], x["risk_score"], x["day"]))
    
    # Select top 4 strong days
    selected_strong_days = sorted_strong[:4]
    
    # Clean up output format (removing internal score variables)
    def clean_output(days_list):
        return [
            {
                "day": d["day"],
                "title": d["title"],
                "module": d["module_num"],
                "reason": d["reason"],
                "priority": d["priority"]
            }
            for d in days_list
        ]
        
    return {
        "focus_days": clean_output(selected_focus_days),
        "strong_days": clean_output(selected_strong_days)
    }
