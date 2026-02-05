"""
Simple test to verify project setup and basic functionality
"""

import subprocess
import sys
import time
import requests
import json

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def test_imports():
    """Test if all required packages can be imported"""
    print_header("TEST 1: Checking Package Imports")
    
    packages = [
        ("fastapi", "FastAPI"),
        ("sqlalchemy", "SQLAlchemy"),
        ("pydantic", "Pydantic"),
        ("langchain", "LangChain"),
        ("pinecone", "Pinecone"),
        ("openai", "OpenAI"),
        ("httpx", "HTTPX"),
        ("pytest", "Pytest"),
    ]
    
    passed = 0
    failed = 0
    
    for module, name in packages:
        try:
            __import__(module)
            print(f"  ✓ {name:20} - OK")
            passed += 1
        except ImportError as e:
            print(f"  ✗ {name:20} - FAILED: {e}")
            failed += 1
    
    print(f"\n  Result: {passed} passed, {failed} failed")
    return failed == 0

def test_env_file():
    """Test if .env file exists and has required variables"""
    print_header("TEST 2: Checking Environment Configuration")
    
    try:
        with open(".env", "r") as f:
            content = f.read()
        
        required_vars = [
            "DATABASE_URL",
            "SECRET_KEY",
            "PROJECT_NAME",
            "DEBUG",
        ]
        
        passed = 0
        failed = 0
        
        for var in required_vars:
            if var in content:
                print(f"  ✓ {var:30} - Found")
                passed += 1
            else:
                print(f"  ✗ {var:30} - Missing")
                failed += 1
        
        print(f"\n  Result: {passed} passed, {failed} failed")
        return failed == 0
    except FileNotFoundError:
        print("  ✗ .env file not found")
        return False

def test_app_structure():
    """Test if app structure is correct"""
    print_header("TEST 3: Checking Project Structure")
    
    import os
    
    required_dirs = [
        "app",
        "app/api",
        "app/api/v1",
        "app/core",
        "app/models",
        "app/schemas",
        "app/services",
        "alembic",
        "scripts",
    ]
    
    passed = 0
    failed = 0
    
    for dir_path in required_dirs:
        if os.path.isdir(dir_path):
            print(f"  ✓ {dir_path:40} - OK")
            passed += 1
        else:
            print(f"  ✗ {dir_path:40} - Missing")
            failed += 1
    
    print(f"\n  Result: {passed} passed, {failed} failed")
    return failed == 0

def test_database_config():
    """Test database configuration"""
    print_header("TEST 4: Checking Database Configuration")
    
    try:
        from app.core.config import settings
        
        print(f"  Database URL: {settings.DATABASE_URL[:50]}...")
        print(f"  Debug Mode: {settings.DEBUG}")
        print(f"  Project Name: {settings.PROJECT_NAME}")
        print(f"  API Version: {settings.VERSION}")
        print(f"  Pool Size: {settings.DB_POOL_SIZE}")
        print(f"  Max Overflow: {settings.DB_MAX_OVERFLOW}")
        
        print("\n  ✓ Configuration loaded successfully")
        return True
    except Exception as e:
        print(f"  ✗ Failed to load configuration: {e}")
        return False

def test_api_import():
    """Test if API can be imported"""
    print_header("TEST 5: Checking API Import")
    
    try:
        from app.main import app
        print(f"  ✓ FastAPI app imported successfully")
        print(f"  ✓ App title: {app.title}")
        print(f"  ✓ App version: {app.version}")
        
        # Count routes
        routes = len(app.routes)
        print(f"  ✓ Total routes: {routes}")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed to import app: {e}")
        return False

def test_models():
    """Test if models can be imported"""
    print_header("TEST 6: Checking Database Models")
    
    try:
        from app.models.user import User
        from app.models.dealership import Dealership
        from app.models.refresh_token import RefreshToken
        
        print(f"  ✓ User model imported")
        print(f"  ✓ Dealership model imported")
        print(f"  ✓ RefreshToken model imported")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed to import models: {e}")
        return False

