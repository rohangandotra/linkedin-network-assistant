import streamlit as st
import pandas as pd
import json
from openai import OpenAI
import os
from dotenv import load_dotenv
from io import StringIO
import uuid
import requests
import traceback

# Load environment variables FIRST - before importing modules that need them
load_dotenv()

# Import analytics module (optional - don't crash if missing)
try:
    import analytics
    HAS_ANALYTICS = True
except Exception as e:
    print(f"⚠️ Analytics module not available: {e}")
    HAS_ANALYTICS = False
    # Create a dummy analytics module
    class DummyAnalytics:
        @staticmethod
        def log_search_query(*args, **kwargs):
            pass
        @staticmethod
        def log_csv_upload(*args, **kwargs):
            pass
        @staticmethod
        def log_email_generation(*args, **kwargs):
            pass
        @staticmethod
        def log_contact_export(*args, **kwargs):
            pass
    analytics = DummyAnalytics()

# Import authentication module (needs env vars to be loaded)
import auth

# Import collaboration module
import collaboration

# Import security module
import security

# Import security services (Week 1 security hardening)
from services.security import (
    check_rate_limit,
    get_remaining_attempts,
    sanitize_html,
    validate_email,
    validate_search_query,
    sanitize_csv_data,
    generate_csrf_token,
    validate_csrf_token_detailed,
    cleanup_csrf_tokens,
    log_security_event,
    log_failed_login,
    log_successful_login,
    log_csrf_failure,
    log_rate_limit,
    log_malicious_input
)

# Import feedback module
import feedback

# Import profile module
import user_profile

# Phase 3B: Import new hybrid search system
try:
    from search_integration import (
        initialize_search_for_user,
        smart_search,
        migrate_to_new_search,
        get_search_summary
    )
    HAS_NEW_SEARCH = True
    print("✅ Phase 3B hybrid search loaded")
except ImportError as e:
    HAS_NEW_SEARCH = False
    print(f"⚠️  New search system not available: {e}")

# Phase 4: Import AI search agent (NEW - rebuilt from scratch)
try:
    from services.ai_search_agent import create_ai_search_agent
    HAS_AI_AGENT = True
    print("✅ AI Search Agent loaded (GPT-4 powered)")
except ImportError as e:
    HAS_AI_AGENT = False
    print(f"⚠️  AI Search Agent not available: {e}")

# Initialize OpenAI client - works both locally and on Streamlit Cloud
def get_openai_api_key():
    """Get OpenAI API key from Streamlit secrets or environment variable"""
    # Try Streamlit Cloud secrets first
    try:
        if 'OPENAI_API_KEY' in st.secrets:
            key = st.secrets["OPENAI_API_KEY"]
            # CRITICAL: Strip whitespace and newlines that may be in TOML secrets
            key = key.strip().replace('\n', '').replace('\r', '').replace(' ', '')
            if key and len(key) > 20:  # Basic validation
                return key
    except Exception:
        pass

    # Fall back to environment variable for local development
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        # Also strip for consistency
        api_key = api_key.strip().replace('\n', '').replace('\r', '').replace(' ', '')
        if len(api_key) > 20:
            return api_key

    st.error("OpenAI API key not found! Please check Streamlit Cloud secrets.")
    st.stop()
    return None

# Initialize client lazily to avoid startup errors
client = None

def get_client():
    """Get or create OpenAI client"""
    global client
    if client is None:
        try:
            client = OpenAI(
                api_key=get_openai_api_key(),
                timeout=30.0,
                max_retries=2
            )
        except Exception as e:
            st.error(f"Failed to initialize OpenAI client: {str(e)}")
            st.stop()
    return client

def run_diagnostic_test():
    """Run comprehensive diagnostic tests to identify connection issues"""
    api_key = get_openai_api_key()

    results = {
        "api_key_loaded": False,
        "direct_http_test": {"status": "pending", "details": ""},
        "openai_sdk_test": {"status": "pending", "details": ""},
        "network_info": {},
    }

    # Test 1: Check API key is loaded
    if api_key and len(api_key) > 20:
        results["api_key_loaded"] = True
        results["api_key_format"] = "Valid (hidden for security)"
    else:
        results["api_key_loaded"] = False
        results["api_key_format"] = "Invalid or missing"
        return results

    # Test 2: Direct HTTP request to OpenAI API
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Say 'test successful' in 2 words"}],
            "max_tokens": 10
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        results["direct_http_test"]["status_code"] = response.status_code

        if response.status_code == 200:
            results["direct_http_test"]["status"] = "success"
            data = response.json()
            results["direct_http_test"]["details"] = f"Response: {data['choices'][0]['message']['content']}"
        else:
            results["direct_http_test"]["status"] = "failed"
            results["direct_http_test"]["details"] = f"Error: {response.status_code} - {response.text[:200]}"

    except requests.exceptions.Timeout:
        results["direct_http_test"]["status"] = "timeout"
        results["direct_http_test"]["details"] = "Request timed out after 30 seconds"
    except requests.exceptions.ConnectionError as e:
        results["direct_http_test"]["status"] = "connection_error"
        results["direct_http_test"]["details"] = f"Cannot connect to OpenAI API: {str(e)[:200]}"
    except Exception as e:
        results["direct_http_test"]["status"] = "error"
        results["direct_http_test"]["details"] = f"{type(e).__name__}: {str(e)[:200]}"
        results["direct_http_test"]["traceback"] = traceback.format_exc()[:500]

    # Test 3: OpenAI SDK test
    try:
        test_client = OpenAI(api_key=api_key, timeout=30.0, max_retries=0)

        response = test_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'test successful' in 2 words"}],
            max_tokens=10
        )

        results["openai_sdk_test"]["status"] = "success"
        results["openai_sdk_test"]["details"] = f"Response: {response.choices[0].message.content}"

    except Exception as e:
        results["openai_sdk_test"]["status"] = "error"
        results["openai_sdk_test"]["details"] = f"{type(e).__name__}: {str(e)[:200]}"
        results["openai_sdk_test"]["traceback"] = traceback.format_exc()[:500]

    return results

# Generate session ID for tracking (persists for the session)
if 'session_id' not in st.session_state:
    st.session_state['session_id'] = str(uuid.uuid4())

# Initialize dark mode state
if 'dark_mode' not in st.session_state:
    st.session_state['dark_mode'] = False

# Page configuration
st.set_page_config(
    page_title="LinkedIn Network Assistant",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="auto"  # Auto-expand on desktop, collapsed on mobile
)

