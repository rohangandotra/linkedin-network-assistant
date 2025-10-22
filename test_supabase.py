"""
Test script to verify Supabase connection
Run this to make sure database is set up correctly
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def test_connection():
    """Test basic Supabase connection"""
    print("🧪 Testing Supabase Connection...\n")

    # Get credentials from .env
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("❌ ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env file")
        return False

    print(f"✅ Found credentials")
    print(f"   URL: {url}")
    print(f"   Key: {key[:20]}...{key[-10:]}\n")

    try:
        # Create Supabase client
        supabase: Client = create_client(url, key)
        print("✅ Supabase client created successfully\n")

        # Test 1: Check if tables exist
        print("📋 Testing database tables...")

        # Query users table (should be empty)
        response = supabase.table('users').select("*").limit(1).execute()
        print(f"   ✅ users table exists (found {len(response.data)} rows)")

        # Query contacts table (should be empty)
        response = supabase.table('contacts').select("*").limit(1).execute()
        print(f"   ✅ contacts table exists (found {len(response.data)} rows)")

        # Query csv_uploads table (should be empty)
        response = supabase.table('csv_uploads').select("*").limit(1).execute()
        print(f"   ✅ csv_uploads table exists (found {len(response.data)} rows)")

        print("\n🎉 SUCCESS! Supabase is fully configured and ready to use!")
        print("\nNext steps:")
        print("  1. ✅ Database schema created")
        print("  2. ✅ Connection verified")
        print("  3. ⏳ Ready to build authentication module")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nTroubleshooting:")
        print("  - Check that SQL schema was run in Supabase SQL Editor")
        print("  - Verify credentials in .env file are correct")
        print("  - Make sure you're using SUPABASE_SERVICE_KEY (not anon key)")
        return False

if __name__ == "__main__":
    test_connection()
