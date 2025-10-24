"""
Check if Phase 3A security schema tables exist in Supabase
"""
import auth

def check_security_schema():
    """Check if all security tables exist"""
    supabase = auth.get_supabase_client()

    print("Checking Phase 3A Security Schema...")
    print("=" * 60)

    # Tables that should exist
    security_tables = [
        'password_reset_tokens',
        'login_attempts',
        'api_rate_limits',
        'security_events'
    ]

    results = {}

    for table in security_tables:
        try:
            # Try to query the table (will fail if doesn't exist)
            response = supabase.table(table).select("*").limit(1).execute()
            results[table] = "✅ EXISTS"
            print(f"✅ {table:30s} - Table exists")
        except Exception as e:
            results[table] = f"❌ MISSING - {str(e)}"
            print(f"❌ {table:30s} - Table NOT found")

    print("\n" + "=" * 60)

    # Check if email_verified column exists in users table
    print("\nChecking users table columns...")
    try:
        response = supabase.table('users').select('id, email_verified, verification_token').limit(1).execute()
        if response.data and len(response.data) > 0:
            user = response.data[0]
            if 'email_verified' in user:
                print("✅ email_verified column exists in users table")
            else:
                print("❌ email_verified column MISSING from users table")
        else:
            print("⚠️  No users in database to verify columns")
    except Exception as e:
        print(f"❌ Error checking users table: {e}")

    print("\n" + "=" * 60)

    # Summary
    missing_tables = [t for t, status in results.items() if "MISSING" in status]

    if missing_tables:
        print(f"\n❌ SCHEMA INCOMPLETE - {len(missing_tables)} table(s) missing:")
        for table in missing_tables:
            print(f"   - {table}")
        print("\n📋 ACTION REQUIRED:")
        print("   1. Open Supabase SQL Editor: https://supabase.com/dashboard/project/gfdbsdmjczrmygzvitiq/sql")
        print("   2. Open security_schema.sql in your editor")
        print("   3. Copy the entire contents")
        print("   4. Paste into Supabase SQL Editor")
        print("   5. Click 'Run' to execute")
        print("   6. Run this script again to verify")
    else:
        print("\n✅ ALL SECURITY TABLES EXIST!")
        print("   Phase 3A schema is fully deployed.")
        print("\n🚀 Next steps:")
        print("   1. Test locally: python3 -m streamlit run app.py")
        print("   2. Try password reset flow")
        print("   3. Try registration with email verification")
        print("   4. Deploy to Streamlit Cloud")

if __name__ == "__main__":
    check_security_schema()
