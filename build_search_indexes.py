"""
Build Search Indexes for a User
Run this after a user uploads contacts to build all search indexes
"""

import pandas as pd
import sys
from search_hybrid import HybridSearchEngine


def build_indexes_for_user(user_id: str, contacts_file: str):
    """
    Build all search indexes for a user

    Args:
        user_id: User ID
        contacts_file: Path to contacts CSV file
    """
    print(f"Building search indexes for user: {user_id}")
    print(f"Contacts file: {contacts_file}")
    print("="*60)

    # Load contacts
    try:
        contacts_df = pd.read_csv(contacts_file)
        print(f"✅ Loaded {len(contacts_df)} contacts")
    except Exception as e:
        print(f"❌ Failed to load contacts: {e}")
        return False

    # Ensure required columns exist
    required_cols = ['full_name', 'company', 'position', 'email']
    missing_cols = [col for col in required_cols if col not in contacts_df.columns]

    if missing_cols:
        # Try to create missing columns from available data
        if 'Full Name' in contacts_df.columns and 'full_name' not in contacts_df.columns:
            contacts_df['full_name'] = contacts_df['Full Name']
        if 'Company' in contacts_df.columns and 'company' not in contacts_df.columns:
            contacts_df['company'] = contacts_df['Company']
        if 'Position' in contacts_df.columns and 'position' not in contacts_df.columns:
            contacts_df['position'] = contacts_df['Position']
        if 'Email Address' in contacts_df.columns and 'email' not in contacts_df.columns:
            contacts_df['email'] = contacts_df['Email Address']

    # Initialize search engine
    search_engine = HybridSearchEngine()

    # Build indexes
    try:
        search_engine.build_indexes(user_id, contacts_df)
        print("\n✅ All search indexes built successfully!")
        return True
    except Exception as e:
        print(f"\n❌ Failed to build indexes: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python build_search_indexes.py <user_id> <contacts.csv>")
        print("Example: python build_search_indexes.py user123 sample_contacts.csv")
        sys.exit(1)

    user_id = sys.argv[1]
    contacts_file = sys.argv[2]

    success = build_indexes_for_user(user_id, contacts_file)
    sys.exit(0 if success else 1)
