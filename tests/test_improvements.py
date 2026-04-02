#!/usr/bin/env python
"""Test script to validate the 3 improvements."""

import json
import requests
from pydantic import ValidationError
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.auth import UserRegisterRequest
from app.schemas.cv import PaginationParams

BASE_URL = "http://127.0.0.1:8000"

def test_email_validation():
    """Test 1: Email validation with EmailStr."""
    print("\n📧 TEST 1: Email Validation")
    print("-" * 50)
    
    # Valid email
    try:
        req = UserRegisterRequest(email="user@example.com", password="ValidPass123")
        print("✅ Valid email accepted: user@example.com")
    except ValidationError as e:
        print(f"❌ Valid email rejected: {e}")
        return False
    
    # Invalid email formats
    invalid_emails = [
        ("notanemail", "Missing @"),
        ("@example.com", "Missing local part"),
        ("user@", "Missing domain"),
        ("user@.com", "Missing domain name"),
    ]
    
    for email, reason in invalid_emails:
        try:
            UserRegisterRequest(email=email, password="ValidPass123")
            print(f"❌ Invalid email accepted: {email} ({reason})")
            return False
        except ValidationError:
            print(f"✅ Invalid email rejected: {email} ({reason})")
    
    return True

def test_password_validation():
    """Test 2: Password strength validation."""
    print("\n🔐 TEST 2: Password Strength Validation")
    print("-" * 50)
    
    # Valid password
    try:
        req = UserRegisterRequest(email="user@example.com", password="ValidPass123")
        print("✅ Valid password accepted: ValidPass123 (has upper, lower, digit)")
    except ValidationError as e:
        print(f"❌ Valid password rejected: {e}")
        return False
    
    # Invalid passwords
    invalid_passwords = [
        ("pass123", "No uppercase letter"),
        ("PASS123", "No lowercase letter"),
        ("PassWord", "No digit"),
        ("Pass", "Too short and no digit"),
    ]
    
    for pwd, reason in invalid_passwords:
        try:
            UserRegisterRequest(email="user@example.com", password=pwd)
            print(f"❌ Invalid password accepted: {pwd} ({reason})")
            return False
        except ValidationError:
            print(f"✅ Invalid password rejected: {pwd} ({reason})")
    
    return True

def test_pagination_params():
    """Test 3: Pagination parameters validation."""
    print("\n📄 TEST 3: Pagination Parameters")
    print("-" * 50)
    
    # Valid pagination
    try:
        params = PaginationParams(limit=20, offset=0)
        print(f"✅ Valid pagination: limit={params.limit}, offset={params.offset}")
    except ValidationError as e:
        print(f"❌ Valid pagination rejected: {e}")
        return False
    
    # Test limits
    test_cases = [
        (1, 0, "Min limit"),
        (200, 0, "Max limit"),
        (0, 0, "Limit too low (should fail)"),
        (201, 0, "Limit too high (should fail)"),
        (20, -1, "Negative offset (should be clamped to 0)"),
    ]
    
    for limit, offset, desc in test_cases:
        try:
            params = PaginationParams(limit=limit, offset=offset)
            if limit == 0 or limit > 200:
                print(f"❌ {desc}: {limit}, {offset} should have failed")
                return False
            else:
                print(f"✅ {desc}: limit={params.limit}, offset={params.offset}")
        except ValidationError:
            if limit == 0 or limit > 200:
                print(f"✅ {desc} rejected: {limit}, {offset}")
            else:
                print(f"❌ {desc} rejected unexpectedly: {limit}, {offset}")
                return False
    
    return True

def test_api_health():
    """Test API health endpoint."""
    print("\n🏥 TEST 4: API Health Check")
    print("-" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                print("✅ API is healthy")
                return True
        print(f"❌ Unexpected response: {response.status_code} {response.text}")
        return False
    except Exception as e:
        print(f"❌ API health check failed: {e}")
        return False

def main():
    print("=" * 50)
    print("🚀 TESTING 3 IMPROVEMENTS")
    print("=" * 50)
    
    results = {
        "Email Validation": test_email_validation(),
        "Password Strength": test_password_validation(),
        "Pagination Params": test_pagination_params(),
        "API Health": test_api_health(),
    }
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
    
    all_passed = all(results.values())
    print("=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
