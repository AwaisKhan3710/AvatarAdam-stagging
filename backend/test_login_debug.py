"""Debug login endpoint"""

import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000/api/v1"

async def test_login():
    """Test login endpoint"""
    async with httpx.AsyncClient() as client:
        # First, register a user
        print("1. Registering user...")
        signup_payload = {
            "email": "testuser@example.com",
            "password": "TestPass123!",
            "first_name": "Test",
            "last_name": "User",
            "role": "user"
        }
        
        signup_response = await client.post(f"{BASE_URL}/auth/signup", json=signup_payload)
        print(f"   Status: {signup_response.status_code}")
        if signup_response.status_code in [200, 201]:
            signup_data = signup_response.json()
            print(f"   ✅ User registered successfully")
            print(f"   Access Token: {signup_data.get('access_token')[:30]}...")
        else:
            print(f"   ❌ Registration failed: {signup_response.text}")
            return
        
        # Now try to login
        print("\n2. Logging in with same credentials...")
        login_payload = {
            "email": "testuser@example.com",
            "password": "TestPass123!"
        }
        
        login_response = await client.post(f"{BASE_URL}/auth/login", json=login_payload)
        print(f"   Status: {login_response.status_code}")
        print(f"   Response: {login_response.text}")
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            print(f"   ✅ Login successful")
            print(f"   Access Token: {login_data.get('access_token')[:30]}...")
        else:
            print(f"   ❌ Login failed")

if __name__ == "__main__":
    asyncio.run(test_login())
