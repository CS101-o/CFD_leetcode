"""
Database initialization script

Run this to create all database tables
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.database import init_db, Base
from app.core.config import settings
from app.models import User, Simulation, Challenge, ChallengeSubmission, ChatMessage

async def main():
    """Initialize database tables"""
    print(f"Initializing database: {settings.DATABASE_URL}")
    print("Creating tables...")

    try:
        await init_db()
        print("✅ Database initialized successfully!")
        print("\nCreated tables:")
        print("  - users")
        print("  - simulations")
        print("  - challenges")
        print("  - challenge_submissions")
        print("  - chat_messages")

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
