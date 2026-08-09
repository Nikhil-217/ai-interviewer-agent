import json
import os
import pytest
from app.loader import load_curriculum, build_focus_map

@pytest.fixture
def curriculum():
    path = os.path.join(os.path.dirname(__file__), "..", "curriculum.json")
    return load_curriculum(path)

@pytest.fixture
def sample_candidates():
    path = os.path.join(os.path.dirname(__file__), "..", "candidates.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["candidates"]

def test_load_curriculum(curriculum):
    # Verify we loaded all 31 days
    assert len(curriculum) == 31
    
    # Check a specific day (Day 7: Embeddings Explained, which should be in Module 3)
    day7 = curriculum[7]
    assert day7["day"] == 7
    assert "Embeddings" in day7["title"]
    assert day7["module_num"] == 3
    assert day7["module_title"] == "Embeddings & Vector Search"
    
    # Check all days have valid module mapping
    for d_num, info in curriculum.items():
        assert info["module_num"] is not None
        assert info["module_num"] in range(1, 9)
        assert info["module_title"] != ""

def test_build_focus_map_constraints(sample_candidates, curriculum):
    for candidate in sample_candidates:
        focus_map = build_focus_map(candidate, curriculum)
        
        focus_days = focus_map["focus_days"]
        strong_days = focus_map["strong_days"]
        
        # Requirement: At least 4 distinct days selected
        assert len(focus_days) >= 4
        
        # Requirement: Cover at least 3 different modules (if candidate has activity across them)
        modules_covered = {d["module"] for d in focus_days}
        assert len(modules_covered) >= 3
        
        # Ensure no overlap between focus_days and strong_days
        focus_day_nums = {d["day"] for d in focus_days}
        strong_day_nums = {d["day"] for d in strong_days}
        assert focus_day_nums.isdisjoint(strong_day_nums)
        
        # Check priority levels are mapped correctly
        for d in focus_days:
            assert d["priority"] in ["high", "medium", "low"]

def test_build_focus_map_scoring_rules(curriculum):
    # Construct a mock candidate with specific mission outcomes to test scoring logic
    mock_candidate = {
        "member": {
            "id": "CAND-MOCK",
            "name": "Mock Candidate",
            "jobRole": "Software Engineer",
            "yearsExperience": 3,
            "education": "BS",
            "status": "IN_PROGRESS"
        },
        "missions": [
            { "day": 1, "title": "VS Code Setup", "skipped": True },
            { "day": 2, "title": "Ollama Setup", "passed": False, "attempts": 2 },
            { "day": 3, "title": "React Frontend", "passed": True, "attempts": 4 },
            { "day": 4, "title": "Python Basics", "passed": True, "attempts": 2 },
            { "day": 5, "title": "SQL Basics", "passed": True, "attempts": 1 }
        ],
        "signals": {
            "commitDays": 5,
            "missionsCompleted": 4,
            "missionsFirstTry": 1
        }
    }
    
    focus_map = build_focus_map(mock_candidate, curriculum)
    focus_days = focus_map["focus_days"]
    
    # Let's check that Day 3 (struggled with 4 attempts), Day 4 (struggled slightly), and Day 5 (passed first try) are in focus_days
    focus_day_nums = [d["day"] for d in focus_days]
    
    assert 3 in focus_day_nums  # Passed with 4 attempts (Highest risk = 10)
    assert 4 in focus_day_nums  # Passed with 2 attempts (Risk = 8)
    assert 5 in focus_day_nums  # Passed with 1 attempt (Risk = 6)
    
    # Check sorting order of focus days: Day 3 should be first, Day 4 second, Day 5 third
    assert focus_days[0]["day"] == 3
    assert focus_days[1]["day"] == 4
    assert focus_days[2]["day"] == 5
    
    # Check reasons match the status
    assert "struggled" in focus_days[0]["reason"].lower()
    assert "second attempt" in focus_days[1]["reason"].lower()
    assert "first attempt" in focus_days[2]["reason"].lower()
