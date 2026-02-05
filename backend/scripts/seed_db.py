"""Database seeding script for initial data."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.schemas.user import UserCreate


async def seed_database() -> None:
    """Seed database with initial data."""
    async with async_session_maker() as db:
        try:
            print("Starting database seeding...")

            # Create test dealership
            from app.models.dealership import Dealership
            from sqlalchemy import select
            
            result = await db.execute(select(Dealership).where(Dealership.name == "Premium Auto Group"))
            dealership = result.scalar_one_or_none()
            
            if not dealership:
                dealership = Dealership(
                    name="Premium Auto Group",
                    address="123 Main St, New York, NY 10001",
                    contact_email="contact@premiumauto.com",
                    contact_phone="(555) 123-4567",
                    rag_config={
                        "vector_db_collection": "dealership_1_knowledge",
                        "embedding_model": "text-embedding-3-small",
                        "chunk_size": 1000,
                        "chunk_overlap": 200,
                        "metadata": {
                            "dealership_id": 1,
                            "dealership_name": "Premium Auto Group",
                            "industry": "automotive"
                        }
                    }
                )
                db.add(dealership)
                await db.flush()
                await db.refresh(dealership)
                print(f"✓ Created dealership: {dealership.name}")
            else:
                print(f"- Dealership already exists: {dealership.name}")

            # Create super admin user
            admin_data = UserCreate(
                email="admin@avataradam.com",
                password="Admin123!@#",  # Change this in production!
                first_name="Super",
                last_name="Admin",
                role=UserRole.SUPER_ADMIN,
                dealership_id=None,
            )

            result = await db.execute(select(User).where(User.email == admin_data.email))
            existing_admin = result.scalar_one_or_none()
            if not existing_admin:
                admin = User(
                    email=admin_data.email,
                    hashed_password=get_password_hash(admin_data.password),
                    first_name=admin_data.first_name,
                    last_name=admin_data.last_name,
                    role=admin_data.role,
                    dealership_id=admin_data.dealership_id,
                )
                db.add(admin)
                await db.flush()
                print(f"✓ Created super admin: {admin.email}")
                print(f"  Password: Admin123!@# (CHANGE THIS!)")
            else:
                print(f"- Super admin already exists: {admin_data.email}")

            # Create dealership admin
            dealership_admin_data = UserCreate(
                email="admin@premiumauto.com",
                password="Admin123!",
                first_name="Dealership",
                last_name="Admin",
                role=UserRole.DEALERSHIP_ADMIN,
                dealership_id=dealership.id,
            )

            result = await db.execute(select(User).where(User.email == dealership_admin_data.email))
            existing_d_admin = result.scalar_one_or_none()
            if not existing_d_admin:
                d_admin = User(
                    email=dealership_admin_data.email,
                    hashed_password=get_password_hash(dealership_admin_data.password),
                    first_name=dealership_admin_data.first_name,
                    last_name=dealership_admin_data.last_name,
                    role=dealership_admin_data.role,
                    dealership_id=dealership_admin_data.dealership_id,
                )
                db.add(d_admin)
                await db.flush()
                print(f"✓ Created dealership admin: {d_admin.email}")
                print(f"  Password: Admin123!")
            else:
                print(f"- Dealership admin already exists: {dealership_admin_data.email}")

            # Create test user
            user_data = UserCreate(
                email="user@premiumauto.com",
                password="User123!",
                first_name="Test",
                last_name="User",
                role=UserRole.USER,
                dealership_id=dealership.id,
            )

            result = await db.execute(select(User).where(User.email == user_data.email))
            existing_user = result.scalar_one_or_none()
            if not existing_user:
                user = User(
                    email=user_data.email,
                    hashed_password=get_password_hash(user_data.password),
                    first_name=user_data.first_name,
                    last_name=user_data.last_name,
                    role=user_data.role,
                    dealership_id=user_data.dealership_id,
                )
                db.add(user)
                await db.flush()
                print(f"✓ Created test user: {user.email}")
                print(f"  Password: User123!")
            else:
                print(f"- Test user already exists: {user_data.email}")

            # Commit all changes
            await db.commit()
            print("\n✓ Database seeding completed successfully!")

            # Print summary
            print("\n" + "=" * 60)
            print("SEED DATA SUMMARY")
            print("=" * 60)
            print("\nDealership:")
            print(f"  {dealership.name} (ID: {dealership.id})")
            print("\nUsers:")
            print(f"  Super Admin: admin@avataradam.com / Admin123!@#")
            print(f"  Dealership Admin: admin@premiumauto.com / Admin123!")
            print(f"  User: user@premiumauto.com / User123!")
            print("\n⚠️  IMPORTANT: Change all passwords in production!")
            print("=" * 60)

        except Exception as e:
            print(f"\n✗ Error during seeding: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    print("Avatar Adam - Database Seeding Script")
    print("=" * 60)
    asyncio.run(seed_database())
