#!/usr/bin/env python3
"""
Reset password for a user
"""

import sys
import auth

print("=" * 80)
print("PASSWORD RESET TOOL")
print("=" * 80)

email = input("\nEnter email address: ").strip()
new_password = input("Enter new password (min 6 chars): ").strip()

if len(new_password) < 6:
    print("❌ Password must be at least 6 characters")
    sys.exit(1)

# Get supabase client
supabase = auth.get_supabase_client()

# Get user
response = supabase.table('users').select("*").eq('email', email).execute()

if not response.data or len(response.data) == 0:
    print(f"❌ User with email {email} not found")
    sys.exit(1)

user = response.data[0]
user_id = user['id']

# Hash new password
new_hash = auth.hash_password(new_password)

# Update password
supabase.table('users').update({'password_hash': new_hash}).eq('id', user_id).execute()

print(f"\n✅ Password reset successfully for {email}")
print(f"   You can now login with the new password")
print("\n" + "=" * 80)
