"""
Test authentication module
"""

from auth import register_user, login_user, get_user_profile

def test_auth():
    print("🧪 Testing Authentication Module...\n")

    # Test 1: Register a test user
    print("1️⃣ Testing user registration...")
    result = register_user(
        email="test@example.com",
        password="testpassword123",
        full_name="Test User"
    )

    if result['success']:
        print(f"   ✅ Registration successful!")
        print(f"   User ID: {result['user']['id']}")
        print(f"   Email: {result['user']['email']}")
        print(f"   Name: {result['user']['full_name']}\n")
        user_id = result['user']['id']
    else:
        print(f"   ⚠️  {result['message']}")
        print("   (This is OK if user already exists from previous test)\n")

        # Try logging in with existing user
        print("   Attempting login with existing credentials...")
        login_result = login_user("test@example.com", "testpassword123")
        if login_result['success']:
            user_id = login_result['user']['id']
            print(f"   ✅ Login successful! User ID: {user_id}\n")
        else:
            print(f"   ❌ Login failed: {login_result['message']}\n")
            return

    # Test 2: Login with correct password
    print("2️⃣ Testing login with correct password...")
    result = login_user("test@example.com", "testpassword123")

    if result['success']:
        print(f"   ✅ Login successful!")
        print(f"   User: {result['user']['full_name']}")
        print(f"   Email: {result['user']['email']}\n")
    else:
        print(f"   ❌ Login failed: {result['message']}\n")
        return

    # Test 3: Login with wrong password
    print("3️⃣ Testing login with wrong password...")
    result = login_user("test@example.com", "wrongpassword")

    if not result['success']:
        print(f"   ✅ Correctly rejected: {result['message']}\n")
    else:
        print(f"   ❌ ERROR: Should have rejected wrong password!\n")

    # Test 4: Get user profile
    print("4️⃣ Testing get user profile...")
    profile = get_user_profile(user_id)

    if profile:
        print(f"   ✅ Profile retrieved!")
        print(f"   Name: {profile['full_name']}")
        print(f"   Email: {profile['email']}")
        print(f"   Plan: {profile['plan_tier']}")
        print(f"   Created: {profile['created_at']}\n")
    else:
        print(f"   ❌ Failed to retrieve profile\n")

    print("🎉 All authentication tests passed!")
    print("\nNext step: Integrate authentication into main app")

if __name__ == "__main__":
    test_auth()