def test_schemas():
    """Test if schemas can be imported"""
    print_header("TEST 7: Checking Pydantic Schemas")
    
    try:
        from app.schemas.auth import LoginRequest, TokenResponse
        from app.schemas.user import UserCreate, UserResponse
        
        print(f"  ✓ Auth schemas imported")
        print(f"  ✓ User schemas imported")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed to import schemas: {e}")
        return False

def test_services():
    """Test if services can be imported"""
    print_header("TEST 8: Checking Services")
    
    try:
        from app.services.llm_service import LLMService
        from app.services.rag_service import RAGService
        from app.services.voice_service import VoiceService
        
        print(f"  ✓ LLM service imported")
        print(f"  ✓ RAG service imported")
        print(f"  ✓ Voice service imported")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed to import services: {e}")
        return False

def test_security():
    """Test security utilities"""
    print_header("TEST 9: Checking Security Utilities")
    
    try:
        from app.core.security import (
            create_access_token,
            create_refresh_token,
            verify_password,
            get_password_hash,
        )
        
        # Test password hashing
        password = "TestPassword123!@#"
        hashed = get_password_hash(password)
        verified = verify_password(password, hashed)
        
        if verified:
            print(f"  ✓ Password hashing working")
        else:
            print(f"  ✗ Password verification failed")
            return False
        
        # Test token creation
        token = create_access_token(subject="test_user")
        if token:
            print(f"  ✓ Access token creation working")
        else:
            print(f"  ✗ Token creation failed")
            return False
        
        return True
    except Exception as e:
        print(f"  ✗ Security test failed: {e}")
        return False

def test_api_endpoints():
    """Test if API endpoints are accessible"""
    print_header("TEST 10: Testing API Endpoints")
    
    try:
        # Wait for server to be ready
        max_retries = 10
        for i in range(max_retries):
            try:
                response = requests.get("http://127.0.0.1:8000/", timeout=2)
                if response.status_code == 200:
                    break
            except:
                if i < max_retries - 1:
                    time.sleep(1)
                else:
                    raise
        
        # Test root endpoint
        response = requests.get("http://127.0.0.1:8000/")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Root endpoint: {data.get('message')}")
        else:
            print(f"  ✗ Root endpoint failed: {response.status_code}")
            return False
        
        # Test health endpoint
        response = requests.get("http://127.0.0.1:8000/health")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Health endpoint: {data.get('status')}")
        else:
            print(f"  ✗ Health endpoint failed: {response.status_code}")
            return False
        
        # Test docs endpoint
        response = requests.get("http://127.0.0.1:8000/docs")
        if response.status_code == 200:
            print(f"  ✓ Swagger UI available")
        else:
            print(f"  ✗ Swagger UI failed: {response.status_code}")
            return False
        
        return True
    except Exception as e:
        print(f"  ✗ API endpoint test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "AVATAR ADAM - PROJECT TESTING SUITE" + " "*19 + "║")
    print("╚" + "="*68 + "╝")
    
    tests = [
        ("Package Imports", test_imports),
        ("Environment File", test_env_file),
        ("Project Structure", test_app_structure),
        ("Database Config", test_database_config),
        ("API Import", test_api_import),
        ("Database Models", test_models),
        ("Pydantic Schemas", test_schemas),
        ("Services", test_services),
        ("Security", test_security),
        ("API Endpoints", test_api_endpoints),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n  ✗ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    failed = sum(1 for _, result in results if not result)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status:8} - {test_name}")
    
    print(f"\n  Total: {passed} passed, {failed} failed out of {len(results)} tests")
    print(f"  Success Rate: {(passed/len(results)*100):.1f}%")
    
    if failed == 0:
        print("\n  ✓ ALL TESTS PASSED - PROJECT IS READY!")
    else:
        print(f"\n  ✗ {failed} test(s) failed - Please review the errors above")
    
    print("\n" + "="*70 + "\n")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
