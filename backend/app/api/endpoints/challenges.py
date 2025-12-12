"""
CFD LeetCode - Challenge System
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import random

router = APIRouter()

# Challenge Database
CHALLENGES = {
    "beginner_1": {
        "id": "beginner_1",
        "title": "First Flight",
        "difficulty": "Easy",
        "description": "Design an airfoil that generates lift coefficient (CL) of at least 0.5 at 5° angle of attack.",
        "constraints": {
            "alpha": 5.0,
            "reynolds": 1000000,
            "target_cl_min": 0.5,
            "target_cl_max": 0.7
        },
        "hints": [
            "Symmetric airfoils like NACA 0012 have zero lift at 0° but generate lift at positive angles",
            "Try increasing the camber (first digit) to generate more lift",
            "NACA 2412 or NACA 4412 might work well"
        ],
        "points": 100
    },
    "beginner_2": {
        "id": "beginner_2",
        "title": "Efficiency Master",
        "difficulty": "Easy",
        "description": "Design an airfoil with L/D ratio greater than 70 at 5° angle of attack.",
        "constraints": {
            "alpha": 5.0,
            "reynolds": 1000000,
            "target_ld_min": 70
        },
        "hints": [
            "L/D ratio = Lift / Drag. Higher is better!",
            "Thin airfoils tend to have less drag",
            "Try NACA 0012 or NACA 2412"
        ],
        "points": 100
    },
    "intermediate_1": {
        "id": "intermediate_1",
        "title": "High Lift Challenge",
        "difficulty": "Medium",
        "description": "Design an airfoil that generates CL > 1.2 at 10° angle of attack while keeping CD < 0.02.",
        "constraints": {
            "alpha": 10.0,
            "reynolds": 1000000,
            "target_cl_min": 1.2,
            "target_cd_max": 0.02
        },
        "hints": [
            "High camber airfoils generate more lift",
            "But they also create more drag - balance is key",
            "Try NACA 4412 or NACA 6412"
        ],
        "points": 200
    },
    "intermediate_2": {
        "id": "intermediate_2",
        "title": "Sweet Spot Finder",
        "difficulty": "Medium",
        "description": "Find the optimal angle of attack for NACA 2412 that gives the highest L/D ratio.",
        "constraints": {
            "naca": "2412",
            "reynolds": 1000000,
            "target_ld_min": 90
        },
        "hints": [
            "Test different angles between 0° and 15°",
            "L/D ratio typically peaks at low angles (3-7°)",
            "Too high angle causes more drag"
        ],
        "points": 200
    },
    "advanced_1": {
        "id": "advanced_1",
        "title": "The Perfect Balance",
        "difficulty": "Hard",
        "description": "Design an airfoil that achieves CL > 1.0, CD < 0.01, and L/D > 100 simultaneously at any angle between 5-10°.",
        "constraints": {
            "alpha_min": 5.0,
            "alpha_max": 10.0,
            "reynolds": 1000000,
            "target_cl_min": 1.0,
            "target_cd_max": 0.01,
            "target_ld_min": 100
        },
        "hints": [
            "This requires finding both the right airfoil AND the right angle",
            "Moderate camber (2-4%) often works best",
            "Test multiple angles to find the sweet spot"
        ],
        "points": 300
    }
}

class ChallengeResponse(BaseModel):
    challenge: Dict
    message: str

class SubmissionRequest(BaseModel):
    challenge_id: str
    naca_designation: str
    alpha: float
    cl: float
    cd: float
    ld: float

class SubmissionResponse(BaseModel):
    success: bool
    message: str
    points: int
    feedback: str

@router.get("/list")
async def list_challenges():
    """Get all available challenges"""
    return {
        "challenges": [
            {
                "id": c["id"],
                "title": c["title"],
                "difficulty": c["difficulty"],
                "description": c["description"],
                "points": c["points"]
            }
            for c in CHALLENGES.values()
        ]
    }

@router.get("/{challenge_id}")
async def get_challenge(challenge_id: str):
    """Get a specific challenge"""
    if challenge_id not in CHALLENGES:
        raise HTTPException(404, f"Challenge '{challenge_id}' not found")
    
    challenge = CHALLENGES[challenge_id]
    return ChallengeResponse(
        challenge=challenge,
        message=f"Challenge: {challenge['title']} ({challenge['difficulty']})\n\n{challenge['description']}"
    )

@router.post("/submit")
async def submit_solution(submission: SubmissionRequest):
    """Submit a solution to a challenge"""
    if submission.challenge_id not in CHALLENGES:
        raise HTTPException(404, f"Challenge '{submission.challenge_id}' not found")
    
    challenge = CHALLENGES[submission.challenge_id]
    constraints = challenge["constraints"]
    
    # Validate submission
    feedback_parts = []
    success = True
    
    # Check CL
    if "target_cl_min" in constraints:
        if submission.cl < constraints["target_cl_min"]:
            success = False
            feedback_parts.append(f"❌ CL too low: {submission.cl:.4f} < {constraints['target_cl_min']}")
        else:
            feedback_parts.append(f"✅ CL requirement met: {submission.cl:.4f}")
    
    if "target_cl_max" in constraints:
        if submission.cl > constraints["target_cl_max"]:
            success = False
            feedback_parts.append(f"❌ CL too high: {submission.cl:.4f} > {constraints['target_cl_max']}")
    
    # Check CD
    if "target_cd_max" in constraints:
        if submission.cd > constraints["target_cd_max"]:
            success = False
            feedback_parts.append(f"❌ CD too high: {submission.cd:.6f} > {constraints['target_cd_max']}")
        else:
            feedback_parts.append(f"✅ Drag requirement met: {submission.cd:.6f}")
    
    # Check L/D
    if "target_ld_min" in constraints:
        if submission.ld < constraints["target_ld_min"]:
            success = False
            feedback_parts.append(f"❌ L/D too low: {submission.ld:.1f} < {constraints['target_ld_min']}")
        else:
            feedback_parts.append(f"✅ L/D requirement met: {submission.ld:.1f}")
    
    # Check alpha range
    if "alpha" in constraints:
        if abs(submission.alpha - constraints["alpha"]) > 0.1:
            success = False
            feedback_parts.append(f"❌ Must use α = {constraints['alpha']}°")
    
    feedback = "\n".join(feedback_parts)
    
    if success:
        message = f"🎉 Challenge Complete!\n\n{feedback}\n\nYou earned {challenge['points']} points!"
        points = challenge["points"]
    else:
        message = f"Not quite there yet!\n\n{feedback}\n\nKeep trying!"
        points = 0
    
    return SubmissionResponse(
        success=success,
        message=message,
        points=points,
        feedback=feedback
    )

@router.get("/random")
async def get_random_challenge():
    """Get a random challenge"""
    challenge_id = random.choice(list(CHALLENGES.keys()))
    return await get_challenge(challenge_id)