"""
Seed database with challenge definitions from JSON files
"""

import asyncio
import json
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.database import async_session_maker
from app.models import Challenge, DifficultyLevel, ChallengeCategory


async def load_challenges_from_json(challenges_dir: Path) -> list:
    """Load challenge definitions from JSON files"""
    challenges = []

    # Iterate through difficulty directories
    for difficulty_dir in ["easy", "medium", "hard"]:
        dir_path = challenges_dir / difficulty_dir
        if not dir_path.exists():
            print(f"⚠️  Directory not found: {dir_path}")
            continue

        # Load each JSON file
        for json_file in dir_path.glob("*.json"):
            print(f"Loading {json_file.name}...")
            with open(json_file, 'r') as f:
                challenge_data = json.load(f)
                challenges.append(challenge_data)

    return challenges


async def seed_challenges(session: AsyncSession, challenges: list):
    """Insert challenges into database"""
    for challenge_data in challenges:
        # Create Challenge object
        challenge = Challenge(
            title=challenge_data["title"],
            slug=challenge_data["slug"],
            description=challenge_data["description"],
            difficulty=DifficultyLevel(challenge_data["difficulty"]),
            category=ChallengeCategory(challenge_data["category"]),
            constraints=challenge_data["constraints"],
            validation_criteria=challenge_data["validation_criteria"],
            hints=challenge_data.get("hints", []),
            learning_objectives=challenge_data.get("learning_objectives", []),
            reference_solution=challenge_data.get("reference_solution"),
            points=challenge_data.get("points", 100),
            order=challenge_data.get("order", 0),
            is_active=True
        )

        session.add(challenge)
        print(f"  ✅ Added: {challenge.title}")

    await session.commit()


async def main():
    """Main seeding function"""
    print("🌱 Seeding challenges from JSON files...")

    # Find challenges directory
    challenges_dir = Path(__file__).parent.parent.parent.parent / "shared" / "challenges"

    if not challenges_dir.exists():
        print(f"❌ Challenges directory not found: {challenges_dir}")
        print("   Please ensure shared/challenges/ exists with JSON files")
        sys.exit(1)

    print(f"📂 Loading from: {challenges_dir}\n")

    # Load challenge definitions
    challenges = await load_challenges_from_json(challenges_dir)
    print(f"\n📊 Found {len(challenges)} challenges\n")

    if not challenges:
        print("❌ No challenges found!")
        sys.exit(1)

    # Insert into database
    async with async_session_maker() as session:
        try:
            await seed_challenges(session, challenges)
            print(f"\n✅ Successfully seeded {len(challenges)} challenges!")

        except Exception as e:
            print(f"\n❌ Error seeding challenges: {e}")
            await session.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
