#!/usr/bin/env python3
"""
Check all users in the database
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Connect to Supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

print("=" * 80)
print("DATABASE USERS")
print("=" * 80)

# Query all users
response = supabase.table('users').select("*").execute()

if response.data:
    print(f"\nFound {len(response.data)} user(s):\n")

    for i, user in enumerate(response.data, 1):
        print(f"{i}. Email: {user['email']}")
        print(f"   Full Name: {user['full_name']}")
        print(f"   Plan: {user.get('plan_tier', 'N/A')}")
        print(f"   Created: {user.get('created_at', 'N/A')}")
        print(f"   Last Login: {user.get('last_login', 'Never')}")
        print(f"   Password Hash: {user.get('password_hash', 'N/A')[:50]}...")
        print()
else:
    print("\n❌ No users found in database\n")

print("=" * 80)
