"""
Email Domain Enrichment for 6th Degree AI
Parse email domains to infer company information

Example:
- john@google.com → Company: Google
- sarah@stripe.com → Company: Stripe
- alex.chen@a16z.com → Company: Andreessen Horowitz (a16z)
"""

import pandas as pd
import re
from typing import Dict, Optional, Tuple


class EmailEnricher:
    """
    Enrich contact data by parsing email domains

    Infers company information from work email addresses
    """

    # Known company domain mappings
    DOMAIN_TO_COMPANY = {
        # Tech giants
        'google.com': 'Google',
        'gmail.com': None,  # Personal email
        'meta.com': 'Meta',
        'facebook.com': 'Meta',
        'instagram.com': 'Meta',
        'whatsapp.com': 'Meta',
        'apple.com': 'Apple',
        'microsoft.com': 'Microsoft',
        'amazon.com': 'Amazon',
        'netflix.com': 'Netflix',
        'salesforce.com': 'Salesforce',
        'oracle.com': 'Oracle',
        'adobe.com': 'Adobe',
        'ibm.com': 'IBM',
        'intel.com': 'Intel',
        'nvidia.com': 'NVIDIA',
        'amd.com': 'AMD',
        'qualcomm.com': 'Qualcomm',
        'cisco.com': 'Cisco',
        'vmware.com': 'VMware',

        # Startups & Tech
        'stripe.com': 'Stripe',
        'uber.com': 'Uber',
        'lyft.com': 'Lyft',
        'airbnb.com': 'Airbnb',
        'doordash.com': 'DoorDash',
        'instacart.com': 'Instacart',
        'square.com': 'Square',
        'plaid.com': 'Plaid',
        'coinbase.com': 'Coinbase',
        'robinhood.com': 'Robinhood',
        'chime.com': 'Chime',
        'figma.com': 'Figma',
        'notion.so': 'Notion',
        'slack.com': 'Slack',
        'zoom.us': 'Zoom',
        'dropbox.com': 'Dropbox',
        'asana.com': 'Asana',
        'atlassian.com': 'Atlassian',
        'gitlab.com': 'GitLab',
        'github.com': 'GitHub',
        'reddit.com': 'Reddit',
        'pinterest.com': 'Pinterest',
        'snap.com': 'Snap',
        'snapchat.com': 'Snap',
        'tiktok.com': 'TikTok',
        'bytedance.com': 'ByteDance',
        'twitter.com': 'Twitter',
        'x.com': 'X (Twitter)',

        # Venture Capital
        'a16z.com': 'Andreessen Horowitz',
        'sequoiacap.com': 'Sequoia Capital',
        'accel.com': 'Accel',
        'greylock.com': 'Greylock Partners',
        'benchmark.com': 'Benchmark',
        'kleinerperkins.com': 'Kleiner Perkins',
        'gv.com': 'Google Ventures',
        'nea.com': 'NEA',
        'foundry.com': 'Foundry Group',
        'spark.vc': 'Spark Capital',

        # Finance
        'gs.com': 'Goldman Sachs',
        'goldmansachs.com': 'Goldman Sachs',
        'jpmorgan.com': 'JPMorgan',
        'jpmchase.com': 'JPMorgan Chase',
        'morganstanley.com': 'Morgan Stanley',
        'citi.com': 'Citigroup',
        'baml.com': 'Bank of America',
        'blackrock.com': 'BlackRock',
        'vanguard.com': 'Vanguard',
        'fidelity.com': 'Fidelity',

        # Consulting
        'mckinsey.com': 'McKinsey & Company',
        'bain.com': 'Bain & Company',
        'bcg.com': 'Boston Consulting Group',
        'deloitte.com': 'Deloitte',
        'pwc.com': 'PwC',
        'ey.com': 'EY',
        'kpmg.com': 'KPMG',
        'accenture.com': 'Accenture',

        # AI Companies
        'openai.com': 'OpenAI',
        'anthropic.com': 'Anthropic',
        'deepmind.com': 'DeepMind',
        'huggingface.co': 'Hugging Face',
        'cohere.ai': 'Cohere',
        'stability.ai': 'Stability AI',
        'midjourney.com': 'Midjourney',
        'character.ai': 'Character.AI',

        # Personal email providers (ignore these)
        'yahoo.com': None,
        'hotmail.com': None,
        'outlook.com': None,
        'icloud.com': None,
        'me.com': None,
        'aol.com': None,
        'protonmail.com': None,
    }

    def __init__(self):
        """Initialize email enricher"""
        self.stats = {
            'total_processed': 0,
            'enriched': 0,
            'already_had_company': 0,
            'personal_email': 0,
            'no_email': 0
        }

    def extract_domain(self, email: str) -> Optional[str]:
        """
        Extract domain from email address

        Args:
            email: Email address

        Returns:
            Domain or None

        Example:
            extract_domain("john@google.com") → "google.com"
        """
        if not email or not isinstance(email, str):
            return None

        email = email.strip().lower()

        # Basic email validation
        if '@' not in email:
            return None

        try:
            domain = email.split('@')[1]
            return domain
        except:
            return None

    def infer_company_from_domain(self, domain: str) -> Optional[str]:
        """
        Infer company name from email domain

        Args:
            domain: Email domain (e.g., "google.com")

        Returns:
            Company name or None

        Example:
            infer_company_from_domain("google.com") → "Google"
            infer_company_from_domain("gmail.com") → None (personal)
        """
        if not domain:
            return None

        domain = domain.strip().lower()

        # Check known mappings
        if domain in self.DOMAIN_TO_COMPANY:
            return self.DOMAIN_TO_COMPANY[domain]

        # For unknown domains, try to guess from domain name
        # Remove common TLDs and clean up
        company_name = domain

        # Remove TLDs
        tlds = ['.com', '.co', '.io', '.ai', '.net', '.org', '.vc', '.us', '.so']
        for tld in tlds:
            if company_name.endswith(tld):
                company_name = company_name[:-len(tld)]
                break

        # Capitalize first letter
        if company_name:
            company_name = company_name.capitalize()
            return company_name

        return None

    def enrich_contact(self, contact: Dict) -> Tuple[Dict, bool]:
        """
        Enrich a single contact with company info from email

        Args:
            contact: Contact dictionary with 'email' and 'company' fields

        Returns:
            (enriched_contact, was_enriched)

        Example:
            contact = {'email': 'john@google.com', 'company': ''}
            enriched, changed = enrich_contact(contact)
            # enriched['company'] == 'Google'
            # changed == True
        """
        self.stats['total_processed'] += 1

        email = contact.get('email', '').strip()
        company = contact.get('company', '').strip()

        # Skip if no email
        if not email:
            self.stats['no_email'] += 1
            return contact, False

        # Skip if already has company
        if company:
            self.stats['already_had_company'] += 1
            return contact, False

        # Extract domain and infer company
        domain = self.extract_domain(email)
        if not domain:
            return contact, False

        inferred_company = self.infer_company_from_domain(domain)

        # Personal email or no match
        if not inferred_company:
            self.stats['personal_email'] += 1
            return contact, False

        # Enrich!
        contact = contact.copy()
        contact['company'] = inferred_company
        contact['company_source'] = 'email_domain'
        self.stats['enriched'] += 1

        return contact, True

    def enrich_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        Enrich entire contacts DataFrame

        Args:
            df: Contacts DataFrame with 'email' and 'company' columns

        Returns:
            (enriched_df, stats)

        Example:
            df = pd.DataFrame([
                {'email': 'john@google.com', 'company': ''},
                {'email': 'sarah@stripe.com', 'company': 'Stripe'}
            ])
            enriched_df, stats = enricher.enrich_dataframe(df)
            # stats['enriched'] == 1 (john got Google, sarah already had Stripe)
        """
        # Reset stats
        self.stats = {
            'total_processed': 0,
            'enriched': 0,
            'already_had_company': 0,
            'personal_email': 0,
            'no_email': 0
        }

        if df.empty:
            return df, self.stats

        # Ensure columns exist
        if 'email' not in df.columns:
            df['email'] = ''
        if 'company' not in df.columns:
            df['company'] = ''

        # Enrich each contact
        enriched_contacts = []
        for _, row in df.iterrows():
            contact = row.to_dict()
            enriched_contact, _ = self.enrich_contact(contact)
            enriched_contacts.append(enriched_contact)

        enriched_df = pd.DataFrame(enriched_contacts)

        return enriched_df, self.stats

    def get_stats(self) -> Dict:
        """Get enrichment statistics"""
        return self.stats.copy()


# Singleton instance
_enricher_instance = None

def get_email_enricher() -> EmailEnricher:
    """Get singleton email enricher instance"""
    global _enricher_instance
    if _enricher_instance is None:
        _enricher_instance = EmailEnricher()
    return _enricher_instance


def enrich_contacts_from_email(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    Convenience function to enrich contacts DataFrame

    Args:
        df: Contacts DataFrame

    Returns:
        (enriched_df, stats)
    """
    enricher = get_email_enricher()
    return enricher.enrich_dataframe(df)


