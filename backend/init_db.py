"""
Database initialization script
Creates all tables and initializes the database
"""

import asyncio
from app.core.database import engine, Base
from app.models.user import User
from app.models.dealership import Dealership
from app.models.refresh_token import RefreshToken
from app.models.document import Document


async def init_db():
    """Initialize database by creating all tables"""
    print("🔄 Initializing database...")
    
    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False
    finally:
        await engine.dispose()


async def main():
    """Main function"""
    success = await init_db()
    if success:
        print("\n✅ Database initialization complete!")
    else:
        print("\n❌ Database initialization failed!")


if __name__ == "__main__":
    asyncio.run(main())