# Flow-inspired refined CSS styling - clean, minimal, professional
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Crimson+Pro:wght@400;600;700&display=swap');

    :root {
        /* SaaS-style modern color palette */
        /* Primary brand color - professional blue */
        --primary: #2B6CB0;
        --primary-hover: #2C5282;
        --primary-light: #dbeafe;

        /* Soft neutral backgrounds */
        --bg-primary: #fafaf9;
        --bg-secondary: #ffffff;
        --bg-tertiary: #f5f5f4;

        /* Text hierarchy - AA contrast compliant */
        --text-primary: #18181b;
        --text-secondary: #52525b;
        --text-tertiary: #a1a1aa;

        /* Borders - subtle 1px */
        --border-subtle: #e7e5e4;
        --border-medium: #d6d3d1;

        /* Feedback colors */
        --success: #16a34a;
        --error: #dc2626;
        --warning: #ea580c;

        /* Spacing scale */
        --space-1: 0.25rem;
        --space-2: 0.5rem;
        --space-3: 0.75rem;
        --space-4: 1rem;
        --space-6: 1.5rem;
        --space-8: 2rem;
        --space-12: 3rem;
        --space-16: 4rem;
        --space-24: 6rem;

        /* Border radius - 12-16px range */
        --radius-sm: 0.5rem;
        --radius-md: 0.75rem;
        --radius-lg: 1rem;
        --radius-pill: 9999px;

        /* Refined shadows - subtle and consistent */
        --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
        --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.06);
        --shadow-lg: 0 4px 16px rgba(0, 0, 0, 0.08);

        /* Typography */
        --font-serif: 'Crimson Pro', Georgia, serif;
        --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
    }

    * {
        font-family: var(--font-sans);
    }

    /* Sidebar styling - Flow aesthetic */
    section[data-testid="stSidebar"] {
        background: var(--bg-secondary);
        border-right: 1px solid var(--border-subtle);
    }

    section[data-testid="stSidebar"] > div {
        background: var(--bg-secondary);
    }

    /* Main background - soft neutral */
    .main {
        background: var(--bg-primary);
        padding-top: 0 !important;
    }

    /* Content container - centered, spacious */
    .block-container {
        padding-top: 5rem !important;
        padding-bottom: var(--space-16);
        max-width: 1140px;
        margin: 0 auto;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Hero typography - Serif/Sans pairing */
    .hero-title {
        font-family: var(--font-serif);
        font-size: 4rem;
        font-weight: 600;
        color: var(--text-primary);
        letter-spacing: -0.02em;
        line-height: 1.1;
        margin-bottom: var(--space-4);
    }

    .hero-subtitle {
        font-family: var(--font-sans);
        font-size: 1.125rem;
        font-weight: 400;
        color: var(--text-secondary);
        line-height: 1.5;
        margin-bottom: var(--space-8);
    }

    /* Typography hierarchy */
    h1 {
        font-family: var(--font-serif);
        font-size: 2.5rem !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.02em;
        line-height: 1.2 !important;
    }

    h2, h3 {
        font-family: var(--font-sans);
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.01em !important;
    }

    /* Search input - Clean and minimal */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: var(--radius-md);
        border: 1px solid var(--border-subtle);
        background: var(--bg-secondary);
        padding: 0.875rem 1.25rem;
        font-size: 0.9375rem;
        transition: all 0.2s ease;
        color: var(--text-primary);
        box-shadow: var(--shadow-sm);
        font-family: var(--font-sans);
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        outline: none;
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(43, 108, 176, 0.1), var(--shadow-md);
    }

    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: var(--text-tertiary);
    }

    /* Select boxes - Notion style */
    .stSelectbox > div > div {
        border-radius: var(--radius-md);
        border: 1px solid var(--border-subtle);
        transition: all 0.2s ease;
    }

    .stSelectbox > div > div:hover {
        border-color: var(--border-medium);
    }

    .stSelectbox > div > div:focus-within {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(43, 108, 176, 0.1);
    }

    /* Multiselect - Clean */
    .stMultiSelect > div > div {
        border-radius: var(--radius-md);
        border: 1px solid var(--border-subtle);
        background: var(--bg-secondary);
    }

    .stMultiSelect > div > div:focus-within {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(43, 108, 176, 0.1);
    }

    /* Checkboxes - Notion style */
    .stCheckbox {
        padding: 0.25rem 0;
    }

    .stCheckbox > label {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        cursor: pointer;
        user-select: none;
    }

    .stCheckbox > label > div:first-child {
        flex-shrink: 0;
    }

    /* Radio buttons - Clean */
    .stRadio > div {
        gap: 0.5rem;
    }

    .stRadio > div > label {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem;
        border-radius: var(--radius-sm);
        transition: background 0.15s ease;
        cursor: pointer;
    }

    .stRadio > div > label:hover {
        background: var(--bg-tertiary);
    }

    /* ============================================
       STANDARDIZED BUTTON STYLES - SaaS Modern
       ============================================ */

    /* Base button styling - All buttons */
    .stButton > button,
    .stFormSubmitButton > button {
        /* Shape: Rectangular with moderate corner radius */
        border-radius: 10px !important;

        /* Sizing: Minimum width to prevent text wrapping */
        min-width: 120px !important;
        padding: 0.75rem 1.5rem !important;

        /* Typography: 16px semibold */
        font-size: 16px !important;
        font-weight: 600 !important;
        line-height: 1.5 !important;

        /* Spacing: Prevent text wrapping */
        white-space: nowrap !important;

        /* Transitions: Smooth 150ms */
        transition: all 0.15s ease !important;

        /* Cursor */
        cursor: pointer !important;

        /* Remove transforms to avoid bubbly feel */
        transform: none !important;
    }

    /* Primary button (type="primary" or default) */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid*="primary"],
    .stFormSubmitButton > button,
    .stButton > button:not([kind="secondary"]):not([kind="tertiary"]) {
        background: var(--primary) !important;
        color: white !important;
        border: 2px solid var(--primary) !important;
        box-shadow: var(--shadow-sm) !important;
    }

    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid*="primary"]:hover,
    .stFormSubmitButton > button:hover,
    .stButton > button:not([kind="secondary"]):not([kind="tertiary"]):hover {
        background: var(--primary-hover) !important;
        border-color: var(--primary-hover) !important;
        box-shadow: var(--shadow-md) !important;
        /* No transform - keep it flat */
    }

    /* Secondary button (type="secondary") */
    .stButton > button[kind="secondary"],
    .stButton > button[data-testid*="secondary"] {
        background: white !important;
        color: var(--primary) !important;
        border: 2px solid var(--primary) !important;
        box-shadow: var(--shadow-sm) !important;
    }

    .stButton > button[kind="secondary"]:hover,
    .stButton > button[data-testid*="secondary"]:hover {
        background: var(--primary-light) !important;
        border-color: var(--primary-hover) !important;
        color: var(--primary-hover) !important;
        box-shadow: var(--shadow-md) !important;
        /* No transform - keep it flat */
    }

    /* Active/pressed state - subtle feedback */
    .stButton > button:active,
    .stFormSubmitButton > button:active {
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1) !important;
        transform: none !important;
    }

    /* Disabled state */
    .stButton > button:disabled,
    .stFormSubmitButton > button:disabled {
        opacity: 0.5 !important;
        cursor: not-allowed !important;
    }

    /* Button spacing - Consistent gaps between buttons */
    .stButton {
        margin: 0 !important;
    }

    /* Horizontal button groups - even spacing */
    [data-testid="column"] .stButton {
        margin: 0 6px !important;
    }

    [data-testid="column"]:first-child .stButton {
        margin-left: 0 !important;
    }

    [data-testid="column"]:last-child .stButton {
        margin-right: 0 !important;
    }

    /* File uploader - Premium card */
    .stFileUploader {
        background: var(--bg-secondary);
        border-radius: var(--radius-lg);
        padding: var(--space-8);
        border: 1px solid var(--border-light);
        transition: all 0.15s ease;
        box-shadow: var(--shadow-sm);
    }

    .stFileUploader:hover {
        border-color: var(--primary);
        background: var(--bg-secondary);
        box-shadow: var(--shadow-md);
    }

    /* Dataframe styling - Clean card */
    .stDataFrame {
        border-radius: var(--radius-md);
        overflow: hidden;
        border: 1px solid var(--border-subtle);
        box-shadow: var(--shadow-sm);
        background: var(--bg-secondary);
    }

    /* Success/Info boxes - Clean alerts */
    .stSuccess {
        background: rgba(16, 185, 129, 0.05);
        border: 1px solid var(--success);
        border-radius: var(--radius-md);
        padding: var(--space-4);
        color: var(--success);
        box-shadow: var(--shadow-sm);
        font-weight: 500;
    }

    .stInfo {
        background: rgba(37, 99, 235, 0.05);
        border: 1px solid var(--primary);
        border-radius: var(--radius-md);
        padding: var(--space-4);
        color: var(--primary);
        box-shadow: var(--shadow-sm);
        font-weight: 500;
    }

    .stWarning {
        background: rgba(234, 88, 12, 0.05);
        border: 1px solid var(--warning);
        border-radius: var(--radius-md);
        padding: var(--space-4);
        color: var(--warning);
        box-shadow: var(--shadow-sm);
        font-weight: 500;
    }

    .stError {
        background: rgba(220, 38, 38, 0.05);
        border: 1px solid var(--error);
        border-radius: var(--radius-md);
        padding: var(--space-4);
        color: var(--error);
        box-shadow: var(--shadow-sm);
        font-weight: 500;
    }

    /* Expander styling - Clean card */
    .streamlit-expanderHeader {
        background: var(--bg-secondary);
        border-radius: var(--radius-md);
        font-weight: 600;
        color: var(--text-primary);
        border: 1px solid var(--border-subtle);
        transition: all 0.15s ease;
        box-shadow: var(--shadow-sm);
    }

    .streamlit-expanderHeader:hover {
        border-color: var(--border-medium);
        background: var(--bg-tertiary);
        box-shadow: var(--shadow-md);
    }

    /* Results summary - Clean card */
    .results-summary {
        background: var(--bg-secondary);
        padding: var(--space-8);
        border-radius: var(--radius-md);
        border: 1px solid var(--border-subtle);
        margin: var(--space-6) 0;
        box-shadow: var(--shadow-sm);
        transition: all 0.15s ease;
    }

    .results-summary:hover {
        box-shadow: var(--shadow-md);
        border-color: var(--border-medium);
    }

    .results-summary strong {
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--text-primary);
        display: block;
        margin-bottom: 0.5rem;
    }

    .results-summary-meta {
        color: var(--text-secondary);
        font-size: 0.9375rem;
        line-height: 1.6;
    }

    /* Download buttons - Standardized secondary style */
    .stDownloadButton > button {
        background: white !important;
        color: var(--primary) !important;
        border: 2px solid var(--primary) !important;
        border-radius: 10px !important;
        padding: 0.75rem 1.5rem !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        min-width: 120px !important;
        white-space: nowrap !important;
        transition: all 0.15s ease !important;
        box-shadow: var(--shadow-sm) !important;
    }

    .stDownloadButton > button:hover {
        background: var(--primary-light) !important;
        color: var(--primary-hover) !important;
        border-color: var(--primary-hover) !important;
        box-shadow: var(--shadow-md) !important;
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Section headers - Clean */
    h2 {
        font-size: 1.75rem !important;
        margin-bottom: var(--space-6) !important;
    }

    h3 {
        font-size: 1.25rem !important;
        margin-bottom: var(--space-4) !important;
    }

    /* Markdown text */
    .main .stMarkdown {
        color: var(--text-secondary);
        line-height: 1.7;
    }

    /* Dividers - Clean */
    hr {
        border: none;
        height: 1px;
        background: var(--border-subtle);
        margin: var(--space-8) 0;
    }

    /* Section spacing - Generous whitespace */
    .section-spacing {
        margin-top: var(--space-12);
        margin-bottom: var(--space-12);
    }

    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: var(--space-6);
        letter-spacing: -0.01em;
    }

    /* Pagination controls - Notion style */
    .pagination-button {
        min-width: 40px !important;
        height: 40px !important;
        padding: 0.5rem !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    .pagination-current {
        background: var(--primary) !important;
        color: white !important;
        font-weight: 600;
        padding: 0.5rem 1rem;
        border-radius: var(--radius-sm);
        display: inline-block;
        text-align: center;
    }

    /* Upload card - Premium styling */
    .upload-section {
        background: var(--bg-secondary);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: var(--space-8);
        margin: var(--space-8) 0;
        box-shadow: var(--shadow-sm);
        transition: all 0.2s ease;
    }

    .upload-section:hover {
        border-color: var(--primary);
        box-shadow: var(--shadow-md);
    }

    .upload-header {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: var(--space-4);
        text-align: center;
    }

    .upload-subtitle {
        color: var(--text-secondary);
        font-size: 0.9375rem;
        text-align: center;
        margin-bottom: var(--space-6);
    }

    /* Card component */
    .card {
        background: var(--bg-secondary);
        border-radius: var(--radius-md);
        padding: var(--space-6);
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border-subtle);
        transition: all 0.15s ease;
    }

    .card:hover {
        box-shadow: var(--shadow-md);
    }

    /* ============================================
       NOTION-INSPIRED CONTACT CARDS
       ============================================ */

    .contact-card {
        background: var(--bg-secondary);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: var(--space-6);
        margin-bottom: var(--space-3);
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: var(--shadow-sm);
        position: relative;
        cursor: pointer;
    }

    .contact-card:hover {
        border-color: var(--primary);
        box-shadow: 0 4px 12px rgba(43, 108, 176, 0.12);
        transform: translateY(-2px);
    }

    .contact-avatar {
        width: 44px;
        height: 44px;
        border-radius: var(--radius-md);
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-hover) 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 600;
        font-size: 1.125rem;
        flex-shrink: 0;
        box-shadow: var(--shadow-sm);
    }

    .contact-name {
        font-weight: 600;
        font-size: 1rem;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
        line-height: 1.4;
    }

    .contact-position {
        color: var(--text-secondary);
        font-size: 0.9375rem;
        margin-bottom: 0.25rem;
        line-height: 1.5;
    }

    .contact-company {
        color: var(--text-tertiary);
        font-size: 0.875rem;
        display: flex;
        align-items: center;
        gap: 0.375rem;
    }

    .contact-email {
        color: var(--primary);
        font-size: 0.8125rem;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        margin-top: 0.5rem;
        padding: 0.25rem 0.5rem;
        background: var(--primary-light);
        border-radius: var(--radius-sm);
    }

    .contact-info-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin-top: 0.5rem;
    }

    /* Extended network contact card */
    .extended-contact-card {
        background: #f0f9ff;
        border: 1px solid #bfdbfe;
        border-left: 4px solid #3b82f6;
        border-radius: var(--radius-md);
        padding: var(--space-6);
        margin-bottom: var(--space-3);
        transition: all 0.2s ease;
        box-shadow: var(--shadow-sm);
    }

    .extended-contact-card:hover {
        border-left-color: #2563eb;
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }

    .extended-badge {
        background: white;
        padding: 0.375rem 0.75rem;
        border-radius: var(--radius-sm);
        color: #0369a1;
        font-size: 0.8125rem;
        font-weight: 600;
        display: inline-block;
        margin-top: 0.75rem;
        box-shadow: var(--shadow-sm);
    }

    /* Top navigation bar */
    .top-nav {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 64px;
        background: var(--bg-secondary);
        border-bottom: 1px solid var(--border-subtle);
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 var(--space-8);
        z-index: 1000;
        box-shadow: var(--shadow-sm);
    }

    .header-title {
        font-family: var(--font-serif);
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: var(--text-primary) !important;
        text-decoration: none;
        line-height: 2.5rem !important;
        margin: 0 !important;
        letter-spacing: -0.01em;
    }

    .top-nav-logo {
        font-family: var(--font-serif);
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text-primary);
        text-decoration: none;
    }

    .top-nav-links {
        display: flex;
        gap: var(--space-8);
        align-items: center;
    }

    .top-nav-link {
        font-size: 0.9375rem;
        font-weight: 500;
        color: var(--text-secondary);
        text-decoration: none;
        transition: color 0.15s ease;
    }

    .top-nav-link:hover {
        color: var(--text-primary);
    }

    /* Select contacts header */
    .select-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: var(--space-6);
        padding: var(--space-4);
        background: var(--bg-tertiary);
        border-radius: var(--radius-md);
    }

    .select-header h3 {
        margin: 0 !important;
        font-size: 1.25rem !important;
        font-weight: 600;
        color: var(--text-primary);
    }

    .page-info {
        color: var(--text-secondary);
        font-size: 0.9375rem;
        font-weight: 500;
    }

    .top-nav-cta {
        background: var(--primary);
        color: white;
        border: 2px solid var(--primary);
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-size: 16px;
        min-width: 120px;
        white-space: nowrap;
        transition: all 0.15s ease;
        box-shadow: var(--shadow-sm);
        cursor: pointer;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
    }

    .top-nav-cta:hover {
        background: var(--primary-hover);
        border-color: var(--primary-hover);
        box-shadow: var(--shadow-md);
    }

    /* ============================================
       MOBILE RESPONSIVE STYLES
       ============================================ */

    @media (max-width: 768px) {
        .hero-title {
            font-size: 2.5rem;
        }

        .hero-subtitle {
            font-size: 1rem;
        }

        .block-container {
            padding-top: 5rem !important;
            padding-left: var(--space-4);
            padding-right: var(--space-4);
        }

        .top-nav {
            padding: 0 var(--space-4);
        }

        .top-nav-links {
            gap: var(--space-4);
        }

        .top-nav-link {
            display: none;
        }

        .stButton > button,
        .stFormSubmitButton > button {
            width: 100% !important;
            padding: 0.875rem 1.5rem !important;
            font-size: 16px !important;
            min-width: auto !important;
        }

        .stTextInput > div > div > input {
            width: 100%;
            font-size: 16px !important;
        }

        h2, h3, h4 {
            font-size: 1.4rem !important;
        }

        .stDataFrame {
            font-size: 0.9rem;
        }

        .results-summary {
            padding: var(--spacing-lg);
            font-size: 0.95rem;
        }

        .stDownloadButton > button {
            width: 100%;
            margin-bottom: var(--spacing-sm);
        }

        .card {
            padding: var(--spacing-lg);
        }
    }

    @media (max-width: 480px) {
        h1 {
            font-size: 1.875rem !important;
        }

        .subtitle {
            font-size: 0.95rem;
        }

        .block-container {
            padding-left: var(--spacing-sm);
            padding-right: var(--spacing-sm);
        }

        .stButton > button,
        .stFormSubmitButton > button {
            padding: 0.875rem 1.25rem !important;
            font-size: 16px !important;
        }
    }

    @media (min-width: 769px) and (max-width: 1024px) {
        h1 {
            font-size: 2.75rem !important;
        }

        .block-container {
            max-width: 900px;
        }
    }

    /* ============================================
       TAB STYLING - Clean tabs
       ============================================ */

    .stTabs {
        background: var(--bg-secondary);
        border-radius: var(--radius-md);
        padding: var(--space-2);
        border: 1px solid var(--border-subtle);
        box-shadow: var(--shadow-sm);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: var(--space-2);
        background: var(--bg-tertiary);
        padding: var(--space-2);
        border-radius: var(--radius-md);
    }

    .stTabs [data-baseweb="tab"] {
        background: var(--bg-secondary);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        color: var(--text-secondary);
        font-size: 0.9375rem;
        transition: all 0.15s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: var(--bg-secondary);
        border-color: var(--border-medium);
        color: var(--text-primary);
    }

    .stTabs [aria-selected="true"] {
        background: var(--primary) !important;
        color: white !important;
        border-color: var(--primary) !important;
        box-shadow: var(--shadow-md) !important;
    }

    .stTabs [data-baseweb="tab-panel"] {
        padding: var(--spacing-xl) var(--spacing-sm);
    }

    .stTabs button[role="tab"] {
        color: var(--gray-700) !important;
        font-weight: 600 !important;
    }

    .stTabs button[role="tab"][aria-selected="true"] {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# UNIFIED TOP NAVIGATION BAR (Phase 1)
# ============================================
# Replaces old top nav + sidebar + duplicate nav buttons

# Add CSS for clean, professional navigation bar
st.markdown("""
<style>
/* Top Navigation Bar - SaaS Modern (Notion/Linear style) */
.top-nav-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 32px;
    background: white;
    border-bottom: 1px solid #e5e7eb;
    margin-bottom: 0;
    height: 64px;
    box-sizing: border-box;
}

.top-nav-logo {
    font-family: var(--font-serif);
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
    line-height: 1;
}

.top-nav-buttons {
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Navigation button overrides - ONLY for top nav */
[data-testid="column"] > div > div > button[data-testid*="baseButton-"] {
    padding: 12px 20px !important;
    border-radius: 8px !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    height: 40px !important;
    min-width: auto !important;
    white-space: nowrap !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-sizing: border-box !important;
}

/* Gap columns create spacing - no additional margins needed */
</style>
""", unsafe_allow_html=True)

# CSS for text-link style buttons (no boxes) and inactive nav buttons
st.markdown("""
<style>
/* Top bar buttons - absolutely no borders or backgrounds - HIGHEST SPECIFICITY */
.text-link-button > .stButton {
    margin: 0 !important;
}

/* Target all button types explicitly with attribute selectors for maximum specificity */
.text-link-button > .stButton > button[kind="primary"],
.text-link-button > .stButton > button[kind="secondary"],
.text-link-button > .stButton > button:not([kind]),
.text-link-button .stButton > button[kind="primary"],
.text-link-button .stButton > button[kind="secondary"],
.text-link-button .stButton > button:not([kind]) {
    background: transparent !important;
    border: 0px solid transparent !important;
    box-shadow: none !important;
    outline: none !important;
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    padding: 8px 12px !important;
    min-width: auto !important;
    transition: color 0.15s ease !important;
    line-height: 2.5rem !important;
    height: 2.5rem !important;
    display: inline-flex !important;
    align-items: center !important;
    vertical-align: middle !important;
}

.text-link-button > .stButton > button[kind="primary"]:hover,
.text-link-button > .stButton > button[kind="secondary"]:hover,
.text-link-button > .stButton > button:not([kind]):hover,
.text-link-button .stButton > button[kind="primary"]:hover,
.text-link-button .stButton > button[kind="secondary"]:hover,
.text-link-button .stButton > button:not([kind]):hover {
    background: transparent !important;
    border: 0px solid transparent !important;
    box-shadow: none !important;
    color: var(--primary) !important;
}

.text-link-button > .stButton > button[kind="primary"]:focus,
.text-link-button > .stButton > button[kind="primary"]:active,
.text-link-button > .stButton > button[kind="secondary"]:focus,
.text-link-button > .stButton > button[kind="secondary"]:active,
.text-link-button > .stButton > button:not([kind]):focus,
.text-link-button > .stButton > button:not([kind]):active,
.text-link-button .stButton > button[kind="primary"]:focus,
.text-link-button .stButton > button[kind="primary"]:active,
.text-link-button .stButton > button[kind="secondary"]:focus,
.text-link-button .stButton > button[kind="secondary"]:active,
.text-link-button .stButton > button:not([kind]):focus,
.text-link-button .stButton > button:not([kind]):active {
    background: transparent !important;
    border: 0px solid transparent !important;
    box-shadow: none !important;
    outline: none !important;
}

/* Logo text styling */
.nav-logo-text {
    font-family: var(--font-serif);
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 40px;
    margin: 0;
}
</style>
""", unsafe_allow_html=True)

# ============================================
# PROFESSIONAL HEADER BAR (SaaS Style)
# ============================================
# NOTE: Header rendering moved inside main() function to prevent duplication

# Feedback Modal definition (at module level for access from header button)
def render_feedback_modal():
    """Render feedback modal when requested"""
    if not st.session_state.get('show_feedback_modal'):
        return

    st.markdown("### 📋 Report an Issue or Give Feedback")
    st.markdown("<p style='color: var(--text-secondary); margin-bottom: 1rem;'>Help us improve! Let us know if something isn't working or if you have ideas.</p>", unsafe_allow_html=True)

    feedback_type = st.selectbox(
        "Type of feedback",
        ["Bug Report", "Feature Request", "General Feedback", "Praise"],
        key="feedback_type_modal"
    )

    feedback_text = st.text_area(
        "Your feedback",
        placeholder="Describe what happened or what you'd like to see...",
        height=120,
        key="feedback_text_modal"
    )

    # For anonymous users, optionally collect email
    feedback_email = None
    if not st.session_state.get('authenticated'):
        feedback_email = st.text_input(
            "Email (optional)",
            placeholder="your@email.com",
            help="We'll only use this to follow up on your feedback",
            key="feedback_email_modal"
        )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Submit Feedback", use_container_width=True, type="primary", key="feedback_submit_modal"):
            if feedback_text and feedback_text.strip():
                # Get user info
                user_id = st.session_state.get('user', {}).get('id', 'anonymous')
                user_email = st.session_state.get('user', {}).get('email') or feedback_email

                # === SECURITY: Rate Limiting ===
                allowed, error_msg = check_rate_limit(user_id, 'feedback')
                if not allowed:
                    st.error(error_msg)
                    log_rate_limit(user_id, 'feedback', extract_wait_time(error_msg))
                else:
                    # === SECURITY: Input Validation ===
                    from services.security.input_validator import InputValidator
                    validation = InputValidator.sanitize_feedback(feedback_text)

                    if not validation['valid']:
                        st.error(validation['message'])
                    else:
                        # Use sanitized feedback
                        sanitized_feedback = validation['text']

                        # Get page context
                        page_context = "Main Dashboard"
                        if 'contacts_df' not in st.session_state:
                            page_context = "Empty State (No Contacts)"
                        elif st.session_state.get('show_connections'):
                            page_context = "Connections Page"

                        # Submit feedback (using sanitized text)
                        result = feedback.submit_feedback(
                            feedback_text=sanitized_feedback,
                            feedback_type=feedback_type.lower().replace(" ", "_"),
                            page_context=page_context,
                            user_id=user_id,
                            user_email=user_email
                        )

                        if result['success']:
                            st.success(result['message'])
                            st.session_state['show_feedback_modal'] = False
                            st.rerun()
                        else:
                            st.error(result['message'])
            else:
                st.warning("Please enter your feedback before submitting")

    with col2:
        if st.button("Cancel", use_container_width=True, key="feedback_cancel_modal"):
            st.session_state['show_feedback_modal'] = False
            st.rerun()

    st.markdown("---")

# ============================================================================
# SECURITY HELPER FUNCTIONS
# ============================================================================

def extract_wait_time(error_msg: str) -> int:
    """
    Extract wait time from rate limit error message

    Args:
        error_msg: Error message like "Rate limit exceeded. You can try again in 5 minute(s)."

    Returns:
        Wait time in minutes
    """
    import re
    match = re.search(r'(\d+)\s+minute', error_msg)
    if match:
        return int(match.group(1))
    return 0

# ============================================================================
# CSV PARSING AND DATA PROCESSING
# ============================================================================

def parse_linkedin_csv(uploaded_file):
    """Parse LinkedIn CSV export and return a dataframe"""
    try:
        # LinkedIn exports often have metadata at the top, so we need to find the real headers
        uploaded_file.seek(0)

        # Read the file line by line to find where the real headers are
        lines = []
        for i, line in enumerate(uploaded_file):
            try:
                decoded_line = line.decode('utf-8', errors='ignore').strip()
                lines.append(decoded_line)
                if i >= 10:  # Only check first 10 lines
                    break
            except:
                continue

        # Find the row that looks like LinkedIn headers
        header_row = 0
        linkedin_indicators = ['first name', 'last name', 'company', 'position', 'email']

        for i, line in enumerate(lines):
            line_lower = line.lower()
            # Check if this line contains multiple LinkedIn column indicators
            matches = sum(1 for indicator in linkedin_indicators if indicator in line_lower)
            if matches >= 2:  # If we find at least 2 LinkedIn column names, this is the header
                header_row = i
                st.info(f"Found LinkedIn headers at row {i + 1}")
                break

        # Now read the CSV with the correct header row
        uploaded_file.seek(0)

        try:
            df = pd.read_csv(
                uploaded_file,
                encoding='utf-8',
                skiprows=header_row,
                on_bad_lines='skip'
            )
        except Exception:
            uploaded_file.seek(0)
            df = pd.read_csv(
                uploaded_file,
                encoding='latin-1',
                skiprows=header_row,
                on_bad_lines='skip'
            )

        if df is None or df.empty:
            raise Exception("CSV file appears to be empty or has no data rows")

        # Normalize column names
        df.columns = df.columns.str.strip().str.lower()

        # Debug: show what columns we found
        st.success(f"Loaded {len(df)} connections with columns: {', '.join(df.columns.tolist()[:10])}")

        # Map common LinkedIn column names
        column_mapping = {
            'first name': 'first_name',
            'last name': 'last_name',
            'company': 'company',
            'position': 'position',
            'title': 'position',
            'email address': 'email',
            'email': 'email',
            'connected on': 'connected_on',
            'url': 'url',
        }

        df = df.rename(columns=column_mapping)

        # Create full name if we have first and last
        if 'first_name' in df.columns and 'last_name' in df.columns:
            df['full_name'] = df['first_name'].fillna('') + ' ' + df['last_name'].fillna('')
            df['full_name'] = df['full_name'].str.strip()

        # Fill NaN values
        df = df.fillna('')

        # Validate we have at least one required column
        required_cols = ['full_name', 'first_name', 'company', 'position']
        has_required = any(col in df.columns for col in required_cols)

        if not has_required:
            raise Exception(
                f"This doesn't look like a LinkedIn Connections export.\n\n"
                f"Found columns: {', '.join(df.columns.tolist())}\n\n"
                f"Expected columns like: First Name, Last Name, Company, Position"
            )

        return df

    except Exception as e:
        st.error(f"**Error parsing CSV:** {str(e)}")

        with st.expander("📖 How to Download Your LinkedIn Connections"):
            st.markdown("""
            **Step-by-step instructions:**

            1. Go to [linkedin.com/mypreferences/d/download-my-data](https://www.linkedin.com/mypreferences/d/download-my-data)
            2. Click **"Request archive"** (not "Want something in particular?")
            3. LinkedIn will email you when ready (usually 10-15 minutes)
            4. Download and **extract the ZIP file**
            5. Inside, look for the **`Connections.csv`** file
            6. Upload that file here

            **The file should have columns like:**
            - First Name
            - Last Name
            - Company
            - Position
            - Email Address
            - Connected On

            The app will automatically skip any metadata rows at the top of the file.
            """)

        return None

def extract_search_intent(query, contacts_df):
    """Use OpenAI to intelligently match the query against the dataset using its world knowledge"""

    # Get all unique companies and positions from the dataset
    all_companies = contacts_df['company'].unique().tolist()
    all_companies = [c for c in all_companies if c]  # Remove empty strings

    all_positions = contacts_df['position'].unique().tolist()
    all_positions = [p for p in all_positions if p]  # Remove empty strings

    system_prompt = f"""You are an intelligent search assistant with deep knowledge about companies, industries, and job roles.

The user has a dataset of LinkedIn contacts with these companies:
{json.dumps(all_companies)}

And these job positions:
{json.dumps(all_positions[:20])}

The user will ask a natural language question about their network. Your job is to use YOUR KNOWLEDGE about industries, companies, and roles to identify which contacts match their query.

For example:
- If they ask "Who works in tech?", you should identify that Google, Meta, Microsoft, Amazon, Stripe, Tesla, OpenAI, Airbnb are tech companies
- If they ask "Who works in finance?", you should identify financial companies (banks, investment firms, etc.)
- If they ask "Who works in venture capital?", look for VC firms like Sequoia, a16z, Benchmark, etc.
- If they ask "Who is an engineer?", look for positions with "engineer" in the title

Return a JSON object with:
- "matching_companies": list of company names from the dataset that match the query (use your knowledge of what industry each company is in). IMPORTANT: Only include companies if the user is asking about a specific industry/company. If asking about roles/seniority, leave this EMPTY.
- "matching_position_keywords": list of keywords to search in position titles (e.g., ["engineer", "manager"])
- "matching_name_keywords": list of keywords to search in person names (only if user asks for specific person)
- "requires_ranking": boolean - set to true if user asks for "most senior", "highest level", "top", etc. - queries that require ranking people by seniority
- "ranking_criteria": if requires_ranking is true, specify "seniority" or other ranking criteria
- "limit_results": number - if user asks for "most senior person" (singular) or "top 3", specify how many results to return
- "summary": brief summary of what the user is looking for

BE INTELLIGENT:
- Use your world knowledge to categorize companies correctly
- If user asks "Who is the most senior person?", set requires_ranking=true, matching_companies=[], and focus on position_keywords for senior titles
- Don't include ALL companies when user is asking about seniority/roles

Return ONLY valid JSON, no other text."""

    try:
        response = get_client().chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        intent = json.loads(response.choices[0].message.content)
        return intent
    except Exception as e:
        error_msg = str(e)
        st.error(f"**OpenAI API Error:** {error_msg}")

        # Provide specific guidance based on error type
        if "insufficient_quota" in error_msg.lower():
            st.error("**Insufficient quota** - Your OpenAI credits have run out or billing is not set up.")
            st.info("Go to https://platform.openai.com/account/billing and add a payment method")
        elif "invalid_api_key" in error_msg.lower():
            st.error("**Invalid API key** - The API key is incorrect or expired.")
        elif "rate_limit" in error_msg.lower():
            st.warning("**Rate limit exceeded** - Too many requests. Please wait a moment and try again.")
        elif "timeout" in error_msg.lower():
            st.warning("**Request timeout** - The API took too long to respond. Try again.")
        else:
            st.error("Please check: 1) Your API key is valid, 2) You have credits/billing set up, 3) Your internet connection")
            st.info("Check your OpenAI account: https://platform.openai.com/account/billing")

        # Show full error in expander for debugging
        with st.expander("Full error details (for debugging)"):
            st.code(error_msg)

        return None

def filter_contacts(df, intent):
    """Filter contacts based on AI's intelligent matching"""

    if df.empty or not intent:
        return df

    # Start with no matches
    final_mask = pd.Series([False] * len(df))

    # Filter by matching companies (AI has used its knowledge to identify these)
    if intent.get('matching_companies'):
        for company in intent['matching_companies']:
            # Case-insensitive exact match or contains
            final_mask |= df['company'].str.lower() == company.lower()
            # Also try partial match in case of slight variations
            final_mask |= df['company'].str.lower().str.contains(company.lower(), na=False)

    # Filter by position keywords
    if intent.get('matching_position_keywords'):
        for keyword in intent['matching_position_keywords']:
            keyword_lower = keyword.lower()
            final_mask |= df['position'].str.lower().str.contains(keyword_lower, na=False)

    # Filter by name keywords (if searching for specific people)
    if intent.get('matching_name_keywords'):
        for keyword in intent['matching_name_keywords']:
            keyword_lower = keyword.lower()
            if 'full_name' in df.columns:
                final_mask |= df['full_name'].str.lower().str.contains(keyword_lower, na=False)

    # Get filtered results
    filtered_df = df[final_mask].copy()

    # Handle ranking queries (e.g., "most senior person")
    if intent.get('requires_ranking') and intent.get('ranking_criteria') == 'seniority':
        filtered_df = rank_by_seniority(filtered_df, intent.get('limit_results'))

    return filtered_df

def rank_by_seniority(df, limit=None):
    """Rank contacts by seniority level based on their job title"""

    if df.empty:
        return df

    # Define seniority scores for common titles
    seniority_keywords = {
        # C-level and founders
        'ceo': 100, 'chief executive': 100, 'founder': 100, 'co-founder': 100,
        'cto': 95, 'chief technology': 95, 'cfo': 95, 'chief financial': 95,
        'coo': 95, 'chief operating': 95, 'cmo': 95, 'chief marketing': 95,

        # Executive level
        'president': 90, 'vp': 85, 'vice president': 85, 'svp': 87, 'evp': 88,

        # Partner level (VC/Consulting)
        'general partner': 90, 'managing partner': 90, 'partner': 80,

        # Director level
        'director': 70, 'head of': 70,

        # Principal/Staff
        'principal': 65, 'staff': 60, 'distinguished': 65,

        # Senior/Lead
        'senior': 50, 'lead': 45, 'sr': 50,

        # Manager
        'manager': 40, 'engineering manager': 45,

        # Individual contributor
        'engineer': 30, 'developer': 30, 'analyst': 30, 'associate': 25,
        'designer': 30, 'scientist': 35, 'researcher': 35,
    }

    # Calculate seniority score for each contact
    def calculate_seniority_score(position):
        if pd.isna(position) or not position:
            return 0

        position_lower = position.lower()
        score = 0

        for keyword, points in seniority_keywords.items():
            if keyword in position_lower:
                score = max(score, points)  # Take highest matching score

        return score

    df['seniority_score'] = df['position'].apply(calculate_seniority_score)

    # Sort by seniority score (highest first)
    df = df.sort_values('seniority_score', ascending=False)

    # Remove the score column before returning
    result_df = df.drop('seniority_score', axis=1)

    # Limit results if specified
    if limit and limit > 0:
        result_df = result_df.head(limit)

    return result_df

def generate_summary(filtered_df, intent):
    """Generate a natural language summary of the results"""

    count = len(filtered_df)

    if count == 0:
        return "I couldn't find any contacts matching your criteria."

    # Get top companies and positions
    top_companies = filtered_df['company'].value_counts().head(3)
    top_positions = filtered_df['position'].value_counts().head(3)

    summary_parts = [f"**Found {count} contact{'s' if count != 1 else ''}**"]

    if intent.get('summary'):
        summary_parts.append(f"matching: _{intent['summary']}_")

    if not top_companies.empty and top_companies.iloc[0]:
        companies_text = ", ".join([f"{comp} ({cnt})" for comp, cnt in top_companies.items() if comp])
        if companies_text:
            summary_parts.append(f"\n\n**Top companies:** {companies_text}")

    if not top_positions.empty and top_positions.iloc[0]:
        positions_text = ", ".join([f"{pos} ({cnt})" for pos, cnt in list(top_positions.items())[:2] if pos])
        if positions_text:
            summary_parts.append(f"\n\n**Common roles:** {positions_text}")

    return "\n".join(summary_parts)

def classify_query_type(query):
    """
    Determine if a query is a SEARCH (return people) or ANALYTICS (return insights)

    Returns: "search" or "analytics"
    """
    query_lower = query.lower()

    # Analytics keywords
    analytics_keywords = [
        'how many', 'what percentage', 'what percent', 'breakdown', 'distribution',
        'summarize', 'summary', 'analyze', 'analysis', 'most common', 'least common',
        'what industry', 'which industry', 'which companies', 'top companies',
        'how diverse', 'composition', 'split between', 'ratio', 'compare'
    ]

    # Search keywords
    search_keywords = [
        'who', 'show me', 'find', 'list', 'get me', 'looking for',
        'introduce me', 'connect me', 'know anyone'
    ]

    # Check for analytics keywords
    if any(keyword in query_lower for keyword in analytics_keywords):
        return "analytics"

    # Check for search keywords
    if any(keyword in query_lower for keyword in search_keywords):
        return "search"

    # Default to search (finding people is the primary use case)
    return "search"

def analyze_network_with_ai(query, contacts_df):
    """
    Use AI to analyze the user's network and answer analytical questions

    Examples:
    - "What industry do I have most contacts in?"
    - "How many engineers vs managers?"
    - "Which companies are most represented?"
    """

    # Aggregate network data for GPT
    total_contacts = len(contacts_df)

    # Get company distribution
    company_counts = contacts_df['company'].value_counts().head(20).to_dict()

    # Get position distribution
    position_counts = contacts_df['position'].value_counts().head(20).to_dict()

    # Create summary for GPT
    network_summary = {
        "total_contacts": total_contacts,
        "top_companies": company_counts,
        "top_positions": position_counts
    }

    # Build prompt for GPT
    prompt = f"""You are analyzing a professional's LinkedIn network. Answer their question using the network data provided.

NETWORK DATA:
- Total contacts: {total_contacts}

Top Companies (with contact count):
{chr(10).join([f"  - {company}: {count} contacts" for company, count in list(company_counts.items())[:15]])}

Top Positions/Titles (with contact count):
{chr(10).join([f"  - {position}: {count} contacts" for position, count in list(position_counts.items())[:15]])}

USER'S QUESTION: {query}

Analyze the data and provide a clear, insightful answer. Use your world knowledge to:
- Categorize companies by industry (e.g., Google/Meta = Tech, Goldman Sachs = Finance)
- Identify patterns in job roles and seniority
- Provide percentages and specific numbers
- Be concise but informative

Answer:"""

    try:
        response = get_client().chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert at analyzing professional networks and providing actionable insights."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=600
        )

        answer = response.choices[0].message.content.strip()

        # Log analytics query
        analytics.log_search_query(
            query=query,
            results_count=0,  # Analytics queries don't return contacts
            intent={"type": "analytics"},
            session_id=st.session_state['session_id']
        )

        return {
            'success': True,
            'answer': answer
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def generate_personalized_emails(selected_contacts, email_purpose="🤝 Just catching up / Reconnecting", email_tone="Friendly & Casual", additional_context=""):
    """Generate personalized outreach emails for each selected contact using AI"""

    # Map email purpose to specific instructions
    purpose_instructions = {
        "🤝 Just catching up / Reconnecting": "reconnect and catch up. Keep it casual and friendly.",
        "💼 I'm looking for a job": "explore job opportunities at their company or ask for referrals. Be professional but humble.",
        "👥 I'm looking to hire": "see if they know someone who might be interested in a role at your company. Be clear about the opportunity.",
        "🚀 Pitching my startup/idea": "share your startup/project and get their feedback or support. Be concise and compelling.",
        "💡 Asking for advice/mentorship": "ask for their advice or mentorship in their area of expertise. Be respectful of their time.",
        "🔗 Making an introduction": "ask if they'd be open to being introduced to someone in your network. Explain the mutual benefit.",
        "☕ Requesting a coffee chat": "suggest a casual coffee chat to catch up and learn from their experience.",
        "📚 Seeking information/insights": "ask for information or insights about their industry, company, or role. Be specific about what you're curious about."
    }

    # Map tone to specific style instructions
    tone_instructions = {
        "Friendly & Casual": "Use a warm, friendly tone like you're texting a friend. Keep it light and conversational.",
        "Professional & Formal": "Use formal business language. Be polished and professional throughout.",
        "Enthusiastic & Energetic": "Show excitement and energy. Use exclamation points and positive language.",
        "Direct & Brief": "Be extremely concise. Get straight to the point. No fluff.",
        "Humble & Respectful": "Show deep respect for their time and expertise. Be modest and appreciative."
    }

    purpose_instruction = purpose_instructions.get(email_purpose, "reconnect and catch up")
    tone_instruction = tone_instructions.get(email_tone, "Use a warm, friendly tone")

    emails = []

    for _, row in selected_contacts.iterrows():
        name = row.get('full_name', 'Unknown')
        position = row.get('position', 'Unknown position')
        company = row.get('company', 'Unknown company')
        email = row.get('email', 'No email')

        # Build context section if additional context is provided
        context_section = ""
        if additional_context and additional_context.strip():
            context_section = f"\n\nADDITIONAL CONTEXT ABOUT OUR RELATIONSHIP:\n{additional_context.strip()}\n\nIMPORTANT: Use this context to make the email more personal and authentic. Reference specific details if they're relevant to this person."

        # Use AI to generate a personalized email
        prompt = f"""Write a personalized outreach email to this person from my LinkedIn network:

Name: {name}
Current Role: {position}
Company: {company}

EMAIL PURPOSE: {purpose_instruction}
TONE: {tone_instruction}{context_section}

The email should:
1. Be brief and conversational (2-3 short paragraphs)
2. Mention their current role/company naturally
3. Align with the stated purpose above
4. Match the specified tone perfectly
5. If additional context was provided, naturally weave in personal details to make the email more authentic
6. Include a clear call-to-action appropriate for the purpose
7. Be warm and genuine, not salesy or pushy
8. Use placeholders like [YOUR NAME] and [YOUR COMPANY/ROLE] that I can fill in

Return the email with a subject line."""

        try:
            response = get_client().chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that writes warm, personalized networking emails."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )

            email_text = response.choices[0].message.content

            # Return as dictionary for tabbed display
            emails.append({
                "name": name,
                "email": email,
                "position": position,
                "company": company,
                "email_text": email_text
            })

        except Exception as e:
            emails.append({
                "name": name,
                "email": email,
                "position": position,
                "company": company,
                "email_text": f"ERROR: {str(e)}\n\nPlease check your OpenAI API key and credits.",
                "error": True
            })

    return emails

# Authentication UI Functions
def show_login_page():
    """Display login page"""
    st.markdown("<h1 style='text-align: center; margin-top: 2rem; font-family: var(--font-serif);'>Login to 6th Degree</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: var(--text-secondary); margin-bottom: 3rem;'>Access your personalized network dashboard</p>", unsafe_allow_html=True)

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Check if user needs to verify email (show resend button outside form)
        if st.session_state.get('unverified_user'):
            user_info = st.session_state['unverified_user']

            st.warning("Please verify your email to continue. Check your inbox for the verification link.")
            st.info(f"Verification email sent to: {user_info['email']}")

            if st.button("Resend Verification Email", type="primary", use_container_width=True):
                result = security.send_verification_email(
                    user_info['id'],
                    user_info['email'],
                    user_info['full_name']
                )
                if result:
                    st.success("Verification email sent!")
                else:
                    st.error("Failed to send verification email. Please try again or contact support.")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Back to Login", use_container_width=True):
                st.session_state['unverified_user'] = None
                st.rerun()
        else:
            # === SECURITY: Generate CSRF token ===
            csrf_token = generate_csrf_token('login')
            st.session_state['login_csrf_token'] = csrf_token

            with st.form("login_form"):
                st.markdown("### Sign In")
                email = st.text_input("Email", placeholder="your@email.com")
                password = st.text_input("Password", type="password", placeholder="Enter your password")

                submit = st.form_submit_button("Login", use_container_width=True, type="primary")

                if submit:
                    # === SECURITY: Validate CSRF token ===
                    token_result = validate_csrf_token_detailed('login', st.session_state.get('login_csrf_token', ''))

                    if not token_result['valid']:
                        st.error(token_result['message'])
                        log_csrf_failure('login', email if email else 'unknown', token_result['reason'])
                        st.stop()

                    # Strip whitespace from inputs
                    email = email.strip() if email else ""
                    password = password.strip() if password else ""

                    if not email or not password:
                        st.error("Please enter both email and password")
                    else:
                        with st.spinner("Logging in..."):
                            try:
                                # Check rate limit
                                rate_limit = security.check_login_rate_limit(email)
                                if not rate_limit['allowed']:
                                    st.error(rate_limit['message'])
                                    return

                                result = auth.login_user(email, password)

                                if result['success']:
                                    # === SECURITY: Log successful login ===
                                    log_successful_login(
                                        user_id=result['user']['id'],
                                        email=email,
                                        ip='unknown'  # Streamlit doesn't expose IP easily
                                    )

                                    # Old logging for backwards compatibility
                                    security.log_login_attempt(email, True)

                                    # Check if email is verified
                                    supabase = auth.get_supabase_client()
                                    user_data = supabase.table('users').select('email_verified').eq('id', result['user']['id']).execute()

                                    if user_data.data and not user_data.data[0].get('email_verified', False):
                                        # Store unverified user info and rerun to show resend button outside form
                                        st.session_state['unverified_user'] = result['user']
                                        st.rerun()

                                    # Store user info in session
                                    st.session_state['authenticated'] = True
                                    st.session_state['user'] = result['user']

                                    # Load user's contacts from database
                                    contacts_df = auth.load_user_contacts(result['user']['id'])
                                    if contacts_df is not None:
                                        st.session_state['contacts_df'] = contacts_df

                                    st.success(f"Welcome back, {result['user']['full_name']}!")
                                    st.rerun()
                                else:
                                    # === SECURITY: Log failed login ===
                                    log_failed_login(
                                        email=email,
                                        ip='unknown',  # Streamlit doesn't expose IP easily
                                        reason=result['message']
                                    )

                                    # Old logging for backwards compatibility
                                    security.log_login_attempt(email, False)

                                    st.error(result['message'])
                                    if rate_limit.get('remaining_attempts'):
                                        st.caption(f"Remaining attempts: {rate_limit['remaining_attempts']}")
                            except Exception as e:
                                st.error(f"Login failed: {str(e)}")
                                with st.expander("Technical Details"):
                                    st.code(str(e))
                                    st.caption("If this error persists, please contact support.")

        # Forgot password link
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Forgot Password?", use_container_width=True, type="secondary"):
                st.session_state['show_forgot_password'] = True
                st.rerun()
        with col2:
            pass  # Empty column for spacing

        st.markdown("---")
        st.markdown("<p style='text-align: center;'>Don't have an account?</p>", unsafe_allow_html=True)

        if st.button("Create New Account", use_container_width=True):
            st.session_state['show_register'] = True
            st.rerun()

def show_forgot_password_page():
    """Display forgot password page"""
    st.markdown("<h1 style='text-align: center; margin-top: 2rem; font-family: var(--font-serif);'>Reset Your Password</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: var(--text-secondary); margin-bottom: 3rem;'>Enter your email to receive a password reset link</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # === SECURITY: Generate CSRF token ===
        csrf_token = generate_csrf_token('forgot_password')
        st.session_state['forgot_password_csrf_token'] = csrf_token

        with st.form("forgot_password_form"):
            st.markdown("### Password Reset")
            email = st.text_input("Email Address", placeholder="your@email.com")

            submit = st.form_submit_button("Send Reset Link", use_container_width=True, type="primary")

            if submit:
                # === SECURITY: Validate CSRF token ===
                token_result = validate_csrf_token_detailed('forgot_password', st.session_state.get('forgot_password_csrf_token', ''))

                if not token_result['valid']:
                    st.error(token_result['message'])
                    log_csrf_failure('forgot_password', email if email else 'unknown', token_result['reason'])
                    st.stop()

                email = email.strip() if email else ""

                if not email:
                    st.error("Please enter your email address")
                else:
                    with st.spinner("Sending reset link..."):
                        result = security.request_password_reset(email)
                        st.success(result['message'])
                        st.info("If the email exists in our system, you'll receive a reset link shortly. Please check your inbox (and spam folder).")

        st.markdown("---")

        if st.button("Back to Login", use_container_width=True):
            st.session_state['show_forgot_password'] = False
            st.rerun()


def show_password_reset_form(token):
    """Display password reset form (when user clicks email link)"""
    st.markdown("<h1 style='text-align: center; margin-top: 2rem; font-family: var(--font-serif);'>Set New Password</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: var(--text-secondary); margin-bottom: 3rem;'>Create a strong new password</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Check if password was already reset successfully
        if st.session_state.get('password_reset_success'):
            st.success("Password reset successful!")
            st.info("You can now log in with your new password.")

            if st.button("Go to Login", type="primary", use_container_width=True):
                st.session_state['password_reset_success'] = False
                st.session_state['show_register'] = False
                st.session_state['show_login'] = True
                st.query_params.clear()
                st.rerun()
        else:
            # === SECURITY: Generate CSRF token ===
            csrf_token = generate_csrf_token('reset_password')
            st.session_state['reset_password_csrf_token'] = csrf_token

            with st.form("reset_password_form"):
                st.markdown("### New Password")

                new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter new password")

                submit = st.form_submit_button("Reset Password", use_container_width=True, type="primary")

                if submit:
                    # === SECURITY: Validate CSRF token ===
                    token_result = validate_csrf_token_detailed('reset_password', st.session_state.get('reset_password_csrf_token', ''))

                    if not token_result['valid']:
                        st.error(token_result['message'])
                        log_csrf_failure('reset_password', 'password_reset_user', token_result['reason'])
                        st.stop()

                    new_password = new_password.strip() if new_password else ""
                    confirm_password = confirm_password.strip() if confirm_password else ""

                    if not new_password or not confirm_password:
                        st.error("Please fill in all fields")
                    elif new_password != confirm_password:
                        st.error("Passwords don't match")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters")
                    else:
                        # Check password strength
                        strength = security.check_password_strength(new_password)
                        if not strength['strong']:
                            st.warning(strength['message'])

                        with st.spinner("Resetting password..."):
                            result = security.reset_password_with_token(token, new_password)

                            if result['success']:
                                st.session_state['password_reset_success'] = True
                                st.rerun()
                            else:
                                st.error(result['message'])


def show_profile_page():
    """Display user profile page with view and edit functionality"""

    # Get user ID
    user_id = st.session_state.get('user', {}).get('id')

    if not user_id or user_id == 'anonymous':
        st.warning("Please log in to view your profile")
        return

    # Get current profile
    user_profile_data = user_profile.get_profile(user_id)

    if not user_profile_data:
        st.error("Profile not found. Please complete onboarding.")
        return

    # Parse JSON fields
    import json
    goals = user_profile_data.get('goals', [])
    if isinstance(goals, str):
        goals = json.loads(goals)

    interests = user_profile_data.get('interests', [])
    if isinstance(interests, str):
        interests = json.loads(interests)

    seeking_connections = user_profile_data.get('seeking_connections', [])
    if isinstance(seeking_connections, str):
        seeking_connections = json.loads(seeking_connections)

    privacy_settings = user_profile_data.get('privacy_settings', {})
    if isinstance(privacy_settings, str):
        privacy_settings = json.loads(privacy_settings)

    # Header with Back to Dashboard button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("<h1 class='hero-title' style='font-family: var(--font-serif); font-size: 3rem; font-weight: 700; margin-bottom: var(--space-2);'>My Profile</h1>", unsafe_allow_html=True)
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Back to Dashboard", key="profile_back_dashboard"):
            st.session_state['show_profile'] = False
            st.rerun()

    st.markdown("<hr style='margin: var(--space-6) 0; border: none; border-top: 1px solid var(--border-light);'>", unsafe_allow_html=True)

    # Check if in edit mode
    edit_mode = st.session_state.get('profile_edit_mode', False)

    if not edit_mode:
        # ============================================
        # VIEW MODE
        # ============================================

        # Edit Profile button
        if st.button("Edit Profile", type="primary", key="profile_edit_btn"):
            st.session_state['profile_edit_mode'] = True
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # Display profile fields in cards
        st.markdown("### Professional Information")

        # Current Role
        visibility_icon = "" if privacy_settings.get('current_role', True) else "🔒"
        st.markdown(f"""
<div class='card' style='padding: var(--space-5); margin-bottom: var(--space-4);'>
    <p style='font-size: 0.875rem; color: var(--text-tertiary); margin: 0 0 var(--space-1) 0;'>Current Role {visibility_icon}</p>
    <p style='font-size: 1.125rem; font-weight: 600; color: var(--text-primary); margin: 0;'>{user_profile_data.get('current_role', 'N/A')}</p>
</div>
""", unsafe_allow_html=True)

        # Current Company
        visibility_icon = "" if privacy_settings.get('current_company', True) else "🔒"
        st.markdown(f"""
<div class='card' style='padding: var(--space-5); margin-bottom: var(--space-4);'>
    <p style='font-size: 0.875rem; color: var(--text-tertiary); margin: 0 0 var(--space-1) 0;'>Current Company {visibility_icon}</p>
    <p style='font-size: 1.125rem; font-weight: 600; color: var(--text-primary); margin: 0;'>{user_profile_data.get('current_company', 'N/A')}</p>
</div>
""", unsafe_allow_html=True)

        # Industry
        visibility_icon = "" if privacy_settings.get('industry', True) else "🔒"
        st.markdown(f"""
<div class='card' style='padding: var(--space-5); margin-bottom: var(--space-4);'>
    <p style='font-size: 0.875rem; color: var(--text-tertiary); margin: 0 0 var(--space-1) 0;'>Industry {visibility_icon}</p>
    <p style='font-size: 1.125rem; font-weight: 600; color: var(--text-primary); margin: 0;'>{user_profile_data.get('industry', 'N/A')}</p>
</div>
""", unsafe_allow_html=True)

        # Company Stage (if provided)
        if user_profile_data.get('company_stage'):
            visibility_icon = "" if privacy_settings.get('company_stage', True) else "🔒"
            st.markdown(f"""
<div class='card' style='padding: var(--space-5); margin-bottom: var(--space-4);'>
    <p style='font-size: 0.875rem; color: var(--text-tertiary); margin: 0 0 var(--space-1) 0;'>Company Stage {visibility_icon}</p>
    <p style='font-size: 1.125rem; font-weight: 600; color: var(--text-primary); margin: 0;'>{user_profile_data.get('company_stage')}</p>
</div>
""", unsafe_allow_html=True)

        # Location
        visibility_icon_city = "🔓" if privacy_settings.get('location_city', True) else "🔒"
        visibility_icon_country = "🔓" if privacy_settings.get('location_country', True) else "🔒"
        location_str = user_profile_data.get('location_city', 'N/A')
        if user_profile_data.get('location_country'):
            location_str += f", {user_profile_data.get('location_country')}"
        st.markdown(f"""
<div class='card' style='padding: var(--space-5); margin-bottom: var(--space-4);'>
    <p style='font-size: 0.875rem; color: var(--text-tertiary); margin: 0 0 var(--space-1) 0;'>Location {visibility_icon_city}</p>
    <p style='font-size: 1.125rem; font-weight: 600; color: var(--text-primary); margin: 0;'>{location_str}</p>
</div>
""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Goals & Interests")

        # Goals
        if goals:
            visibility_icon = "" if privacy_settings.get('goals', False) else "🔒"
            goals_str = ", ".join(goals) if goals else "None specified"
            st.markdown(f"""
<div class='card' style='padding: var(--space-5); margin-bottom: var(--space-4);'>
    <p style='font-size: 0.875rem; color: var(--text-tertiary); margin: 0 0 var(--space-1) 0;'>Goals {visibility_icon}</p>
    <p style='font-size: 1rem; color: var(--text-primary); margin: 0;'>{goals_str}</p>
</div>
""", unsafe_allow_html=True)

        # Interests
        if interests:
            visibility_icon = "" if privacy_settings.get('interests', True) else "🔒"
            interests_str = ", ".join(interests) if interests else "None specified"
            st.markdown(f"""
<div class='card' style='padding: var(--space-5); margin-bottom: var(--space-4);'>
    <p style='font-size: 0.875rem; color: var(--text-tertiary); margin: 0 0 var(--space-1) 0;'>Interests {visibility_icon}</p>
    <p style='font-size: 1rem; color: var(--text-primary); margin: 0;'>{interests_str}</p>
</div>
""", unsafe_allow_html=True)

        # Seeking Connections
        if seeking_connections:
            visibility_icon = "" if privacy_settings.get('seeking_connections', True) else "🔒"
            seeking_str = ", ".join(seeking_connections) if seeking_connections else "None specified"
            st.markdown(f"""
<div class='card' style='padding: var(--space-5); margin-bottom: var(--space-4);'>
    <p style='font-size: 0.875rem; color: var(--text-tertiary); margin: 0 0 var(--space-1) 0;'>Seeking Connections {visibility_icon}</p>
    <p style='font-size: 1rem; color: var(--text-primary); margin: 0;'>{seeking_str}</p>
</div>
""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 0.875rem; color: var(--text-tertiary);'>🔒 = Private (not visible to others)</p>", unsafe_allow_html=True)

    else:
        # ============================================
        # EDIT MODE
        # ============================================

        st.markdown("<h2 style='font-family: var(--font-serif); font-size: 2rem; font-weight: 600; margin-bottom: var(--space-6);'>Edit Profile</h2>", unsafe_allow_html=True)

        # === SECURITY: Generate CSRF token ===
        csrf_token = generate_csrf_token('edit_profile')
        st.session_state['edit_profile_csrf_token'] = csrf_token

        with st.form("edit_profile_form"):
            st.markdown("### Professional Information")

            # Current Role
            col1, col2 = st.columns([3, 1])
            with col1:
                new_current_role = st.text_input("Current Role", value=user_profile_data.get('current_role', ''), help="Your job title")
            with col2:
                st.markdown("<p style='font-size: 0.875rem; color: var(--text-tertiary); margin-top: 2rem;'>Visibility</p>", unsafe_allow_html=True)
                role_visible = st.checkbox("Public", value=privacy_settings.get('current_role', True), key="privacy_role")

            # Current Company
            col1, col2 = st.columns([3, 1])
            with col1:
                new_current_company = st.text_input("Current Company", value=user_profile_data.get('current_company', ''), help="Your company")
            with col2:
                st.markdown("<p style='font-size: 0.875rem; color: var(--text-tertiary); margin-top: 2rem;'>Visibility</p>", unsafe_allow_html=True)
                company_visible = st.checkbox("Public", value=privacy_settings.get('current_company', True), key="privacy_company")

            # Industry
            col1, col2 = st.columns([3, 1])
            with col1:
                current_industry_index = 0
                if user_profile_data.get('industry') in user_profile.INDUSTRY_OPTIONS:
                    current_industry_index = user_profile.INDUSTRY_OPTIONS.index(user_profile_data.get('industry'))
                new_industry = st.selectbox("Industry", options=user_profile.INDUSTRY_OPTIONS, index=current_industry_index)
            with col2:
                st.markdown("<p style='font-size: 0.875rem; color: var(--text-tertiary); margin-top: 2rem;'>Visibility</p>", unsafe_allow_html=True)
                industry_visible = st.checkbox("Public", value=privacy_settings.get('industry', True), key="privacy_industry")

            # Company Stage
            col1, col2 = st.columns([3, 1])
            with col1:
                current_stage_index = 0
                all_stage_options = [''] + user_profile.COMPANY_STAGE_OPTIONS
                if user_profile_data.get('company_stage') in user_profile.COMPANY_STAGE_OPTIONS:
                    current_stage_index = all_stage_options.index(user_profile_data.get('company_stage'))
                new_company_stage = st.selectbox("Company Stage (Optional)", options=all_stage_options, index=current_stage_index)
            with col2:
                st.markdown("<p style='font-size: 0.875rem; color: var(--text-tertiary); margin-top: 2rem;'>Visibility</p>", unsafe_allow_html=True)
                stage_visible = st.checkbox("Public", value=privacy_settings.get('company_stage', True), key="privacy_stage")

            # Location
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                new_location_city = st.text_input("City", value=user_profile_data.get('location_city', ''))
            with col2:
                new_location_country = st.text_input("Country", value=user_profile_data.get('location_country', ''))
            with col3:
                st.markdown("<p style='font-size: 0.875rem; color: var(--text-tertiary); margin-top: 2rem;'>Visibility</p>", unsafe_allow_html=True)
                location_visible = st.checkbox("Public", value=privacy_settings.get('location_city', True), key="privacy_location")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### Goals & Interests")

            # Goals
            col1, col2 = st.columns([3, 1])
            with col1:
                new_goals = st.multiselect("Goals (Optional)", options=user_profile.GOAL_OPTIONS, default=goals)
            with col2:
                st.markdown("<p style='font-size: 0.875rem; color: var(--text-tertiary); margin-top: 2rem;'>Visibility</p>", unsafe_allow_html=True)
                goals_visible = st.checkbox("Public", value=privacy_settings.get('goals', False), key="privacy_goals")

            # Interests
            col1, col2 = st.columns([3, 1])
            with col1:
                new_interests = st.multiselect("Interests (Optional)", options=user_profile.INTEREST_OPTIONS, default=interests)
            with col2:
                st.markdown("<p style='font-size: 0.875rem; color: var(--text-tertiary); margin-top: 2rem;'>Visibility</p>", unsafe_allow_html=True)
                interests_visible = st.checkbox("Public", value=privacy_settings.get('interests', True), key="privacy_interests")

            # Seeking Connections
            col1, col2 = st.columns([3, 1])
            with col1:
                new_seeking_connections = st.multiselect("Seeking Connections (Optional)", options=user_profile.CONNECTION_TYPE_OPTIONS, default=seeking_connections)
            with col2:
                st.markdown("<p style='font-size: 0.875rem; color: var(--text-tertiary); margin-top: 2rem;'>Visibility</p>", unsafe_allow_html=True)
                seeking_visible = st.checkbox("Public", value=privacy_settings.get('seeking_connections', True), key="privacy_seeking")

            st.markdown("<br>", unsafe_allow_html=True)

            # Form buttons
            col1, col2 = st.columns(2)
            with col1:
                save_button = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
            with col2:
                cancel_button = st.form_submit_button("Cancel", use_container_width=True)

            if cancel_button:
                st.session_state['profile_edit_mode'] = False
                st.rerun()

            if save_button:
                # === SECURITY: Validate CSRF token ===
                token_result = validate_csrf_token_detailed('edit_profile', st.session_state.get('edit_profile_csrf_token', ''))

                if not token_result['valid']:
                    st.error(token_result['message'])
                    log_csrf_failure('edit_profile', user_id, token_result['reason'])
                    st.stop()

                # Validate required fields
                if not new_current_role or not new_current_company or not new_location_city:
                    st.error("Please fill in all required fields (Role, Company, City)")
                else:
                    # Build updates dict
                    updates = {
                        'current_role': new_current_role,
                        'current_company': new_current_company,
                        'industry': new_industry,
                        'location_city': new_location_city,
                        'goals': new_goals,
                        'interests': new_interests,
                        'seeking_connections': new_seeking_connections,
                        'privacy_settings': {
                            'current_role': role_visible,
                            'current_company': company_visible,
                            'industry': industry_visible,
                            'company_stage': stage_visible,
                            'location_city': location_visible,
                            'location_country': location_visible,
                            'goals': goals_visible,
                            'interests': interests_visible,
                            'seeking_connections': seeking_visible
                        }
                    }

                    # Add optional fields
                    if new_company_stage:
                        updates['company_stage'] = new_company_stage
                    if new_location_country:
                        updates['location_country'] = new_location_country

                    # Update profile
                    result = user_profile.update_profile(user_id, updates)

                    if result['success']:
                        st.success("Profile updated successfully!")
                        st.session_state['profile_edit_mode'] = False
                        st.rerun()
                    else:
                        st.error(f"Failed to update profile: {result['message']}")


def show_connections_page():
    """Display Connections page with 3 tabs: My Connections, Find People, Requests"""

    # Get user ID
    user_id = st.session_state.get('user', {}).get('id')

    if not user_id:
        st.warning("Please log in to use Connections features")
        return

    # Hero heading
    st.markdown("<h1 class='hero-title' style='font-family: var(--font-serif); font-size: 3rem; font-weight: 700; margin-bottom: var(--space-8);'>Connections</h1>", unsafe_allow_html=True)

    # Get pending requests count for badge
    pending_requests = collaboration.get_pending_connection_requests(user_id)
    pending_count = len(pending_requests)

    # Create tabs
    tab_labels = ["My Connections", "Find People", f"Requests ({pending_count})" if pending_count > 0 else "Requests"]
    tabs = st.tabs(tab_labels)

    # ============================================
    # TAB 1: MY CONNECTIONS
    # ============================================
    with tabs[0]:
        st.markdown("<br>", unsafe_allow_html=True)

        connections = collaboration.get_user_connections(user_id, status='accepted')

        if not connections:
            # Empty state
            st.markdown("""
<div class='card' style='text-align: center; padding: var(--space-10); margin: var(--space-6) auto; max-width: 600px;'>
<h2 style='font-family: var(--font-serif); font-size: 1.875rem; font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-4);'>Build Your Network</h2>
<p style='color: var(--text-secondary); font-size: 1.0625rem; line-height: 1.6; margin-bottom: var(--space-2);'>Connect with other users to:</p>
<ul style='text-align: left; color: var(--text-secondary); font-size: 1rem; line-height: 1.8; margin: var(--space-4) auto; max-width: 400px;'>
<li>Search their LinkedIn networks</li>
<li>Request warm introductions</li>
<li>Expand your professional reach</li>
</ul>
</div>
""", unsafe_allow_html=True)

            if st.button("Find People to Connect", type="primary", use_container_width=False):
                st.session_state['connections_active_tab'] = 1
                st.rerun()
        else:
            st.markdown(f"<p style='color: var(--text-secondary); margin-bottom: var(--space-6);'>You have {len(connections)} connection(s)</p>", unsafe_allow_html=True)

            # Display connections
            for conn in connections:
                col1, col2 = st.columns([3, 1])

                with col1:
                    # Connection card
                    contact_count = collaboration.get_user_contact_count(conn['user_id'])
                    sharing_badge = "✓ Sharing network" if conn['network_sharing_enabled'] else "Not sharing"
                    sharing_color = "#10b981" if conn['network_sharing_enabled'] else "#6b7280"

                    # === SECURITY: Sanitize user-generated content ===
                    safe_full_name = sanitize_html(conn['full_name'])
                    safe_organization = sanitize_html(conn.get('organization', 'No organization'))
                    safe_email = sanitize_html(conn['email'])

                    st.markdown(f"""
<div class='card' style='padding: var(--space-5); margin-bottom: var(--space-4);'>
<h3 style='font-size: 1.125rem; font-weight: 600; color: var(--text-primary); margin: 0 0 var(--space-2) 0;'>{safe_full_name}</h3>
<p style='font-size: 0.9375rem; color: var(--text-secondary); margin: 0 0 var(--space-1) 0;'>{safe_organization}</p>
<p style='font-size: 0.875rem; color: var(--text-tertiary); margin: 0 0 var(--space-3) 0;'>{safe_email}</p>
<div style='display: flex; gap: var(--space-4); align-items: center;'>
<span style='font-size: 0.875rem; color: var(--text-tertiary);'>{contact_count:,} contacts</span>
<span style='font-size: 0.875rem; color: {sharing_color};'>{sharing_badge}</span>
</div>
</div>
""", unsafe_allow_html=True)

                with col2:
                    st.markdown("<br>", unsafe_allow_html=True)

                    # Toggle network sharing
                    new_sharing = st.toggle(
                        "Share network",
                        value=conn['network_sharing_enabled'],
                        key=f"sharing_{conn['connection_id']}"
                    )

                    if new_sharing != conn['network_sharing_enabled']:
                        result = collaboration.update_network_sharing(conn['connection_id'], new_sharing)
                        if result['success']:
                            st.success("Updated")
                            st.rerun()

    # ============================================
    # TAB 2: FIND PEOPLE
    # ============================================
    with tabs[1]:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<p style='color: var(--text-secondary); margin-bottom: var(--space-6);'>Search for other 6th Degree users and send connection requests</p>", unsafe_allow_html=True)

        # Search form
        search_query = st.text_input(
            "Search by name or organization",
            placeholder='e.g., "John Smith" or "Acme Inc"',
            key="connections_search_query"
        )

        if search_query and len(search_query) >= 2:
            results = collaboration.search_users(search_query, user_id)

            if not results:
                st.info("No users found matching your search")
            else:
                st.markdown(f"<p style='color: var(--text-secondary); margin: var(--space-4) 0;'>Found {len(results)} user(s)</p>", unsafe_allow_html=True)

                # Get user's existing connections and pending requests to show status
                existing_connections = collaboration.get_user_connections(user_id, status='all')
                sent_requests = collaboration.get_sent_connection_requests(user_id, status='pending')

                # Create sets for quick lookup
                connected_ids = {c['user_id'] for c in existing_connections}
                pending_ids = {r['target_user_id'] for r in sent_requests}

                for result in results:
                    result_user_id = result['id']
                    contact_count = collaboration.get_user_contact_count(result_user_id)

                    # Determine connection status
                    if result_user_id in connected_ids:
                        status_text = "Connected ✓"
                        status_color = "#10b981"
                        show_button = False
                    elif result_user_id in pending_ids:
                        status_text = "Pending"
                        status_color = "#fbbf24"
                        show_button = False
                    else:
                        status_text = None
                        show_button = True

                    col1, col2 = st.columns([3, 1])

                    with col1:
                        # === SECURITY: Sanitize user-generated content ===
                        safe_result_name = sanitize_html(result['full_name'])
                        safe_result_org = sanitize_html(result.get('organization', 'No organization'))
                        safe_result_email = sanitize_html(result['email'])

                        st.markdown(f"""
<div class='card' style='padding: var(--space-5); margin-bottom: var(--space-4);'>
<h3 style='font-size: 1.125rem; font-weight: 600; color: var(--text-primary); margin: 0 0 var(--space-2) 0;'>{safe_result_name}</h3>
<p style='font-size: 0.9375rem; color: var(--text-secondary); margin: 0 0 var(--space-1) 0;'>{safe_result_org}</p>
<p style='font-size: 0.875rem; color: var(--text-tertiary); margin: 0 0 var(--space-3) 0;'>{safe_result_email}</p>
<span style='font-size: 0.875rem; color: var(--text-tertiary);'>{contact_count:,} contacts</span>
</div>
""", unsafe_allow_html=True)

                    with col2:
                        st.markdown("<br>", unsafe_allow_html=True)

                        if status_text:
                            st.markdown(f"<p style='font-size: 0.9375rem; color: {status_color}; font-weight: 600; padding: 0.5rem 0;'>{status_text}</p>", unsafe_allow_html=True)
                        elif show_button:
                            if st.button("Connect", key=f"connect_{result_user_id}", type="primary"):
                                # Show modal for connection request
                                st.session_state[f'show_connect_modal_{result_user_id}'] = True
                                st.rerun()

                    # Connection request modal
                    if st.session_state.get(f'show_connect_modal_{result_user_id}'):
                        with st.form(key=f"connect_form_{result_user_id}"):
                            st.markdown(f"### Send Connection Request to {result['full_name']}")

                            request_message = st.text_area(
                                "Personal message (optional)",
                                placeholder="Hey! I'd love to connect and expand our networks...",
                                height=100,
                                key=f"msg_{result_user_id}"
                            )

                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("Send Request", type="primary", use_container_width=True):
                                    # === SECURITY: Rate Limiting ===
                                    allowed, error_msg = check_rate_limit(user_id, 'connection_request')

                                    if not allowed:
                                        st.error(error_msg)
                                        log_rate_limit(user_id, 'connection_request', extract_wait_time(error_msg))
                                    else:
                                        result_send = collaboration.send_connection_request(
                                            user_id,
                                            result_user_id,
                                            request_message if request_message.strip() else None
                                        )

                                        if result_send['success']:
                                            st.success(result_send['message'])
                                            st.session_state[f'show_connect_modal_{result_user_id}'] = False
                                            st.rerun()
                                        else:
                                            st.error(result_send['message'])

                            with col2:
                                if st.form_submit_button("Cancel", use_container_width=True):
                                    st.session_state[f'show_connect_modal_{result_user_id}'] = False
                                    st.rerun()

    # ============================================
    # TAB 3: REQUESTS
    # ============================================
    with tabs[2]:
        st.markdown("<br>", unsafe_allow_html=True)

        if not pending_requests:
            # Empty state
            st.markdown("""
<div class='card' style='text-align: center; padding: var(--space-10); margin: var(--space-6) auto; max-width: 600px;'>
<h2 style='font-family: var(--font-serif); font-size: 1.875rem; font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-4);'>No Pending Requests</h2>
<p style='color: var(--text-secondary); font-size: 1.0625rem;'>You don't have any pending connection requests at the moment.</p>
</div>
""", unsafe_allow_html=True)
        else:
            st.markdown(f"<p style='color: var(--text-secondary); margin-bottom: var(--space-6);'>You have {len(pending_requests)} pending request(s)</p>", unsafe_allow_html=True)

            for req in pending_requests:
                contact_count = collaboration.get_user_contact_count(req['requester_id'])

                # Request card
                st.markdown(f"""
<div class='card' style='padding: var(--space-5); margin-bottom: var(--space-4);'>
<h3 style='font-size: 1.125rem; font-weight: 600; color: var(--text-primary); margin: 0 0 var(--space-2) 0;'>{req['requester_name']} wants to connect</h3>
<p style='font-size: 0.9375rem; color: var(--text-secondary); margin: 0 0 var(--space-1) 0;'>{req.get('requester_organization', 'No organization')}</p>
<p style='font-size: 0.875rem; color: var(--text-tertiary); margin: 0 0 var(--space-3) 0;'>{req['requester_email']}</p>
<span style='font-size: 0.875rem; color: var(--text-tertiary);'>{contact_count:,} contacts</span>
</div>
""", unsafe_allow_html=True)

                # Show message if exists
                if req.get('request_message'):
                    st.markdown(f"""
<div style='padding: var(--space-4); background: var(--bg-tertiary); border-left: 3px solid var(--primary); border-radius: var(--radius-md); margin-bottom: var(--space-4);'>
<p style='font-size: 0.9375rem; color: var(--text-secondary); margin: 0; font-style: italic;'>"{req['request_message']}"</p>
</div>
""", unsafe_allow_html=True)

                # Action buttons
                col1, col2, col3 = st.columns([1, 1, 2])

                with col1:
                    if st.button("Accept", key=f"accept_{req['connection_id']}", type="primary", use_container_width=True):
                        st.session_state[f'show_accept_modal_{req["connection_id"]}'] = True
                        st.rerun()

                with col2:
                    if st.button("Decline", key=f"decline_{req['connection_id']}", use_container_width=True):
                        result = collaboration.decline_connection_request(req['connection_id'])
                        if result['success']:
                            st.success("Request declined")
                            st.rerun()
                        else:
                            st.error(result['message'])

                # Accept modal
                if st.session_state.get(f'show_accept_modal_{req["connection_id"]}'):
                    with st.form(key=f"accept_form_{req['connection_id']}"):
                        st.markdown(f"### Accept Connection from {req['requester_name']}")

                        share_network = st.checkbox(
                            "Share my network with this connection",
                            value=True,
                            help="Allow them to search your LinkedIn contacts for introductions"
                        )

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Confirm Accept", type="primary", use_container_width=True):
                                result = collaboration.accept_connection_request(req['connection_id'], share_network)

                                if result['success']:
                                    st.success(result['message'])
                                    st.session_state[f'show_accept_modal_{req["connection_id"]}'] = False
                                    st.rerun()
                                else:
                                    st.error(result['message'])

                        with col2:
                            if st.form_submit_button("Cancel", use_container_width=True):
                                st.session_state[f'show_accept_modal_{req["connection_id"]}'] = False
                                st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)


def show_register_page():
    """Display registration page"""
    st.markdown("<h1 style='text-align: center; margin-top: 2rem;'>📝 Create Your Account</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666; margin-bottom: 3rem;'>Join LinkedIn Network Assistant today</p>", unsafe_allow_html=True)

    # Center the registration form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # === SECURITY: Generate CSRF token ===
        csrf_token = generate_csrf_token('registration')
        st.session_state['registration_csrf_token'] = csrf_token

        with st.form("register_form"):
            st.markdown("### Create Account")
            full_name = st.text_input("Full Name", placeholder="John Doe")
            organization = st.text_input("Organization (Optional)", placeholder="e.g., Acme Inc, Stanford University")
            email = st.text_input("Email", placeholder="your@email.com")
            password = st.text_input("Password", type="password", placeholder="Create a strong password")
            password_confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter your password")

            submit = st.form_submit_button("Create Account", use_container_width=True, type="primary")

            if submit:
                # === SECURITY: Validate CSRF token ===
                token_result = validate_csrf_token_detailed('registration', st.session_state.get('registration_csrf_token', ''))

                if not token_result['valid']:
                    st.error(token_result['message'])
                    log_csrf_failure('registration', email if email else 'unknown', token_result['reason'])
                    st.stop()

                # Strip whitespace from all inputs
                full_name = full_name.strip() if full_name else ""
                organization = organization.strip() if organization else None
                email = email.strip() if email else ""
                password = password.strip() if password else ""
                password_confirm = password_confirm.strip() if password_confirm else ""

                # Validation
                if not all([full_name, email, password, password_confirm]):
                    st.error("Please fill in all required fields")
                elif password != password_confirm:
                    st.error("Passwords don't match")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    # Check password strength
                    strength = security.check_password_strength(password)
                    if not strength['strong']:
                        st.error(strength['message'])
                        return

                    with st.spinner("Creating your account..."):
                        try:
                            result = auth.register_user(email, password, full_name, organization)

                            if result['success']:
                                user_id = result['user']['id']
                                user_email = result['user']['email']
                                user_name = result['user']['full_name']

                                # Send verification email
                                email_sent = security.send_verification_email(user_id, user_email, user_name)

                                st.success(result['message'])

                                if email_sent:
                                    st.info("Verification email sent! Please check your inbox and click the verification link to activate your account.")
                                else:
                                    st.warning("Account created but verification email could not be sent. You can still log in, but some features may be limited.")

                                st.session_state['show_register'] = False
                                # Wait a moment then redirect to login
                                import time
                                time.sleep(3)
                                st.rerun()
                            else:
                                st.error(result['message'])
                        except Exception as e:
                            st.error(f"Registration failed: {str(e)}")
                            with st.expander("Technical Details"):
                                st.code(str(e))
                                st.caption("If this error persists, please contact support.")

        st.markdown("---")
        st.markdown("<p style='text-align: center;'>Already have an account?</p>", unsafe_allow_html=True)

        if st.button("Back to Login", use_container_width=True):
            st.session_state['show_register'] = False
            st.rerun()


def show_profile_onboarding(user_id: str):
    """
    Show profile onboarding modal (blocking - required to complete)
    7 questions about user's professional info and goals
    """
    st.markdown("""
<div style='max-width: 700px; margin: 2rem auto; padding: 2rem;'>
<h1 style='font-family: var(--font-serif); font-size: 2.5rem; text-align: center; margin-bottom: 1rem;'>Complete Your Profile</h1>
<p style='text-align: center; color: var(--text-secondary); font-size: 1.125rem; margin-bottom: 2rem;'>Help us personalize your experience</p>
</div>
""", unsafe_allow_html=True)

    # === SECURITY: Generate CSRF token ===
    csrf_token = generate_csrf_token('profile_onboarding')
    st.session_state['profile_onboarding_csrf_token'] = csrf_token

    with st.form("profile_onboarding_form"):
        st.markdown("<div style='max-width: 700px; margin: 0 auto;'>", unsafe_allow_html=True)

        # Question 1: Current Role (required)
        st.markdown("### 1. What's your current role?")
        current_role = st.text_input(
            "Current Role",
            placeholder="e.g., Product Manager, Software Engineer, CEO",
            help="Your job title or role",
            label_visibility="collapsed"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Question 2: Current Company (required)
        st.markdown("### 2. What company do you work at?")
        current_company = st.text_input(
            "Current Company",
            placeholder="e.g., Google, Stripe, your startup name",
            help="Your current company or organization",
            label_visibility="collapsed"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Question 3: Industry (required)
        st.markdown("### 3. Which industry are you in?")
        industry = st.selectbox(
            "Industry",
            options=user_profile.INDUSTRY_OPTIONS,
            label_visibility="collapsed"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Question 4: Company Stage (optional)
        st.markdown("### 4. What's your company stage? (Optional)")
        company_stage = st.selectbox(
            "Company Stage",
            options=[''] + user_profile.COMPANY_STAGE_OPTIONS,
            label_visibility="collapsed"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Question 5: Location (required)
        st.markdown("### 5. Where are you based?")
        col1, col2 = st.columns([2, 1])
        with col1:
            location_city = st.text_input(
                "City",
                placeholder="e.g., San Francisco, New York, London",
                help="Your city or metro area",
                label_visibility="collapsed"
            )
        with col2:
            location_country = st.text_input(
                "Country",
                placeholder="e.g., USA, UK",
                help="Optional: Your country",
                label_visibility="collapsed"
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Question 6: Goals (optional, multi-select)
        st.markdown("### 6. What are your main goals? (Optional)")
        st.caption("Select all that apply")
        goals = st.multiselect(
            "Goals",
            options=user_profile.GOAL_OPTIONS,
            label_visibility="collapsed"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Question 7: Interests (optional, multi-select)
        st.markdown("### 7. What topics are you interested in? (Optional)")
        st.caption("Select all that apply")
        interests = st.multiselect(
            "Interests",
            options=user_profile.INTEREST_OPTIONS,
            label_visibility="collapsed"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Question 8: Seeking Connections (optional, multi-select)
        st.markdown("### 8. Who are you most interested in connecting with? (Optional)")
        st.caption("Select all that apply")
        seeking_connections = st.multiselect(
            "Seeking Connections",
            options=user_profile.CONNECTION_TYPE_OPTIONS,
            label_visibility="collapsed"
        )

        st.markdown("</div>", unsafe_allow_html=True)

        # Submit button
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Complete Profile", use_container_width=True, type="primary")

        if submitted:
            # === SECURITY: Validate CSRF token ===
            token_result = validate_csrf_token_detailed('profile_onboarding', st.session_state.get('profile_onboarding_csrf_token', ''))

            if not token_result['valid']:
                st.error(token_result['message'])
                log_csrf_failure('profile_onboarding', user_id, token_result['reason'])
                st.stop()

            # Validate required fields
            if not current_role or not current_company or not location_city:
                st.error("Please fill in all required fields (Role, Company, Industry, and City)")
            else:
                # Create profile
                result = user_profile.create_profile(
                    user_id=user_id,
                    current_role=current_role,
                    current_company=current_company,
                    industry=industry,
                    location_city=location_city,
                    company_stage=company_stage if company_stage else None,
                    location_country=location_country if location_country else None,
                    goals=goals if goals else [],
                    interests=interests if interests else [],
                    seeking_connections=seeking_connections if seeking_connections else []
                )

                if result['success']:
                    st.success("Profile created! Loading your dashboard...")
                    st.rerun()
                else:
                    st.error(f"Failed to create profile: {result['message']}")


# Main app
def main():
    # Handle URL parameters for password reset and email verification
    query_params = st.query_params

    # Handle email verification token
    if 'verify_email' in query_params:
        token = query_params['verify_email']
        st.markdown("<h1 style='text-align: center; margin-top: 2rem; font-family: var(--font-serif);'>Email Verification</h1>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.spinner("Verifying your email..."):
                result = security.verify_email_token(token)

                if result['success']:
                    st.success(result['message'])
                    st.balloons()
                    if st.button("Go to Login", type="primary", use_container_width=True):
                        st.query_params.clear()
                        st.rerun()
                else:
                    st.error(result['message'])
                    if st.button("Back to Home", use_container_width=True):
                        st.query_params.clear()
                        st.rerun()
        return

    # Handle password reset token
    if 'reset_token' in query_params:
        token = query_params['reset_token']
        show_password_reset_form(token)
        return

    # Initialize session state for authentication
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    if 'show_register' not in st.session_state:
        st.session_state['show_register'] = False
    if 'show_forgot_password' not in st.session_state:
        st.session_state['show_forgot_password'] = False
    if 'show_login' not in st.session_state:
        st.session_state['show_login'] = False
    if 'show_connections' not in st.session_state:
        st.session_state['show_connections'] = False
    if 'show_profile' not in st.session_state:
        st.session_state['show_profile'] = False

    # === SECURITY: Clean up expired CSRF tokens ===
    cleanup_csrf_tokens()

    # === SECURITY: Check session timeout (30 minutes) ===
    if st.session_state.get('authenticated'):
        from datetime import datetime, timedelta

        if 'last_activity' in st.session_state:
            inactive_time = datetime.now() - st.session_state['last_activity']

            if inactive_time > timedelta(minutes=30):
                # Session expired
                user_id = st.session_state.get('user', {}).get('id', 'unknown')
                st.session_state['authenticated'] = False
                st.session_state['user'] = None
                st.warning("Session expired due to inactivity. Please log in again.")
                log_security_event('session_expired', user_id, {
                    'inactive_minutes': inactive_time.total_seconds() / 60
                })
                st.rerun()

        # Update last activity timestamp
        from datetime import datetime
        st.session_state['last_activity'] = datetime.now()

    # ============================================
    # RENDER PROFESSIONAL HEADER BAR
    # ============================================
    # Header CSS
    st.markdown("""
<style>
.header-container {
    background: white;
    padding: 1rem 2rem;
    border-bottom: 1px solid #e5e7eb;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    margin: -1rem -1rem 0 -1rem;
}

.header-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: #1a1a1a;
    margin: 0;
    line-height: 2.5rem;
    white-space: nowrap;
    display: inline-block;
    vertical-align: middle;
}

.header-button {
    background: transparent;
    border: none;
    color: #6b7280;
    font-size: 0.9375rem;
    font-weight: 500;
    padding: 0.5rem 1rem;
    cursor: pointer;
    transition: color 0.15s;
    line-height: 2.5rem;
}

.header-button:hover {
    color: #2563eb;
}
</style>
""", unsafe_allow_html=True)

    if st.session_state.get('authenticated'):
        # Authenticated user navigation
        user_id = st.session_state.get('user', {}).get('id', 'anonymous')
        user_name = st.session_state['user']['full_name']
        user_email = st.session_state['user']['email']

        # Get pending requests count (for later use)
        pending_requests_count = 0
        if user_id != 'anonymous':
            pending_requests_list = collaboration.get_pending_connection_requests(user_id)
            pending_requests_count = len(pending_requests_list)

        # Get contact count
        contact_count = auth.get_contact_count(user_id)

        # Clean header with logo left, buttons right
        header_cols = st.columns([3, 5, 1, 1, 1])

        with header_cols[0]:
            st.markdown('<h1 class="header-title">6th Degree AI</h1>', unsafe_allow_html=True)

        # header_cols[1] is spacer

        with header_cols[2]:
            st.markdown('<div class="text-link-button">', unsafe_allow_html=True)
            if st.button("Feedback", key="top_nav_feedback"):
                st.session_state['show_feedback_modal'] = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with header_cols[3]:
            st.markdown('<div class="text-link-button">', unsafe_allow_html=True)
            user_label = user_name.split()[0] + " ▾"
            if st.button(user_label, key="top_nav_user_menu"):
                st.session_state['show_user_menu'] = not st.session_state.get('show_user_menu', False)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with header_cols[4]:
            st.markdown('<div class="text-link-button">', unsafe_allow_html=True)
            if st.button("Logout", key="top_nav_logout"):
                st.session_state['authenticated'] = False
                st.session_state['user'] = None
                if 'contacts_df' in st.session_state:
                    del st.session_state['contacts_df']
                st.success("Logged out successfully!")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # User dropdown menu (appears below header)
        if st.session_state.get('show_user_menu'):
            st.markdown(f"""
<div style='background: white; border: 1px solid #e5e7eb; border-radius: 8px;
     padding: 1rem; margin: 0.5rem 0 1rem auto; max-width: 300px; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);'>
    <p style='font-size: 0.875rem; color: var(--text-tertiary); margin: 0 0 0.5rem 0;'>Signed in as</p>
    <p style='font-size: 1rem; font-weight: 600; color: var(--text-primary); margin: 0;'>{user_name}</p>
    <p style='font-size: 0.875rem; color: var(--text-secondary); margin: 0.25rem 0 0 0;'>{user_email}</p>
    {f"<p style='font-size: 0.875rem; color: var(--text-secondary); margin: 0.75rem 0 0 0;'>{contact_count:,} contacts saved</p>" if contact_count > 0 else ""}
</div>
""", unsafe_allow_html=True)

            # My Profile button
            if st.button("My Profile", key="nav_profile", use_container_width=True, type="secondary"):
                st.session_state['show_profile'] = True
                st.session_state['show_connections'] = False
                st.session_state['show_user_menu'] = False
                st.rerun()

    else:
        # Anonymous user navigation
        header_cols = st.columns([3, 6, 1, 1])

        with header_cols[0]:
            st.markdown('<h1 class="header-title">6th Degree AI</h1>', unsafe_allow_html=True)

        # header_cols[1] is spacer

        with header_cols[2]:
            if st.button("Login", key="nav_login", type="secondary"):
                st.session_state['show_register'] = False
                st.session_state['show_forgot_password'] = False
                st.session_state['show_login'] = True
                st.rerun()

        with header_cols[3]:
            if st.button("Sign Up", key="nav_signup", type="primary"):
                st.session_state['show_register'] = True
                st.session_state['show_login'] = False
                st.rerun()

    # Clean spacing after header
    st.markdown('<div style="height: 2rem;"></div>', unsafe_allow_html=True)

    # Render feedback modal if requested
    render_feedback_modal()

    # Phase 3B: Migrate existing users to new search (one-time index build)
    if st.session_state.get('authenticated') and HAS_NEW_SEARCH:
        migrate_to_new_search()


    # Apply dark mode CSS if enabled
    if st.session_state.get('dark_mode', False):
        st.markdown("""
        <style>
            /* Dark Mode Overrides - Target ALL background elements */
            html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .main, .stApp {
                background-color: #0a0a0a !important;
                background: #0a0a0a !important;
            }

            /* Force block container background */
            .block-container {
                background-color: #0a0a0a !important;
            }

            h1 {
                color: #ffffff !important;
            }

            .subtitle {
                color: #b0b0b0 !important;
            }

            h2, h3, h4 {
                color: #e0e0e0 !important;
            }

            .main .stMarkdown, .stMarkdown p, .stMarkdown div {
                color: #b0b0b0 !important;
            }

            .stTextInput > div > div > input {
                background: #1a1a1a !important;
                color: #e0e0e0 !important;
                border-color: #2a2a2a !important;
            }

            .stTextInput > div > div > input:focus {
                border-color: #4a4a4a !important;
                box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.05) !important;
            }

            .stButton > button {
                background: #ffffff !important;
                color: #0a0a0a !important;
            }

            .stButton > button:hover {
                background: #e0e0e0 !important;
            }

            .stFormSubmitButton > button {
                background: #ffffff !important;
                color: #0a0a0a !important;
            }

            .stDownloadButton > button {
                background: #1a1a1a !important;
                color: #e0e0e0 !important;
                border-color: #4a4a4a !important;
            }

            .results-summary {
                background: #1a1a1a !important;
                border-color: #2a2a2a !important;
            }

            .stDataFrame {
                border-color: #2a2a2a !important;
            }

            .streamlit-expanderHeader {
                background: #1a1a1a !important;
                color: #e0e0e0 !important;
                border-color: #2a2a2a !important;
            }

            .stTabs {
                background: #1a1a1a !important;
                border-color: #2a2a2a !important;
            }

            .stSuccess {
                background: #1a3a1a !important;
                border-color: #2a5a2a !important;
                color: #86efac !important;
            }

            .stInfo {
                background: #1a2a3a !important;
                border-color: #2a4a5a !important;
                color: #7dd3fc !important;
            }

            hr {
                border-color: #2a2a2a !important;
            }
        </style>
        """, unsafe_allow_html=True)

    # Lower navigation - Dashboard/Connections (only show for authenticated users with contacts, NOT on profile page)
    if st.session_state.get('authenticated') and 'contacts_df' in st.session_state and not st.session_state.get('show_profile'):
        # Get pending requests count (reuse from top nav)
        user_id = st.session_state.get('user', {}).get('id', 'anonymous')
        pending_requests_count = 0
        if user_id != 'anonymous':
            pending_requests_list = collaboration.get_pending_connection_requests(user_id)
            pending_requests_count = len(pending_requests_list)

        # CSS for inactive navigation button (no box at all) - HIGH SPECIFICITY
        st.markdown("""
<style>
/* Remove margins and ensure alignment */
.inactive-nav-button > .stButton {
    margin: 0 !important;
}

.inactive-nav-button > .stButton > button,
.inactive-nav-button .stButton > button {
    background: transparent !important;
    border: 0px solid transparent !important;
    box-shadow: none !important;
    outline: none !important;
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    padding: 12px 20px !important;
    border-radius: 8px !important;
    min-width: 120px !important;
    height: 40px !important;
    font-size: 15px !important;
    transition: all 0.15s ease !important;
    line-height: 1 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}

.inactive-nav-button > .stButton > button:hover,
.inactive-nav-button .stButton > button:hover {
    background: rgba(43, 108, 176, 0.05) !important;
    color: var(--primary) !important;
    border: 0px solid transparent !important;
    box-shadow: none !important;
}

.inactive-nav-button > .stButton > button:focus,
.inactive-nav-button > .stButton > button:active,
.inactive-nav-button .stButton > button:focus,
.inactive-nav-button .stButton > button:active {
    background: transparent !important;
    border: 0px solid transparent !important;
    box-shadow: none !important;
    outline: none !important;
}

/* Ensure active nav buttons also have proper height and alignment */
div[data-testid="column"] > div > .stButton > button[kind="secondary"] {
    height: 40px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    line-height: 1 !important;
}

/* Lower nav container - force vertical alignment for all columns */
.lower-nav-container [data-testid="column"] {
    display: flex !important;
    align-items: center !important;
    min-height: 40px !important;
}
</style>
""", unsafe_allow_html=True)

        # Check which page we're on
        on_connections_page = st.session_state.get('show_connections', False)

        # Lower navigation buttons - single row with proper alignment
        st.markdown('<div class="lower-nav-container">', unsafe_allow_html=True)
        lower_nav_cols = st.columns([1, 0.1, 1.2, 8])

        with lower_nav_cols[0]:
            # Dashboard button
            if not on_connections_page:
                # Active - show with box (type="secondary" gives it border)
                if st.button("Dashboard", key="lower_nav_dashboard", type="secondary"):
                    st.session_state['show_connections'] = False
                    st.rerun()
            else:
                # Inactive - no box
                st.markdown('<div class="inactive-nav-button">', unsafe_allow_html=True)
                if st.button("Dashboard", key="lower_nav_dashboard_inactive"):
                    st.session_state['show_connections'] = False
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # lower_nav_cols[1] is small gap

        with lower_nav_cols[2]:
            # Connections button
            connections_label = f"Connections ({pending_requests_count})" if pending_requests_count > 0 else "Connections"

            if on_connections_page:
                # Active - show with box
                if st.button(connections_label, key="lower_nav_connections", type="secondary"):
                    st.session_state['show_connections'] = True
                    st.rerun()
            else:
                # Inactive - no box
                st.markdown('<div class="inactive-nav-button">', unsafe_allow_html=True)
                if st.button(connections_label, key="lower_nav_connections_inactive"):
                    st.session_state['show_connections'] = True
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # Close lower nav container
        st.markdown('</div>', unsafe_allow_html=True)

        # Add spacing below nav
        st.markdown('<div style="height: 24px;"></div>', unsafe_allow_html=True)

    # Hero section - Flow-inspired minimal design (only show when NOT on profile page)
    if not st.session_state.get('show_profile'):
        st.markdown("""
<div style='text-align: center; padding: var(--space-24) 0 var(--space-16) 0;'>
<h1 class='hero-title'>Get the most out of your network<br>using our advanced AI solution</h1>
<p class='hero-subtitle'>Search your network naturally. Find the right person, instantly.</p>
</div>
""", unsafe_allow_html=True)

    # === SIDEBAR REMOVED (Phase 1) ===
    # All sidebar functionality moved to unified top navigation bar
    # - User info/menu: Now in top-right user dropdown
    # - Login/Signup buttons: Now in top-right for anonymous users
    # - Feedback form: Now accessible via "Feedback" button in nav bar

    # Show login/register modal for anonymous users if requested
    if not st.session_state.get('authenticated'):
        if st.session_state.get('show_register'):
            show_register_page()
            return
        elif st.session_state.get('show_forgot_password'):
            show_forgot_password_page()
            return
        elif st.session_state.get('show_login'):
            show_login_page()
            return

    # === DUPLICATE NAVIGATION REMOVED (Phase 1) ===
    # Old navigation buttons removed - now handled by unified top nav bar

    # Get user_id for main content area (needed for dashboard and other features)
    user_id = st.session_state.get('user', {}).get('id', 'anonymous')

    # === PROFILE ONBOARDING (Required for authenticated users) ===
    if st.session_state.get('authenticated') and user_id != 'anonymous':
        # Check if user has completed profile
        if not user_profile.profile_exists(user_id):
            # Show profile onboarding modal (blocking - can't dismiss)
            show_profile_onboarding(user_id)
            return  # Don't show rest of app until profile complete

    # Show profile page if requested (requires authentication)
    if st.session_state.get('show_profile'):
        if st.session_state.get('authenticated'):
            show_profile_page()
            return
        else:
            st.warning("Please log in to view your profile")
            st.session_state['show_profile'] = False
            st.session_state['show_login'] = True
            st.rerun()

    # Show connections page if requested (requires authentication)
    if st.session_state.get('show_connections'):
        if st.session_state.get('authenticated'):
            show_connections_page()
            return
        else:
            st.warning("Please log in to use Connections features")
            st.session_state['show_connections'] = False
            st.session_state['show_login'] = True
            st.rerun()

    # Main content area
    if 'contacts_df' not in st.session_state:
        # Premium Upload Card - Flow Design with integrated uploader
        st.markdown("<div style='max-width: 700px; margin: var(--space-8) auto;'>", unsafe_allow_html=True)

        st.markdown("""
<div class='card' style='text-align: center; padding: var(--space-8) var(--space-8) var(--space-4) var(--space-8);'>
<h2 style='font-family: var(--font-serif); font-size: 2.25rem; font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-3);'>Get Started</h2>
<p style='color: var(--text-secondary); font-size: 1.125rem; margin-bottom: var(--space-6);'>Upload your LinkedIn CSV to begin searching your network</p>
</div>
""", unsafe_allow_html=True)

        # Check if user already has contacts (only for logged-in users)
        user_has_contacts = False
        replace_contacts = False
        if st.session_state.get('authenticated'):
            user_has_contacts = auth.get_contact_count(st.session_state['user']['id']) > 0
            if user_has_contacts:
                st.info("You already have contacts saved. Upload a new CSV to replace them.")
                replace_contacts = st.checkbox("Replace existing contacts", value=False,
                                             help="Check this to delete your current contacts and upload new ones")

        uploaded_file = st.file_uploader(
            "Upload LinkedIn CSV",
            type=['csv'],
            help="Download your LinkedIn connections and upload the Connections.csv file",
            label_visibility="collapsed"
        )

        st.markdown("</div>", unsafe_allow_html=True)  # Close card container

        if uploaded_file:
            # === SECURITY: Rate Limiting ===
            user_id = st.session_state.get('user', {}).get('id', 'anonymous')
            allowed, error_msg = check_rate_limit(user_id, 'csv_upload')

            if not allowed:
                st.error(error_msg)
                log_rate_limit(user_id, 'csv_upload', extract_wait_time(error_msg))
            else:
                with st.spinner("Parsing contacts..."):
                    df = parse_linkedin_csv(uploaded_file)
                    if df is not None:
                        # === SECURITY: Sanitize CSV Data ===
                        df = sanitize_csv_data(df)

                        # === ENRICHMENT: Infer company from email domains ===
                        try:
                            from services.email_enrichment import enrich_contacts_from_email
                            df, enrichment_stats = enrich_contacts_from_email(df)
                            if enrichment_stats['enriched'] > 0:
                                st.success(f"✨ Enriched {enrichment_stats['enriched']} contacts with company info from email domains!")
                        except Exception as e:
                            print(f"Email enrichment failed: {e}")
                            # Continue without enrichment

                        st.session_state['contacts_df'] = df

                        # Get user_id (for both logged-in and anonymous)
                        user_id = st.session_state.get('user', {}).get('id', 'anonymous')

                        if st.session_state.get('authenticated'):
                            # LOGGED IN: Save to database
                            if user_has_contacts:
                                if not replace_contacts:
                                    st.warning("Check 'Replace existing contacts' above to save these to your account.")
                                    st.info(f"Loaded {len(df)} contacts to current session")
                                else:
                                    # Delete old contacts first
                                    with st.spinner("Replacing contacts..."):
                                        if auth.delete_user_contacts(user_id):
                                            save_result = auth.save_contacts_to_db(user_id, df)
                                            if save_result['success']:
                                                st.success(f"Replaced with {len(df)} new contacts!")
                                            else:
                                                st.error(f"Error saving: {save_result['message']}")
                                        else:
                                            st.error("Error deleting old contacts")
                            else:
                                # No existing contacts, just save
                                save_result = auth.save_contacts_to_db(user_id, df)
                                if save_result['success']:
                                    st.success(f"Loaded and saved {len(df)} contacts to your account!")
                                else:
                                    st.warning(f"Loaded {len(df)} contacts (saved to session only)")
                        else:
                            # ANONYMOUS: Session only with upgrade prompt
                            st.success(f"Loaded {len(df)} contacts!")
                            st.info("**Sign up** in the sidebar to save your contacts permanently!")

                        # Log CSV upload
                        analytics.log_csv_upload(
                            file_name=uploaded_file.name,
                            num_contacts=len(df),
                            success=True,
                            session_id=st.session_state['session_id']
                        )

                        # Phase 3B: Build search indexes for fast future searches
                        if HAS_NEW_SEARCH:
                            # Force rebuild since user uploaded new CSV
                            try:
                                initialize_search_for_user(user_id, df, force_rebuild=True)
                            except Exception as e:
                                st.warning(f"Could not build search indexes: {e}")

                        # Phase 4: Pre-cache popular queries for instant search
                        if HAS_AGENTIC_SEARCH:
                            try:
                                client = get_client()
                                initialize_search_caching(client, df)
                            except Exception as e:
                                print(f"Could not pre-cache queries: {e}")

                        # Show preview
                        with st.expander("Preview contacts"):
                            display_cols = [col for col in ['full_name', 'position', 'company'] if col in df.columns]
                            st.dataframe(df[display_cols].head(10), use_container_width=True)

                        st.rerun()
                    else:
                        # Log failed upload
                        analytics.log_csv_upload(
                            file_name=uploaded_file.name,
                            num_contacts=0,
                            success=False,
                            error_message="Failed to parse CSV",
                            session_id=st.session_state['session_id']
                        )

        # Privacy reassurance
        st.markdown("""
<div style='max-width: 700px; margin: var(--space-6) auto; padding: var(--space-4); background: var(--bg-tertiary); border-radius: var(--radius-md); text-align: center;'>
<p style='font-size: 0.875rem; color: var(--text-secondary); margin: 0;'>Your data is private and secure. We never share or sell your information.</p>
</div>
""", unsafe_allow_html=True)

        # LinkedIn Download Instructions - Clean
        st.markdown("<div style='max-width: 700px; margin: var(--space-16) auto;'><h3 style='font-size: 1.5rem; font-weight: 600; margin-bottom: var(--space-6);'>How to Get Your LinkedIn Data</h3>", unsafe_allow_html=True)
        st.markdown("""
<div class='card' style='margin-bottom: var(--space-8);'>
<ol style='margin: 0; padding-left: 1.5rem; color: var(--text-secondary); line-height: 1.8;'>
<li style='margin-bottom: var(--space-3);'>Go to <a href='https://www.linkedin.com/mypreferences/d/download-my-data' target='_blank' style='color: var(--primary); font-weight: 600; text-decoration: none;'>LinkedIn Data Download</a></li>
<li style='margin-bottom: var(--space-3);'>Click "Request archive"</li>
<li style='margin-bottom: var(--space-3);'>Wait 10-15 minutes for the email</li>
<li style='margin-bottom: var(--space-3);'>Download and extract the ZIP file</li>
<li style='margin-bottom: var(--space-3);'>Find the <strong>Connections.csv</strong> file</li>
<li>Upload it above</li>
</ol>
</div>
</div>
""", unsafe_allow_html=True)

        # Example queries - Clean with clickable questions
        st.markdown("<div style='max-width: 700px; margin: 0 auto;'><h3 style='font-size: 1.5rem; font-weight: 600; margin-bottom: var(--space-6);'>Example Searches</h3>", unsafe_allow_html=True)
        st.markdown("<p style='color: var(--text-secondary); margin-bottom: var(--space-4); font-size: 0.9375rem;'>Click any question to try it:</p>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("<div class='card'><h4 style='margin-bottom: var(--space-3); color: var(--text-primary); font-weight: 600; font-size: 1rem;'>By Industry</h4>", unsafe_allow_html=True)
            if st.button("Who works in venture capital?", key="example_vc", use_container_width=True, type="secondary"):
                st.session_state['auto_execute_query'] = "Who works in venture capital?"
                st.rerun()
            if st.button("Show me people in tech", key="example_tech", use_container_width=True, type="secondary"):
                st.session_state['auto_execute_query'] = "Show me people in tech"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='card'><h4 style='margin-bottom: var(--space-3); color: var(--text-primary); font-weight: 600; font-size: 1rem;'>By Role</h4>", unsafe_allow_html=True)
            if st.button("Who is an engineer?", key="example_engineer", use_container_width=True, type="secondary"):
                st.session_state['auto_execute_query'] = "Who is an engineer?"
                st.rerun()
            if st.button("Show me product managers", key="example_pm", use_container_width=True, type="secondary"):
                st.session_state['auto_execute_query'] = "Show me product managers"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with col3:
            st.markdown("<div class='card'><h4 style='margin-bottom: var(--space-3); color: var(--text-primary); font-weight: 600; font-size: 1rem;'>By Seniority</h4>", unsafe_allow_html=True)
            if st.button("Who is the most senior?", key="example_senior", use_container_width=True, type="secondary"):
                st.session_state['auto_execute_query'] = "Who is the most senior?"
                st.rerun()
            if st.button("Show me top 5 leaders", key="example_leaders", use_container_width=True, type="secondary"):
                st.session_state['auto_execute_query'] = "Show me top 5 leaders"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)  # Close max-width container

    else:
        contacts_df = st.session_state['contacts_df']

        # Initialize network selector in session state
        if 'search_network_selection' not in st.session_state:
            st.session_state['search_network_selection'] = 'My Network'

        # Helper function to round down to nearest 100 and format
        def format_count(count):
            if count == 0:
                return "0"
            rounded = (count // 100) * 100
            return f"{rounded:,}+"

        # Get connection counts for display
        my_network_count = len(contacts_df)
        my_network_display = format_count(my_network_count)

        # Get extended network count (only if authenticated)
        extended_count = 0
        if st.session_state.get('authenticated'):
            try:
                extended_contacts_df = collaboration.get_contacts_from_connected_users(user_id)
                extended_count = len(extended_contacts_df) if not extended_contacts_df.empty else 0
                # Debug: Print to console to verify counts
                print(f"DEBUG - My Network: {my_network_count}, Extended Network: {extended_count}")
            except Exception as e:
                print(f"DEBUG - Error getting extended network count: {e}")
                extended_count = 0

        extended_network_display = format_count(extended_count)

        # Initialize checkbox states in session state
        if 'search_my_network' not in st.session_state:
            st.session_state['search_my_network'] = True  # Default: My Network checked
        if 'search_extended_network' not in st.session_state:
            st.session_state['search_extended_network'] = False  # Default: Extended unchecked

        # Network Selector - Checkboxes (can select both)
        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1])

        with col1:
            search_my = st.checkbox(
                f"Search My Network ({my_network_display} contacts)",
                value=st.session_state['search_my_network'],
                key="checkbox_my_network"
            )
            st.session_state['search_my_network'] = search_my

        with col2:
            search_extended = st.checkbox(
                f"Search Extended Network ({extended_network_display} contacts)",
                value=st.session_state['search_extended_network'],
                key="checkbox_extended_network"
            )
            st.session_state['search_extended_network'] = search_extended

        # Dynamic placeholder based on selection
        if search_my and search_extended:
            search_placeholder = "Search both networks..."
        elif search_my:
            search_placeholder = "Search your contacts..."
        elif search_extended:
            search_placeholder = "Search connected networks..."
        else:
            search_placeholder = "Select at least one network to search..."

        # Unified Search Interface - handles both search and analytics
        with st.form(key='unified_search_form', clear_on_submit=False):
            query = st.text_input(
                "Search...",
                placeholder=search_placeholder,
                label_visibility="collapsed",
                key="unified_search_query"
            )

            # Submit button (triggered by Enter or click)
            search_button = st.form_submit_button("Search", type="primary")

        # Example questions in expander - clickable
        with st.expander("Example Questions", expanded=False):
            st.markdown("**Search for People:**")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Who works in venture capital?", key="exp_vc", use_container_width=True):
                    st.session_state['auto_execute_query'] = "Who works in venture capital?"
                    st.rerun()
                if st.button("Who is the most senior person?", key="exp_senior", use_container_width=True):
                    st.session_state['auto_execute_query'] = "Who is the most senior person?"
                    st.rerun()
            with col2:
                if st.button("Show me people in tech companies", key="exp_tech_companies", use_container_width=True):
                    st.session_state['auto_execute_query'] = "Show me people in tech companies"
                    st.rerun()
                if st.button("Find engineers at Google", key="exp_google_eng", use_container_width=True):
                    st.session_state['auto_execute_query'] = "Find engineers at Google"
                    st.rerun()

            st.markdown("**Network Analytics:**")
            col3, col4 = st.columns(2)
            with col3:
                if st.button("What industry do I have most contacts in?", key="exp_industry", use_container_width=True):
                    st.session_state['auto_execute_query'] = "What industry do I have most contacts in?"
                    st.rerun()
                if st.button("Which companies are most represented?", key="exp_companies", use_container_width=True):
                    st.session_state['auto_execute_query'] = "Which companies are most represented?"
                    st.rerun()
                if st.button("Summarize my network for me", key="exp_summary", use_container_width=True):
                    st.session_state['auto_execute_query'] = "Summarize my network for me"
                    st.rerun()
            with col4:
                if st.button("How many people work at tech companies?", key="exp_tech_count", use_container_width=True):
                    st.session_state['auto_execute_query'] = "How many people work at tech companies?"
                    st.rerun()
                if st.button("What percentage of my contacts are in finance?", key="exp_finance_pct", use_container_width=True):
                    st.session_state['auto_execute_query'] = "What percentage of my contacts are in finance?"
                    st.rerun()

        # Auto-execute search from example questions
        auto_query = st.session_state.get('auto_execute_query')
        if auto_query:
            # Clear the flag
            del st.session_state['auto_execute_query']
            # Set query to execute
            query = auto_query
            search_button = True

        if search_button and query:
            # === SECURITY: Rate Limiting ===
            user_id = st.session_state.get('user_id', 'anonymous')
            allowed, error_msg = check_rate_limit(user_id, 'search')

            if not allowed:
                st.error(error_msg)
                log_rate_limit(user_id, 'search', extract_wait_time(error_msg))
                st.stop()

            # === SECURITY: Input Validation ===
            validation = validate_search_query(query)
            if not validation['valid']:
                st.error(validation['message'])

                # Check if malicious and log
                from services.security.input_validator import InputValidator
                detection = InputValidator.detect_malicious_content(query)
                if detection['is_malicious']:
                    log_malicious_input(
                        input_type='search',
                        user_id=user_id,
                        patterns=detection['detected_patterns'],
                        severity=detection['severity']
                    )

                st.stop()

            # Use sanitized query for the rest of the search
            query = validation['query']

            # Classify query type
            query_type = classify_query_type(query)

            if query_type == "analytics":
                # Handle analytics query
                with st.spinner("AI is analyzing your network..."):
                    result = analyze_network_with_ai(query, contacts_df)

                    if result['success']:
                        # Store analytics result
                        st.session_state['analytics_result'] = result['answer']

                        # Check if query might also want to see people (hybrid query)
                        # Keywords like "how many people" suggest they might want the list too
                        query_lower = query.lower()
                        hybrid_keywords = ['how many people', 'how many contacts', 'who all']
                        is_hybrid = any(keyword in query_lower for keyword in hybrid_keywords)

                        if is_hybrid:
                            # Also run search to get the people list
                            intent = extract_search_intent(query, contacts_df)
                            if intent:
                                filtered_df = filter_contacts(contacts_df, intent)
                                if not filtered_df.empty:
                                    st.session_state['filtered_df'] = filtered_df
                                    st.session_state['last_intent'] = intent
                                    summary = generate_summary(filtered_df, intent)
                                    st.session_state['summary'] = summary
                    else:
                        st.error(f"Analysis failed: {result.get('error', 'Unknown error')}")
            else:
                # Handle search query (find people)
                # Check which networks to search based on checkbox selections
                search_my = st.session_state.get('search_my_network', True)
                search_extended = st.session_state.get('search_extended_network', False)

                # Validate at least one network is selected
                if not search_my and not search_extended:
                    st.warning("Please select at least one network to search.")
                    search_contacts_df = None
                else:
                    # Build combined dataset based on selections
                    datasets_to_search = []
                    search_network_names = []

                    if search_my:
                        datasets_to_search.append(contacts_df)
                        search_network_names.append("My Network")

                    if search_extended:
                        try:
                            extended_contacts_df = collaboration.get_contacts_from_connected_users(user_id)
                            if not extended_contacts_df.empty:
                                datasets_to_search.append(extended_contacts_df)
                                search_network_names.append("Extended Network")
                        except Exception as e:
                            print(f"Error loading extended network: {e}")

                    # Combine datasets if multiple selected
                    if len(datasets_to_search) == 0:
                        st.info("No contacts available in selected network(s).")
                        search_contacts_df = None
                    elif len(datasets_to_search) == 1:
                        search_contacts_df = datasets_to_search[0]
                        spinner_text = f"Searching {search_network_names[0]}..."
                    else:
                        # Combine both networks
                        search_contacts_df = pd.concat(datasets_to_search, ignore_index=True)
                        # Remove duplicates based on email (if present)
                        if 'email' in search_contacts_df.columns:
                            search_contacts_df = search_contacts_df.drop_duplicates(subset=['email'], keep='first')
                        spinner_text = "Searching both networks..."

                # Only proceed if we have contacts to search
                if search_contacts_df is not None and not search_contacts_df.empty:
                    # Check for industry expansion FIRST (before AI agent)
                    # This ensures queries like "finance", "tech", "VC" use company-based search
                    should_use_industry_expansion = False
                    if HAS_NEW_SEARCH:
                        try:
                            from services.industry_expansion import expand_industry_query
                            expansion = expand_industry_query(query)
                            if expansion['should_expand'] and expansion['companies']:
                                should_use_industry_expansion = True
                                print(f"✅ Industry expansion triggered for '{query}': {len(expansion['companies'])} companies")
                        except Exception as e:
                            print(f"Industry expansion check failed: {e}")

                    # Phase 4: Use AI search agent for complex queries (SKIP if industry expansion is better)
                    if HAS_AI_AGENT and not should_use_industry_expansion:
                        # Clear any previous analytics result
                        if 'analytics_result' in st.session_state:
                            del st.session_state['analytics_result']

                        try:
                            # Get OpenAI client
                            client = get_client()

                            with st.spinner("AI is analyzing your query..."):
                                # Create AI agent
                                agent = create_ai_search_agent(client, search_contacts_df)

                                # Execute search
                                search_result = agent.search(query)

                            if search_result['success']:
                                # Convert results to DataFrame
                                if search_result['results']:
                                    # Convert AI results to DataFrame format
                                    results_data = []
                                    for r in search_result['results']:
                                        results_data.append({
                                            'full_name': r.get('name', ''),
                                            'company': r.get('company', ''),
                                            'position': r.get('position', ''),
                                            'email': r.get('email', ''),
                                        })
                                    filtered_df = pd.DataFrame(results_data)
                                else:
                                    filtered_df = pd.DataFrame()

                                st.session_state['filtered_df'] = filtered_df

                                # Generate summary
                                if not filtered_df.empty:
                                    summary = f"""
                                    <strong>Search Results for "{query}"</strong><br>
                                    Found {len(filtered_df)} matches • AI Search • ${search_result['cost_estimate']:.4f}
                                    """
                                else:
                                    summary = f"No results found for '{query}'"

                                st.session_state['summary'] = summary

                                # Display AI reasoning
                                if search_result.get('reasoning'):
                                    with st.expander("How AI found these results", expanded=False):
                                        st.markdown(search_result['reasoning'])
                                        if search_result.get('tool_calls'):
                                            st.markdown("**Tools used:**")
                                            for tc in search_result['tool_calls']:
                                                st.markdown(f"- `{tc['tool']}` → {tc['results_count']} results")
                            else:
                                st.warning(f"AI search didn't find results. Trying regular search...")
                                # Fall through to regular search

                        except Exception as e:
                            st.warning(f"AI search error: {e}. Using regular search...")
                            print(f"AI search error: {e}")
                            import traceback
                            traceback.print_exc()
                            # Fall through to regular search

                    # Fallback to Phase 3B hybrid search
                    if HAS_NEW_SEARCH and ('filtered_df' not in st.session_state or st.session_state.get('filtered_df') is None or st.session_state['filtered_df'].empty):
                        with st.spinner(spinner_text):
                            # Clear any previous analytics result
                            if 'analytics_result' in st.session_state:
                                del st.session_state['analytics_result']

                            try:
                                # Use hybrid search
                                search_result = smart_search(query, search_contacts_df)

                                # Fast hybrid search result
                                filtered_df = search_result.get('filtered_df', pd.DataFrame())
                                st.session_state['filtered_df'] = filtered_df

                                # Generate summary
                                if not filtered_df.empty:
                                    tier_info = f" • Method: {search_result.get('tier_used', 'unknown')}"
                                    latency_info = f" • Time: {search_result.get('latency_ms', 0):.0f}ms"
                                    cached_info = " • Cached" if search_result.get('cached') else ""

                                    summary = f"""
                                    <strong>Search Results for "{query}"</strong><br>
                                    Found {len(filtered_df)} matches{tier_info}{latency_info}{cached_info}
                                    """
                                else:
                                    summary = f"No results found for '{query}'"

                                st.session_state['summary'] = summary

                                # Show performance badge
                                if search_result.get('cached'):
                                    st.success(f"Instant search (cached) • {len(filtered_df)} results")
                                elif search_result.get('latency_ms', 0) < 100:
                                    st.success(f"Lightning fast ({search_result.get('latency_ms', 0):.0f}ms) • {len(filtered_df)} results")

                                # Log search query
                                analytics.log_search_query(
                                    query=query,
                                    results_count=len(st.session_state.get('filtered_df', pd.DataFrame())),
                                    intent={'query': query, 'tier': search_result.get('tier_used', 'unknown')},
                                    session_id=st.session_state['session_id']
                                )

                            except Exception as e:
                                st.error(f"Search error: {e}")
                                st.caption("Falling back to legacy search...")

                                # Fallback to old search
                                intent = extract_search_intent(query, contacts_df)
                                if intent:
                                    st.session_state['last_intent'] = intent
                                    filtered_df = filter_contacts(contacts_df, intent)
                                    st.session_state['filtered_df'] = filtered_df
                                    summary = generate_summary(filtered_df, intent)
                                    st.session_state['summary'] = summary

                else:
                    # Legacy search (if new search not available)
                    with st.spinner("Searching your network..."):
                        intent = extract_search_intent(query, contacts_df)

                        if intent:
                            st.session_state['last_intent'] = intent

                            # Clear any previous analytics result
                            if 'analytics_result' in st.session_state:
                                del st.session_state['analytics_result']

                            # Debug: Show what the AI understood
                            with st.expander("Debug: What the AI understood from your query"):
                                st.json(intent)

                            # Filter contacts
                            filtered_df = filter_contacts(contacts_df, intent)
                            st.session_state['filtered_df'] = filtered_df

                            # Generate summary
                            summary = generate_summary(filtered_df, intent)
                            st.session_state['summary'] = summary

                            # Log search query
                            analytics.log_search_query(
                                query=query,
                                results_count=len(filtered_df),
                                intent=intent,
                                session_id=st.session_state['session_id']
                            )

        # Display results section
        st.markdown("---")

        # Display AI analytics insights if available
        if 'analytics_result' in st.session_state:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### AI Insights")
            st.markdown(f"""
            <div class='results-summary'>
                {st.session_state['analytics_result']}
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        # Display search results (people list)
        if 'filtered_df' in st.session_state and 'summary' in st.session_state:
            st.markdown("<br>", unsafe_allow_html=True)

            # Summary in premium card
            st.markdown(f"""
            <div class='results-summary'>
                {st.session_state['summary']}
            </div>
            """, unsafe_allow_html=True)

            filtered_df = st.session_state['filtered_df']

            if not filtered_df.empty:
                st.markdown("<br>", unsafe_allow_html=True)

                # Check which networks were searched
                search_my = st.session_state.get('search_my_network', True)
                search_extended = st.session_state.get('search_extended_network', False)
                searching_both = search_my and search_extended
                searching_only_extended = search_extended and not search_my

                # Pagination setup
                contacts_per_page = 10
                total_contacts = len(filtered_df)
                total_pages = (total_contacts + contacts_per_page - 1) // contacts_per_page  # Ceiling division

                # Initialize pagination state
                if 'current_page' not in st.session_state:
                    st.session_state['current_page'] = 1

                # Reset to page 1 if we just did a new search
                if 'last_search_query' not in st.session_state or st.session_state.get('last_search_query') != query:
                    st.session_state['current_page'] = 1
                    if query:
                        st.session_state['last_search_query'] = query

                current_page = st.session_state['current_page']

                # Header - always show selection controls since results may contain mixed sources
                col_header1, col_header2, col_header3 = st.columns([2, 1, 1])
                with col_header1:
                    if searching_both:
                        st.markdown("### Results from Both Networks")
                    elif searching_only_extended:
                        st.markdown("### Results from Extended Network")
                    else:
                        st.markdown("### Select Contacts")
                with col_header2:
                    st.markdown(f"<div style='text-align: right; padding-top: 0.5rem; color: #666;'>Page {current_page} of {total_pages}</div>", unsafe_allow_html=True)
                with col_header3:
                    if search_my:  # Only show select all if my network is included
                        select_all_page = st.checkbox("Select All on Page", key="select_all_page_checkbox")
                    else:
                        select_all_page = False

                # Calculate pagination slice
                start_idx = (current_page - 1) * contacts_per_page
                end_idx = min(start_idx + contacts_per_page, total_contacts)

                # Get contacts for current page
                page_contacts = filtered_df.iloc[start_idx:end_idx]

                # Display contacts with checkboxes
                display_cols = []
                for col in ['full_name', 'position', 'company', 'email']:
                    if col in filtered_df.columns:
                        display_cols.append(col)

                # Initialize selected contacts in session state
                if 'selected_contacts' not in st.session_state:
                    st.session_state['selected_contacts'] = set()

                # Handle select all on page (only if my network is included)
                if search_my and select_all_page:
                    for i in range(start_idx, end_idx):
                        # Only add My Network contacts (those without owner_user_id)
                        row_data = filtered_df.iloc[i]
                        if pd.isna(row_data.get('owner_user_id')):
                            st.session_state['selected_contacts'].add(i)
                elif search_my and not select_all_page:
                    # Check if all My Network contacts on current page are selected, if so deselect
                    my_network_indices = []
                    for i in range(start_idx, end_idx):
                        row_data = filtered_df.iloc[i]
                        if pd.isna(row_data.get('owner_user_id')):
                            my_network_indices.append(i)

                    if my_network_indices:
                        all_on_page_selected = all(i in st.session_state['selected_contacts'] for i in my_network_indices)
                        if all_on_page_selected:
                            for i in my_network_indices:
                                st.session_state['selected_contacts'].discard(i)

                # Display each contact card
                for page_idx, (idx, row) in enumerate(page_contacts.iterrows()):
                    # Actual index in the full filtered_df
                    actual_idx = start_idx + page_idx

                    # Determine if this contact is from extended network
                    # Extended network contacts have an owner_user_id field
                    is_extended_contact = not pd.isna(row.get('owner_user_id'))

                    if is_extended_contact:
                        # Extended Network Contact: Show contact with "Request Intro" button
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            name = row.get('full_name', 'No Name')
                            job_position = row.get('position', 'No Position')
                            company = row.get('company', 'No Company')
                            owner_name = row.get('owner_name', 'Unknown')

                            # === SECURITY: Sanitize extended network contact data ===
                            safe_name = sanitize_html(name)
                            safe_position = sanitize_html(job_position)
                            safe_company = sanitize_html(company)
                            safe_owner = sanitize_html(owner_name)

                            # Notion-inspired extended network card
                            st.markdown(f"""
                            <div class='extended-contact-card'>
                                <div class='contact-name'>{safe_name}</div>
                                <div class='contact-position'>{safe_position}</div>
                                <div class='contact-company'>🏢 {safe_company}</div>
                                <div class='extended-badge'>
                                    In {safe_owner}'s network
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                        with col2:
                            st.markdown("<br>", unsafe_allow_html=True)
                            # Request intro button
                            if st.button(f"Request Intro", key=f"req_intro_{actual_idx}_{idx}", use_container_width=True):
                                # Store contact info in session state to show request form
                                st.session_state['intro_request_contact'] = {
                                    'contact_id': row.get('id'),
                                    'target_name': row.get('full_name', ''),
                                    'target_company': row.get('company', ''),
                                    'target_position': row.get('position', ''),
                                    'target_email': row.get('email', ''),
                                    'connector_id': row.get('owner_user_id'),
                                    'connector_name': row.get('owner_name'),
                                    'connector_email': row.get('owner_email')
                                }
                                st.rerun()
                    else:
                        # My Network: Show contact with checkbox for selection
                        contact_selected = actual_idx in st.session_state['selected_contacts']

                        col1, col2 = st.columns([0.1, 0.9])

                        with col1:
                            if st.checkbox("", key=f"contact_{actual_idx}_{idx}", value=contact_selected, label_visibility="collapsed"):
                                st.session_state['selected_contacts'].add(actual_idx)
                            else:
                                st.session_state['selected_contacts'].discard(actual_idx)

                        with col2:
                            # Debug: Log what columns and data we have
                            if idx == 0:  # Only log first result
                                print(f"DEBUG: Available columns: {list(row.keys())}")
                                print(f"DEBUG: Row data sample: {dict(list(row.items())[:5])}")

                            name = row.get('full_name', '').strip() or 'No Name'
                            job_position = row.get('position', '').strip() or 'No Position'
                            company = row.get('company', '').strip() or 'No Company'
                            email = row.get('email', '').strip()

                            # Debug: Log the extracted values
                            if idx == 0:  # Only log first result
                                print(f"DEBUG: Extracted - name: '{name}', position: '{job_position}', company: '{company}'")

                            # === SECURITY: Sanitize all user-generated content to prevent XSS ===
                            safe_name = sanitize_html(name)
                            safe_position = sanitize_html(job_position)
                            safe_company = sanitize_html(company)
                            safe_email = sanitize_html(email) if email else ''

                            # Build email span only if email exists
                            email_html = f'<span class="contact-email">✉️ {safe_email}</span>' if email else ''

                            # Notion-inspired clean contact card
                            contact_card_html = f"""<div class='contact-card'>
    <div style='display: flex; align-items: flex-start; gap: 1rem;'>
        <div class='contact-avatar'>{name[0].upper() if name and name != 'No Name' else '?'}</div>
        <div style='flex: 1; min-width: 0;'>
            <div class='contact-name'>{safe_name}</div>
            <div class='contact-position'>{safe_position}</div>
            <div class='contact-info-row'>
                <span class='contact-company'>🏢 {safe_company}</span>
                {email_html}
            </div>
        </div>
    </div>
</div>"""
                            st.markdown(contact_card_html, unsafe_allow_html=True)

                # Pagination controls - Notion style
                if total_pages > 1:
                    st.markdown('<div style="margin-top: var(--space-8); margin-bottom: var(--space-6);"></div>', unsafe_allow_html=True)
                    col_prev, col_pages, col_next = st.columns([1, 3, 1])

                    with col_prev:
                        if st.button("← Previous", disabled=(current_page == 1), use_container_width=True, type="secondary"):
                            st.session_state['current_page'] = max(1, current_page - 1)
                            st.rerun()

                    with col_pages:
                        # Show page numbers
                        pages_to_show = {1, max(1, current_page - 1), current_page, min(total_pages, current_page + 1), total_pages}
                        pages_to_show = sorted(pages_to_show)

                        cols = st.columns(len(pages_to_show))
                        for i, page_num in enumerate(pages_to_show):
                            with cols[i]:
                                if page_num == current_page:
                                    st.markdown(f"<div class='pagination-current'>{page_num}</div>", unsafe_allow_html=True)
                                else:
                                    if st.button(str(page_num), key=f"page_{page_num}", use_container_width=True, type="secondary"):
                                        st.session_state['current_page'] = page_num
                                        st.rerun()

                    with col_next:
                        if st.button("Next →", disabled=(current_page == total_pages), use_container_width=True, type="secondary"):
                            st.session_state['current_page'] = min(total_pages, current_page + 1)
                            st.rerun()

                    st.markdown(f"<div style='text-align: center; color: var(--text-tertiary); margin-top: var(--space-4); font-size: 0.9375rem;'>Showing {start_idx + 1}-{end_idx} of {total_contacts} contacts</div>", unsafe_allow_html=True)

                # Show intro request form if extended network contact selected
                if 'intro_request_contact' in st.session_state:
                    contact = st.session_state['intro_request_contact']

                    st.markdown("---")
                    st.markdown("### Request Introduction")

                    st.markdown(f"""
                    <div style='background: #fffbeb; padding: 1.5rem; border-radius: 10px; border: 1px solid #fbbf24; margin-bottom: 1.5rem;'>
                        <div style='font-weight: 600; font-size: 1rem; color: #1a1a1a; margin-bottom: 0.5rem;'>
                            Requesting intro to: <span style='color: #3b82f6;'>{contact['target_name']}</span>
                        </div>
                        <div style='color: #666; font-size: 0.9rem; margin-bottom: 0.3rem;'>
                            {contact['target_position']} at {contact['target_company']}
                        </div>
                        <div style='color: #999; font-size: 0.85rem;'>
                            Via: {contact['connector_name']} ({contact['connector_email']})
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    with st.form("intro_request_form"):
                        request_message = st.text_area(
                            "Why do you want to meet this person? *",
                            placeholder="e.g., I'm raising a seed round for my fintech startup and would love to get Sarah's advice on product-market fit...",
                            height=150,
                            help="This will be shown to the person you want to meet"
                        )

                        context_for_connector = st.text_area(
                            "Additional context for your connection (optional)",
                            placeholder="e.g., We met at the Tech Conference 2024. Remember we talked about my startup idea?",
                            height=100,
                            help="Private message to help your connection make the intro"
                        )

                        col1, col2 = st.columns(2)
                        with col1:
                            submit_request = st.form_submit_button("Send Request", type="primary", use_container_width=True)
                        with col2:
                            cancel_request = st.form_submit_button("Cancel", use_container_width=True)

                        if submit_request:
                            if not request_message.strip():
                                st.error("Please explain why you want this introduction")
                            else:
                                # Create intro request
                                result = collaboration.create_intro_request(
                                    requester_id=user_id,
                                    connector_id=contact['connector_id'],
                                    target_contact_id=contact['contact_id'],
                                    target_name=contact['target_name'],
                                    target_company=contact['target_company'],
                                    target_position=contact['target_position'],
                                    target_email=contact['target_email'],
                                    request_message=request_message.strip(),
                                    context_for_connector=context_for_connector.strip() if context_for_connector.strip() else None
                                )

                                if result['success']:
                                    st.success(f"Introduction request sent to {contact['connector_name']}!")
                                    del st.session_state['intro_request_contact']
                                    st.rerun()
                                else:
                                    st.error(result['message'])

                        if cancel_request:
                            del st.session_state['intro_request_contact']
                            st.rerun()

                # Action buttons for selected contacts (My Network contacts only)
                # Only show if we searched My Network and have selections
                if search_my and 'selected_contacts' in st.session_state and len(st.session_state['selected_contacts']) > 0:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown(f"**{len(st.session_state['selected_contacts'])} contact(s) selected**")

                    # Email customization options
                    st.markdown("<br>", unsafe_allow_html=True)

                    col_purpose, col_tone = st.columns(2)

                    with col_purpose:
                        email_purpose = st.selectbox(
                            "What's the purpose of your email?",
                            [
                                "Just catching up / Reconnecting",
                                "I'm looking for a job",
                                "I'm looking to hire",
                                "Pitching my startup/idea",
                                "Asking for advice/mentorship",
                                "Making an introduction",
                                "Requesting a coffee chat",
                                "Seeking information/insights"
                            ],
                            key="email_purpose_selector"
                        )

                    with col_tone:
                        email_tone = st.selectbox(
                            "What tone should the email have?",
                            [
                                "Friendly & Casual",
                                "Professional & Formal",
                                "Enthusiastic & Energetic",
                                "Direct & Brief",
                                "Humble & Respectful"
                            ],
                            key="email_tone_selector"
                        )

                    # Additional context text area
                    st.markdown("<br>", unsafe_allow_html=True)
                    additional_context = st.text_area(
                        "Additional context (optional)",
                        placeholder="e.g., 'We met at the Tech Conference 2023' or 'They mentored me during my internship' or 'We worked together on Project X'",
                        help="Add any personal context about your relationship or what you know about these connections. This helps create more authentic emails.",
                        height=100,
                        key="additional_context_input"
                    )

                    # Action buttons
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if st.button("Generate Personalized Emails", use_container_width=True, type="primary"):
                            # Get selected contacts by position
                            selected_positions = sorted(list(st.session_state['selected_contacts']))
                            selected_df = filtered_df.iloc[selected_positions]

                            # Generate personalized emails with loading spinner
                            with st.spinner(f"AI is writing {len(selected_df)} personalized email(s)..."):
                                try:
                                    email_drafts = generate_personalized_emails(selected_df, email_purpose, email_tone, additional_context)
                                    st.session_state['email_drafts'] = email_drafts
                                    # Initialize to show first contact's email
                                    if 'active_email_tab' not in st.session_state:
                                        st.session_state['active_email_tab'] = 0

                                    # Log successful email generation
                                    analytics.log_email_generation(
                                        num_contacts=len(selected_df),
                                        email_purpose=email_purpose,
                                        email_tone=email_tone,
                                        success=True,
                                        session_id=st.session_state['session_id']
                                    )
                                    st.success(f"Generated {len(selected_df)} personalized email draft(s)!")
                                except Exception as e:
                                    # Log failed email generation
                                    analytics.log_email_generation(
                                        num_contacts=len(selected_df),
                                        email_purpose=email_purpose,
                                        email_tone=email_tone,
                                        success=False,
                                        session_id=st.session_state['session_id']
                                    )
                                    st.error(f"Failed to generate emails: {str(e)}")

                    with col2:
                        if st.button("Copy Contact Info", use_container_width=True):
                            selected_positions = sorted(list(st.session_state['selected_contacts']))
                            selected_df = filtered_df.iloc[selected_positions]
                            contact_info = "\n".join([
                                f"{row.get('full_name', '')} - {row.get('position', '')} at {row.get('company', '')} ({row.get('email', 'No email')})"
                                for _, row in selected_df.iterrows()
                            ])
                            st.session_state['contact_info'] = contact_info

                            # Log export
                            analytics.log_contact_export(
                                export_type="contact_info",
                                num_contacts=len(selected_df),
                                session_id=st.session_state['session_id']
                            )

                            st.success("Contact info copied! Check below.")

                    with col3:
                        # CSV export of selected
                        selected_positions = sorted(list(st.session_state['selected_contacts']))
                        selected_df = filtered_df.iloc[selected_positions]
                        csv = selected_df[display_cols].to_csv(index=False)
                        st.download_button(
                            label="Export Selected",
                            data=csv,
                            file_name="selected_contacts.csv",
                            mime="text/csv",
                            use_container_width=True
                        )

                # Display generated email drafts with tabs
                if 'email_drafts' in st.session_state and st.session_state['email_drafts']:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("### Email Drafts")

                    email_drafts = st.session_state['email_drafts']

                    # Create tabs for each person
                    if len(email_drafts) > 1:
                        tab_labels = [draft['name'] for draft in email_drafts]
                        tabs = st.tabs(tab_labels)

                        for idx, tab in enumerate(tabs):
                            with tab:
                                draft = email_drafts[idx]
                                st.markdown(f"""
                                <div style='background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;'>
                                    <div style='color: #666; font-size: 0.9rem;'>TO:</div>
                                    <div style='font-weight: 600; margin-bottom: 0.5rem;'>{draft['name']} ({draft['email']})</div>
                                    <div style='color: #666; font-size: 0.9rem;'>{draft['position']} at {draft['company']}</div>
                                </div>
                                """, unsafe_allow_html=True)

                                st.text_area(
                                    "Email draft:",
                                    value=draft['email_text'],
                                    height=350,
                                    key=f"email_text_{idx}",
                                    label_visibility="collapsed"
                                )

                                if draft.get('error'):
                                    st.error("There was an error generating this email. Please check your OpenAI API settings.")
                                else:
                                    st.info("AI-generated draft - please personalize before sending!")
                    else:
                        # Single email - no tabs needed
                        draft = email_drafts[0]
                        st.markdown(f"""
                        <div style='background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;'>
                            <div style='color: #666; font-size: 0.9rem;'>TO:</div>
                            <div style='font-weight: 600; margin-bottom: 0.5rem;'>{draft['name']} ({draft['email']})</div>
                            <div style='color: #666; font-size: 0.9rem;'>{draft['position']} at {draft['company']}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        st.text_area(
                            "Email draft:",
                            value=draft['email_text'],
                            height=350,
                            key="email_text_single",
                            label_visibility="collapsed"
                        )

                        if draft.get('error'):
                            st.error("There was an error generating this email. Please check your OpenAI API settings.")
                        else:
                            st.info("AI-generated draft - please personalize before sending!")

                    if st.button("Clear All Email Drafts"):
                        del st.session_state['email_drafts']
                        if 'active_email_tab' in st.session_state:
                            del st.session_state['active_email_tab']
                        st.rerun()

                # Display copied contact info
                if 'contact_info' in st.session_state:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("### Contact Information")
                    st.code(st.session_state['contact_info'], language="text")
                    if st.button("Clear Contact Info"):
                        del st.session_state['contact_info']
                        st.rerun()

                # Export all functionality (moved to bottom)
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("---")
                st.markdown("**Export All Results:**")
                col1, col2 = st.columns(2)

                with col1:
                    csv = filtered_df[display_cols].to_csv(index=False)
                    st.download_button(
                        label="Download All as CSV",
                        data=csv,
                        file_name="all_contacts.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                with col2:
                    text_output = "\n".join([
                        f"{row.get('full_name', '')} - {row.get('position', '')} at {row.get('company', '')}"
                        for _, row in filtered_df.iterrows()
                    ])
                    st.download_button(
                        label="Download All as TXT",
                        data=text_output,
                        file_name="all_contacts.txt",
                        mime="text/plain",
                        use_container_width=True
                    )


if __name__ == "__main__":
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        st.error("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file")
        st.stop()

    main()