if __name__ == "__main__":
    # Test the email enricher
    print("Testing Email Enricher...\n")

    enricher = EmailEnricher()

    # Test cases
    test_contacts = [
        {'email': 'john@google.com', 'company': '', 'name': 'John Smith'},
        {'email': 'sarah@stripe.com', 'company': '', 'name': 'Sarah Johnson'},
        {'email': 'alex@a16z.com', 'company': '', 'name': 'Alex Chen'},
        {'email': 'maria@gmail.com', 'company': '', 'name': 'Maria Garcia'},  # Personal
        {'email': 'david@meta.com', 'company': 'Facebook', 'name': 'David Lee'},  # Already has company
        {'email': '', 'company': '', 'name': 'Jane Doe'},  # No email
        {'email': 'tom@unknown-startup.io', 'company': '', 'name': 'Tom Wilson'},  # Unknown domain
    ]

    df = pd.DataFrame(test_contacts)

    print("Before enrichment:")
    print(df[['name', 'email', 'company']])
    print()

    enriched_df, stats = enricher.enrich_dataframe(df)

    print("After enrichment:")
    print(enriched_df[['name', 'email', 'company']])
    print()

    print("Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()

    print(f"✅ Enrichment rate: {stats['enriched']}/{stats['total_processed']} ({stats['enriched']/stats['total_processed']*100:.1f}%)")
