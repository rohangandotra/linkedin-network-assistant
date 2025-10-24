#!/usr/bin/env python3
"""List all users in the database"""

from dotenv import load_dotenv
import os
from supabase import create_client

# Load environment variables
load_dotenv()

# Get Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

# Create Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Fetch all users
try:
    response = supabase.table('users').select(
        'id, full_name, email, organization, created_at, email_verified, is_verified'
    ).order('created_at', desc=True).execute()

    users = response.data

    if not users:
        print("No users found in the database.")
    else:
        print(f"\n{'='*100}")
        print(f"TOTAL USERS: {len(users)}")
        print(f"{'='*100}\n")

        for i, user in enumerate(users, 1):
            print(f"{i}. {user['full_name']}")
            print(f"   Email: {user['email']}")
            print(f"   Organization: {user.get('organization', 'N/A')}")
            print(f"   Email Verified: {user.get('email_verified', False)}")
            print(f"   Account Verified: {user.get('is_verified', False)}")
            print(f"   Created: {user['created_at']}")
            print(f"   User ID: {user['id']}")
            print()

        print(f"{'='*100}")
        print(f"TOTAL USERS: {len(users)}")
        print(f"{'='*100}\n")

except Exception as e:
    print(f"Error fetching users: {e}")
