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

# Import analytics module
import analytics

# Import authentication module (needs env vars to be loaded)
import auth

# Import collaboration module
import collaboration

# Import security module
import security

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

    st.error("⚠️ OpenAI API key not found! Please check Streamlit Cloud secrets.")
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

# Modern shadcn-inspired CSS styling with gradients and glassmorphism
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        /* Modern color palette - shadcn inspired */
        --primary-50: #eff6ff;
        --primary-100: #dbeafe;
        --primary-200: #bfdbfe;
        --primary-300: #93c5fd;
        --primary-400: #60a5fa;
        --primary-500: #3b82f6;
        --primary-600: #2563eb;
        --primary-700: #1d4ed8;
        --primary-800: #1e40af;
        --primary-900: #1e3a8a;

        --secondary-500: #8b5cf6;
        --secondary-600: #7c3aed;

        --accent-500: #06b6d4;
        --accent-600: #0891b2;

        --success-500: #10b981;
        --success-600: #059669;

        --warning-500: #f59e0b;
        --warning-600: #d97706;

        --error-500: #ef4444;
        --error-600: #dc2626;

        /* Neutral colors */
        --gray-50: #f9fafb;
        --gray-100: #f3f4f6;
        --gray-200: #e5e7eb;
        --gray-300: #d1d5db;
        --gray-400: #9ca3af;
        --gray-500: #6b7280;
        --gray-600: #4b5563;
        --gray-700: #374151;
        --gray-800: #1f2937;
        --gray-900: #111827;

        /* Spacing */
        --spacing-xs: 0.5rem;
        --spacing-sm: 0.75rem;
        --spacing-md: 1rem;
        --spacing-lg: 1.5rem;
        --spacing-xl: 2rem;
        --spacing-2xl: 3rem;

        /* Radius */
        --radius-sm: 0.375rem;
        --radius-md: 0.5rem;
        --radius-lg: 0.75rem;
        --radius-xl: 1rem;
        --radius-2xl: 1.5rem;

        /* Shadows */
        --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        --shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);

        /* Glows */
        --glow-primary: 0 0 20px rgba(59, 130, 246, 0.3);
        --glow-secondary: 0 0 20px rgba(139, 92, 246, 0.3);
        --glow-success: 0 0 20px rgba(16, 185, 129, 0.3);
    }

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Main background - Gradient */
    .main {
        background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 50%, #e5e7eb 100%);
        background-attachment: fixed;
    }

    /* Content container */
    .block-container {
        padding-top: var(--spacing-lg) !important;
        padding-bottom: var(--spacing-xl);
        max-width: 1200px;
    }

    /* Sidebar styling - Modern dark with gradient */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--gray-900) 0%, var(--gray-800) 100%);
        border-right: 1px solid var(--gray-700);
        box-shadow: var(--shadow-xl);
    }

    section[data-testid="stSidebar"] > div {
        padding-top: var(--spacing-xl);
    }

    /* Sidebar text */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label {
        color: var(--gray-100) !important;
    }

    section[data-testid="stSidebar"] .stMarkdown {
        color: var(--gray-400) !important;
    }

    /* Title styling - Gradient text */
    h1 {
        background: linear-gradient(135deg, var(--primary-600) 0%, var(--secondary-500) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3.5rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.03em;
        margin-bottom: var(--spacing-md) !important;
        line-height: 1.1 !important;
        filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
    }

    /* Subtitle/description */
    .subtitle {
        color: var(--gray-600);
        font-size: 1.25rem;
        font-weight: 500;
        margin-bottom: var(--spacing-lg);
        letter-spacing: -0.01em;
        line-height: 1.6;
    }

    /* Search input styling - Modern with gradient border */
    .stTextInput > div > div > input {
        border-radius: var(--radius-xl);
        border: 2px solid transparent;
        background: white;
        background-clip: padding-box;
        padding: 1.1rem 1.75rem;
        font-size: 1.05rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        color: var(--gray-900);
        box-shadow: var(--shadow-md), inset 0 1px 2px rgba(0, 0, 0, 0.05);
        position: relative;
    }

    .stTextInput > div > div {
        position: relative;
    }

    .stTextInput > div > div::before {
        content: '';
        position: absolute;
        inset: 0;
        border-radius: var(--radius-xl);
        padding: 2px;
        background: linear-gradient(135deg, var(--primary-400), var(--secondary-500), var(--accent-500));
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
        opacity: 0;
        transition: opacity 0.3s ease;
        pointer-events: none;
    }

    .stTextInput > div > div:focus-within::before {
        opacity: 1;
    }

    .stTextInput > div > div > input:focus {
        outline: none;
        box-shadow: var(--shadow-lg), var(--glow-primary);
        transform: translateY(-1px);
    }

    .stTextInput > div > div > input::placeholder {
        color: var(--gray-400);
    }

    /* Button styling - Gradient with glow */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-700) 100%);
        color: white;
        border: none;
        border-radius: var(--radius-xl);
        padding: 0.95rem 2.75rem;
        font-weight: 600;
        font-size: 1.05rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        letter-spacing: -0.01em;
        box-shadow: var(--shadow-md), 0 0 0 rgba(59, 130, 246, 0);
        position: relative;
        overflow: hidden;
    }

    .stButton > button::before {
        content: '';
        position: absolute;
        inset: 0;
        background: linear-gradient(135deg, var(--primary-500) 0%, var(--primary-600) 100%);
        opacity: 0;
        transition: opacity 0.3s ease;
    }

    .stButton > button:hover::before {
        opacity: 1;
    }

    .stButton > button:hover {
        transform: translateY(-2px) scale(1.02);
        box-shadow: var(--shadow-xl), var(--glow-primary);
    }

    .stButton > button:active {
        transform: translateY(0) scale(0.98);
    }

    /* Form submit button styling */
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-700) 100%);
        color: white;
        border: none;
        border-radius: var(--radius-xl);
        padding: 0.95rem 2.75rem;
        font-weight: 600;
        font-size: 1.05rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        letter-spacing: -0.01em;
        box-shadow: var(--shadow-md);
    }

    .stFormSubmitButton > button:hover {
        transform: translateY(-2px) scale(1.02);
        box-shadow: var(--shadow-xl), var(--glow-primary);
    }

    /* File uploader - Modern card */
    .stFileUploader {
        background: white;
        border-radius: var(--radius-xl);
        padding: var(--spacing-xl);
        border: 2px dashed var(--gray-300);
        transition: all 0.3s ease;
        box-shadow: var(--shadow-sm);
    }

    .stFileUploader:hover {
        border-color: var(--primary-400);
        background: var(--primary-50);
        box-shadow: var(--shadow-md);
    }

    /* Dataframe styling - Modern card */
    .stDataFrame {
        border-radius: var(--radius-lg);
        overflow: hidden;
        border: 1px solid var(--gray-200);
        box-shadow: var(--shadow-md);
        background: white;
    }

    /* Success/Info boxes - Glassmorphism */
    .stSuccess {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%);
        border: 1px solid var(--success-500);
        border-radius: var(--radius-xl);
        padding: var(--spacing-lg);
        color: var(--success-600);
        backdrop-filter: blur(10px);
        box-shadow: var(--shadow-md), var(--glow-success);
        font-weight: 500;
    }

    .stInfo {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(59, 130, 246, 0.05) 100%);
        border: 1px solid var(--primary-400);
        border-radius: var(--radius-xl);
        padding: var(--spacing-lg);
        color: var(--primary-700);
        backdrop-filter: blur(10px);
        box-shadow: var(--shadow-md), var(--glow-primary);
        font-weight: 500;
    }

    .stWarning {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(245, 158, 11, 0.05) 100%);
        border: 1px solid var(--warning-500);
        border-radius: var(--radius-xl);
        padding: var(--spacing-lg);
        color: var(--warning-600);
        backdrop-filter: blur(10px);
        box-shadow: var(--shadow-md);
        font-weight: 500;
    }

    .stError {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%);
        border: 1px solid var(--error-500);
        border-radius: var(--radius-xl);
        padding: var(--spacing-lg);
        color: var(--error-600);
        backdrop-filter: blur(10px);
        box-shadow: var(--shadow-md);
        font-weight: 500;
    }

    /* Expander styling - Modern card */
    .streamlit-expanderHeader {
        background: white;
        border-radius: var(--radius-lg);
        font-weight: 600;
        color: var(--gray-800);
        border: 1px solid var(--gray-200);
        transition: all 0.2s ease;
        box-shadow: var(--shadow-sm);
    }

    .streamlit-expanderHeader:hover {
        border-color: var(--primary-300);
        background: var(--primary-50);
        box-shadow: var(--shadow-md);
        transform: translateX(4px);
    }

    /* Results summary - Glassmorphism card */
    .results-summary {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.9) 100%);
        backdrop-filter: blur(10px);
        padding: var(--spacing-xl);
        border-radius: var(--radius-2xl);
        border: 1px solid rgba(255, 255, 255, 0.8);
        margin: var(--spacing-lg) 0;
        box-shadow: var(--shadow-xl);
        transition: all 0.3s ease;
    }

    .results-summary:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-2xl);
    }

    /* Download buttons - Outlined gradient */
    .stDownloadButton > button {
        background: white;
        color: var(--primary-600);
        border: 2px solid var(--primary-500);
        border-radius: var(--radius-xl);
        padding: 0.8rem 1.75rem;
        font-weight: 600;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        letter-spacing: -0.01em;
        box-shadow: var(--shadow-sm);
        position: relative;
        overflow: hidden;
    }

    .stDownloadButton > button::before {
        content: '';
        position: absolute;
        inset: 0;
        background: linear-gradient(135deg, var(--primary-500) 0%, var(--primary-600) 100%);
        opacity: 0;
        transition: opacity 0.3s ease;
        z-index: -1;
    }

    .stDownloadButton > button:hover::before {
        opacity: 1;
    }

    .stDownloadButton > button:hover {
        color: white;
        border-color: var(--primary-600);
        transform: translateY(-2px);
        box-shadow: var(--shadow-lg), var(--glow-primary);
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Section headers - Gradient underline */
    h2, h3 {
        color: var(--gray-800) !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        position: relative;
        padding-bottom: var(--spacing-sm);
    }

    h2::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 60px;
        height: 4px;
        background: linear-gradient(90deg, var(--primary-500) 0%, var(--secondary-500) 100%);
        border-radius: 2px;
    }

    /* Animations */
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes slideInFromLeft {
        from {
            opacity: 0;
            transform: translateX(-30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    @keyframes shimmer {
        0% {
            background-position: -1000px 0;
        }
        100% {
            background-position: 1000px 0;
        }
    }

    .main > div {
        animation: fadeIn 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* Markdown text */
    .main .stMarkdown {
        color: var(--gray-600);
        line-height: 1.7;
    }

    /* Dividers - Gradient */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent 0%, var(--primary-300) 50%, transparent 100%);
        margin: var(--spacing-xl) 0;
    }

    /* Badge component */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: var(--radius-md);
        font-size: 0.875rem;
        font-weight: 600;
        background: linear-gradient(135deg, var(--primary-500) 0%, var(--secondary-500) 100%);
        color: white;
        box-shadow: var(--shadow-sm);
    }

    .badge-success {
        background: linear-gradient(135deg, var(--success-500) 0%, var(--success-600) 100%);
    }

    .badge-warning {
        background: linear-gradient(135deg, var(--warning-500) 0%, var(--warning-600) 100%);
    }

    /* Card component */
    .card {
        background: white;
        border-radius: var(--radius-xl);
        padding: var(--spacing-xl);
        box-shadow: var(--shadow-md);
        border: 1px solid var(--gray-200);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .card:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-2xl);
        border-color: var(--primary-300);
    }

    /* ============================================
       MOBILE RESPONSIVE STYLES
       ============================================ */

    @media (max-width: 768px) {
        h1 {
            font-size: 2.25rem !important;
        }

        .subtitle {
            font-size: 1.05rem;
            margin-bottom: var(--spacing-xl);
        }

        .block-container {
            padding-top: var(--spacing-md);
            padding-left: var(--spacing-md);
            padding-right: var(--spacing-md);
        }

        section[data-testid="stSidebar"] {
            width: 280px !important;
        }

        .stButton > button,
        .stFormSubmitButton > button {
            width: 100%;
            padding: 1rem 1.5rem;
            font-size: 1rem;
        }

        .row-widget.stColumns {
            flex-direction: column !important;
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
            padding: 0.9rem 1.25rem;
            font-size: 0.95rem;
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
       TAB STYLING - Modern gradient tabs
       ============================================ */

    .stTabs {
        background: white;
        border-radius: var(--radius-xl);
        padding: var(--spacing-sm);
        border: 1px solid var(--gray-200);
        box-shadow: var(--shadow-md);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: var(--spacing-xs);
        background: var(--gray-50);
        padding: var(--spacing-xs);
        border-radius: var(--radius-lg);
    }

    .stTabs [data-baseweb="tab"] {
        background: white;
        border: 2px solid var(--gray-200);
        border-radius: var(--radius-md);
        padding: 0.875rem 1.75rem;
        font-weight: 600;
        color: var(--gray-700);
        font-size: 1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: var(--shadow-sm);
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: var(--primary-50);
        border-color: var(--primary-300);
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
        color: var(--primary-700);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary-600) 0%, var(--secondary-500) 100%) !important;
        color: white !important;
        border-color: transparent !important;
        box-shadow: var(--shadow-lg), var(--glow-primary) !important;
        transform: translateY(-2px);
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
                st.info(f"🔍 Found LinkedIn headers at row {i + 1}")
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
        st.success(f"✅ Loaded {len(df)} connections with columns: {', '.join(df.columns.tolist()[:10])}")

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
                f"❌ This doesn't look like a LinkedIn Connections export.\n\n"
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
            st.error("❌ **Insufficient quota** - Your OpenAI credits have run out or billing is not set up.")
            st.info("💡 Go to https://platform.openai.com/account/billing and add a payment method")
        elif "invalid_api_key" in error_msg.lower():
            st.error("❌ **Invalid API key** - The API key is incorrect or expired.")
        elif "rate_limit" in error_msg.lower():
            st.warning("⏱️ **Rate limit exceeded** - Too many requests. Please wait a moment and try again.")
        elif "timeout" in error_msg.lower():
            st.warning("⏱️ **Request timeout** - The API took too long to respond. Try again.")
        else:
            st.error("Please check: 1) Your API key is valid, 2) You have credits/billing set up, 3) Your internet connection")
            st.info("💡 Check your OpenAI account: https://platform.openai.com/account/billing")

        # Show full error in expander for debugging
        with st.expander("🔍 Full error details (for debugging)"):
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
    st.markdown("<h1 style='text-align: center; margin-top: 2rem;'>🔐 Login to LinkedIn Network Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666; margin-bottom: 3rem;'>Access your personalized network dashboard</p>", unsafe_allow_html=True)

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        with st.form("login_form"):
            st.markdown("### Sign In")
            email = st.text_input("Email", placeholder="your@email.com")
            password = st.text_input("Password", type="password", placeholder="Enter your password")

            submit = st.form_submit_button("🚀 Login", use_container_width=True)

            if submit:
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

                            # Log login attempt
                            security.log_login_attempt(email, result['success'])

                            if result['success']:
                                # Check if email is verified
                                supabase = auth.get_supabase_client()
                                user_data = supabase.table('users').select('email_verified').eq('id', result['user']['id']).execute()

                                if user_data.data and not user_data.data[0].get('email_verified', False):
                                    st.warning("⚠️ Please verify your email to continue. Check your inbox for the verification link.")

                                    # Show resend verification button
                                    if st.button("📧 Resend Verification Email"):
                                        security.send_verification_email(
                                            result['user']['id'],
                                            result['user']['email'],
                                            result['user']['full_name']
                                        )
                                        st.info("✅ Verification email sent!")
                                    return

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
                                st.error(result['message'])
                                if rate_limit.get('remaining_attempts'):
                                    st.caption(f"Remaining attempts: {rate_limit['remaining_attempts']}")
                        except Exception as e:
                            st.error(f"❌ Login failed: {str(e)}")
                            with st.expander("Technical Details"):
                                st.code(str(e))
                                st.caption("If this error persists, please contact support.")

        # Forgot password link
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔑 Forgot Password?", use_container_width=True, type="secondary"):
                st.session_state['show_forgot_password'] = True
                st.rerun()
        with col2:
            pass  # Empty column for spacing

        st.markdown("---")
        st.markdown("<p style='text-align: center;'>Don't have an account?</p>", unsafe_allow_html=True)

        if st.button("📝 Create New Account", use_container_width=True):
            st.session_state['show_register'] = True
            st.rerun()

def show_forgot_password_page():
    """Display forgot password page"""
    st.markdown("<h1 style='text-align: center; margin-top: 2rem;'>🔑 Reset Your Password</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666; margin-bottom: 3rem;'>Enter your email to receive a password reset link</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        with st.form("forgot_password_form"):
            st.markdown("### Password Reset")
            email = st.text_input("Email Address", placeholder="your@email.com")

            submit = st.form_submit_button("📧 Send Reset Link", use_container_width=True)

            if submit:
                email = email.strip() if email else ""

                if not email:
                    st.error("Please enter your email address")
                else:
                    with st.spinner("Sending reset link..."):
                        result = security.request_password_reset(email)
                        st.success(result['message'])
                        st.info("If the email exists in our system, you'll receive a reset link shortly. Please check your inbox (and spam folder).")

        st.markdown("---")

        if st.button("⬅️ Back to Login", use_container_width=True):
            st.session_state['show_forgot_password'] = False
            st.rerun()


def show_password_reset_form(token):
    """Display password reset form (when user clicks email link)"""
    st.markdown("<h1 style='text-align: center; margin-top: 2rem;'>🔒 Set New Password</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666; margin-bottom: 3rem;'>Create a strong new password</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        with st.form("reset_password_form"):
            st.markdown("### New Password")

            new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter new password")

            submit = st.form_submit_button("✅ Reset Password", use_container_width=True)

            if submit:
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
                            st.success(result['message'])
                            st.info("You can now log in with your new password.")

                            # Clear query params and go to login
                            if st.button("Go to Login", type="primary"):
                                st.session_state['show_register'] = False
                                st.query_params.clear()
                                st.rerun()
                        else:
                            st.error(result['message'])


def show_register_page():
    """Display registration page"""
    st.markdown("<h1 style='text-align: center; margin-top: 2rem;'>📝 Create Your Account</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666; margin-bottom: 3rem;'>Join LinkedIn Network Assistant today</p>", unsafe_allow_html=True)

    # Center the registration form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        with st.form("register_form"):
            st.markdown("### Create Account")
            full_name = st.text_input("Full Name", placeholder="John Doe")
            organization = st.text_input("Organization (Optional)", placeholder="e.g., Acme Inc, Stanford University")
            email = st.text_input("Email", placeholder="your@email.com")
            password = st.text_input("Password", type="password", placeholder="Create a strong password")
            password_confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter your password")

            submit = st.form_submit_button("✨ Create Account", use_container_width=True)

            if submit:
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
                                    st.info("📧 Verification email sent! Please check your inbox and click the verification link to activate your account.")
                                else:
                                    st.warning("⚠️ Account created but verification email could not be sent. You can still log in, but some features may be limited.")

                                st.session_state['show_register'] = False
                                # Wait a moment then redirect to login
                                import time
                                time.sleep(3)
                                st.rerun()
                            else:
                                st.error(result['message'])
                        except Exception as e:
                            st.error(f"❌ Registration failed: {str(e)}")
                            with st.expander("Technical Details"):
                                st.code(str(e))
                                st.caption("If this error persists, please contact support.")

        st.markdown("---")
        st.markdown("<p style='text-align: center;'>Already have an account?</p>", unsafe_allow_html=True)

        if st.button("🔐 Back to Login", use_container_width=True):
            st.session_state['show_register'] = False
            st.rerun()

# Main app
def main():
    # Handle URL parameters for password reset and email verification
    query_params = st.query_params

    # Handle email verification token
    if 'verify_email' in query_params:
        token = query_params['verify_email']
        st.markdown("<h1 style='text-align: center; margin-top: 2rem;'>✅ Email Verification</h1>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.spinner("Verifying your email..."):
                result = security.verify_email_token(token)

                if result['success']:
                    st.success(result['message'])
                    st.balloons()
                    if st.button("🚀 Go to Login", type="primary", use_container_width=True):
                        st.query_params.clear()
                        st.rerun()
                else:
                    st.error(result['message'])
                    if st.button("⬅️ Back to Home", use_container_width=True):
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

    # Authentication guard - show login/register if not authenticated
    if not st.session_state['authenticated']:
        if st.session_state['show_register']:
            show_register_page()
        elif st.session_state['show_forgot_password']:
            show_forgot_password_page()
        else:
            show_login_page()
        return  # Stop here if not authenticated

    # Phase 3B: Migrate existing users to new search (one-time index build)
    if HAS_NEW_SEARCH:
        migrate_to_new_search()

    # Sidebar - Restructured Layout
    with st.sidebar:
        # === TOP SECTION: User Info ===
        st.markdown("### 👤 Account")
        st.markdown(f"**{st.session_state['user']['full_name']}**")
        st.markdown(f"*{st.session_state['user']['email']}*")

        # Show contact count
        contact_count = auth.get_contact_count(st.session_state['user']['id'])
        if contact_count > 0:
            st.markdown(f"**📇 {contact_count:,} contacts**")
        else:
            st.markdown("**📇 No contacts yet**")

        # Hide auto-generated page navigation from top for everyone
        st.markdown("""
        <style>
            /* Hide the auto-generated page navigation at top */
            section[data-testid="stSidebarNav"] {
                display: none !important;
            }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("---")


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

    # Hero section with premium styling - heading and toggle in same row
    col_heading, col_toggle = st.columns([10, 1])

    with col_heading:
        st.markdown("<h1 style='margin-top: 0;'>LinkedIn Network Assistant</h1>", unsafe_allow_html=True)
        st.markdown('<p class="subtitle">Unlock the power of your network with AI-driven insights</p>', unsafe_allow_html=True)

    with col_toggle:
        st.markdown("<div style='padding-top: 2rem;'></div>", unsafe_allow_html=True)  # Spacer to align with heading
        dark_mode_toggle = st.toggle(
            "🌙",
            value=st.session_state.get('dark_mode', False),
            key="dark_mode_toggle",
            help="Toggle dark mode"
        )

        # Update dark mode state if toggle changed
        if dark_mode_toggle != st.session_state.get('dark_mode', False):
            st.session_state['dark_mode'] = dark_mode_toggle
            st.rerun()

    # === MIDDLE SECTION: CSV Upload ===
    with st.sidebar:
        st.markdown("### 📤 Upload Contacts")
        st.markdown("Export your LinkedIn contacts as CSV and upload here.")

        # Check if user already has contacts
        user_has_contacts = auth.get_contact_count(st.session_state['user']['id']) > 0

        # Show replace option if user has contacts
        replace_contacts = False
        if user_has_contacts:
            st.warning(f"⚠️ You already have contacts saved. Upload a new CSV to replace them.")
            replace_contacts = st.checkbox("Replace existing contacts", value=False,
                                         help="Check this to delete your current contacts and upload new ones")

        uploaded_file = st.file_uploader(
            "Choose your LinkedIn CSV file",
            type=['csv'],
            help="Download your LinkedIn connections and upload the CSV file",
            label_visibility="collapsed"
        )

        if uploaded_file:
            with st.spinner("✨ Parsing contacts..."):
                df = parse_linkedin_csv(uploaded_file)
                if df is not None:
                    st.session_state['contacts_df'] = df
                    user_id = st.session_state['user']['id']

                    # Check if we need to replace contacts
                    if user_has_contacts:
                        if not replace_contacts:
                            st.warning(f"⚠️ You already have contacts saved. Check 'Replace existing contacts' to upload new ones.")
                            st.info(f"✅ Loaded {len(df)} contacts to current session (not saved to database)")
                        else:
                            # Delete old contacts first
                            with st.spinner("Deleting old contacts..."):
                                if auth.delete_user_contacts(user_id):
                                    # Save new contacts
                                    save_result = auth.save_contacts_to_db(user_id, df)
                                    if save_result['success']:
                                        st.success(f"✅ Replaced with {len(df)} new contacts!")
                                    else:
                                        st.error(f"❌ Error saving: {save_result['message']}")
                                else:
                                    st.error("❌ Error deleting old contacts")
                    else:
                        # No existing contacts, just save
                        save_result = auth.save_contacts_to_db(user_id, df)
                        if save_result['success']:
                            st.success(f"✅ Loaded and saved {len(df)} contacts to your account!")
                        else:
                            st.warning(f"✅ Loaded {len(df)} contacts (saved to session only - DB error: {save_result['message']})")

                    # Log CSV upload
                    analytics.log_csv_upload(
                        file_name=uploaded_file.name,
                        num_contacts=len(df),
                        success=True,
                        session_id=st.session_state['session_id']
                    )

                    # Phase 3B: Build search indexes for fast future searches
                    if HAS_NEW_SEARCH:
                        with st.spinner("🔨 Building search indexes for faster searches..."):
                            try:
                                initialize_search_for_user(user_id, df)
                                st.success("✅ Search indexes built! Searches will be 25x faster.")
                            except Exception as e:
                                st.warning(f"⚠️ Could not build search indexes (will use legacy search): {e}")

                    # Show preview
                    with st.expander("👀 Preview contacts"):
                        display_cols = [col for col in ['full_name', 'position', 'company'] if col in df.columns]
                        st.dataframe(df[display_cols].head(10), use_container_width=True)
                else:
                    # Log failed upload
                    analytics.log_csv_upload(
                        file_name=uploaded_file.name,
                        num_contacts=0,
                        success=False,
                        error_message="Failed to parse CSV",
                        session_id=st.session_state['session_id']
                    )

        st.markdown("---")

        # === BOTTOM SECTION: Logout Button ===
        st.markdown("### 🚪 Account Actions")
        if st.button("🚪 Logout", use_container_width=True, type="primary", key="logout_button"):
            # Clear session
            st.session_state['authenticated'] = False
            st.session_state['user'] = None
            if 'contacts_df' in st.session_state:
                del st.session_state['contacts_df']
            st.success("Logged out successfully!")
            st.rerun()

        # Admin-only page navigation at bottom
        admin_email = "rohan.gandotra19@gmail.com"
        if st.session_state['user']['email'] == admin_email:
            st.markdown("---")
            st.markdown("### 📊 Pages")
            st.page_link("app.py", label="🏠 Home", icon="🏠")
            st.page_link("pages/Analytics.py", label="📈 Analytics", icon="📈")

        # Diagnostic section (collapsed by default)
        st.markdown("---")
        with st.expander("🔧 Diagnostics", expanded=False):
            if st.button("Run API Connection Test", key="diagnostic_button"):
                with st.spinner("Running diagnostic tests..."):
                    diagnostic_results = run_diagnostic_test()
                    st.session_state['diagnostic_results'] = diagnostic_results

            # Display diagnostic results if available
            if 'diagnostic_results' in st.session_state:
                results = st.session_state['diagnostic_results']

                # API Key Status
                if results['api_key_loaded']:
                    st.success(f"✅ API Key: Loaded ({results.get('api_key_format', 'N/A')})")
                else:
                    st.error(f"❌ API Key: {results.get('api_key_format', 'Not loaded')}")

                # Direct HTTP Test
                http_status = results['direct_http_test']['status']
                if http_status == 'success':
                    st.success(f"✅ Direct HTTP: {results['direct_http_test']['details']}")
                elif http_status == 'pending':
                    st.info("⏳ Direct HTTP: Not tested")
                else:
                    st.error(f"❌ Direct HTTP: {http_status}")
                    with st.expander("HTTP Error Details"):
                        st.code(results['direct_http_test']['details'])
                        if 'traceback' in results['direct_http_test']:
                            st.code(results['direct_http_test']['traceback'])

                # OpenAI SDK Test
                sdk_status = results['openai_sdk_test']['status']
                if sdk_status == 'success':
                    st.success(f"✅ OpenAI SDK: {results['openai_sdk_test']['details']}")
                elif sdk_status == 'pending':
                    st.info("⏳ OpenAI SDK: Not tested")
                else:
                    st.error(f"❌ OpenAI SDK: {sdk_status}")
                    with st.expander("SDK Error Details"):
                        st.code(results['openai_sdk_test']['details'])
                        if 'traceback' in results['openai_sdk_test']:
                            st.code(results['openai_sdk_test']['traceback'])

                # Clear results button
                if st.button("Clear Diagnostic Results"):
                    del st.session_state['diagnostic_results']
                    st.rerun()

    # Get user_id for use throughout the app
    user_id = st.session_state['user']['id']

    # Main content area
    if 'contacts_df' not in st.session_state:
        # Modern empty state with glassmorphism
        st.markdown("""<div style='text-align: center; padding: 3rem 2rem; margin: 2rem 0; background: linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%); border-radius: var(--radius-2xl); border: 2px dashed var(--primary-300);'>
<div style='font-size: 4rem; margin-bottom: 1rem;'>🚀</div>
<h2 style='background: linear-gradient(135deg, var(--primary-600) 0%, var(--secondary-500) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; font-size: 2rem; font-weight: 700; margin-bottom: 0.75rem;'>Get Started with Your Network</h2>
<p style='color: var(--gray-600); font-size: 1.15rem; max-width: 600px; margin: 0 auto 1.5rem;'>Upload your LinkedIn connections to unlock powerful AI-powered search and insights</p>
<div style='display: inline-block; padding: 0.75rem 2rem; background: linear-gradient(135deg, var(--primary-500) 0%, var(--primary-600) 100%); color: white; border-radius: var(--radius-xl); font-weight: 600; box-shadow: var(--shadow-lg), var(--glow-primary);'>👈 Upload your contacts in the sidebar to begin</div>
</div>""", unsafe_allow_html=True)

        # LinkedIn Download Instructions - Modern card
        st.markdown("### 📥 How to Get Your LinkedIn Data")
        st.markdown("""<div class='card' style='background: linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(255, 255, 255, 1) 100%); padding: var(--spacing-xl); border-radius: var(--radius-2xl); border: 2px solid var(--primary-200); margin-bottom: 2rem; box-shadow: var(--shadow-lg);'>
<div style='display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;'>
<div style='width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, var(--primary-500) 0%, var(--primary-600) 100%); display: flex; align-items: center; justify-content: center; font-size: 1.5rem; box-shadow: var(--shadow-md), var(--glow-primary);'>📥</div>
<div style='font-size: 1.3rem; font-weight: 700; color: var(--gray-900);'>Simple 6-Step Process</div>
</div>
<div style='display: grid; gap: 1rem;'>
<div style='display: flex; gap: 1rem; align-items: start;'>
<div style='flex-shrink: 0; width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, var(--primary-500) 0%, var(--secondary-500) 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 0.9rem; box-shadow: var(--shadow-sm);'>1</div>
<div style='flex: 1; padding-top: 0.25rem;'>Go to <a href='https://www.linkedin.com/mypreferences/d/download-my-data' target='_blank' style='color: var(--primary-600); font-weight: 600; text-decoration: none; border-bottom: 2px solid var(--primary-300);'>LinkedIn Data Download</a></div>
</div>
<div style='display: flex; gap: 1rem; align-items: start;'>
<div style='flex-shrink: 0; width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, var(--primary-500) 0%, var(--secondary-500) 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 0.9rem; box-shadow: var(--shadow-sm);'>2</div>
<div style='flex: 1; padding-top: 0.25rem; color: var(--gray-700);'>Click <strong style='color: var(--gray-900);'>"Request archive"</strong> (the big button at the top)</div>
</div>
<div style='display: flex; gap: 1rem; align-items: start;'>
<div style='flex-shrink: 0; width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, var(--primary-500) 0%, var(--secondary-500) 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 0.9rem; box-shadow: var(--shadow-sm);'>3</div>
<div style='flex: 1; padding-top: 0.25rem; color: var(--gray-700);'>LinkedIn will email you in <strong style='color: var(--gray-900);'>10-15 minutes</strong> when your data is ready</div>
</div>
<div style='display: flex; gap: 1rem; align-items: start;'>
<div style='flex-shrink: 0; width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, var(--primary-500) 0%, var(--secondary-500) 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 0.9rem; box-shadow: var(--shadow-sm);'>4</div>
<div style='flex: 1; padding-top: 0.25rem; color: var(--gray-700);'>Download the <strong style='color: var(--gray-900);'>ZIP file</strong> from the email</div>
</div>
<div style='display: flex; gap: 1rem; align-items: start;'>
<div style='flex-shrink: 0; width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, var(--primary-500) 0%, var(--secondary-500) 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 0.9rem; box-shadow: var(--shadow-sm);'>5</div>
<div style='flex: 1; padding-top: 0.25rem; color: var(--gray-700);'>Extract/unzip it and find the <strong style='color: var(--gray-900);'>Connections.csv</strong> file</div>
</div>
<div style='display: flex; gap: 1rem; align-items: start;'>
<div style='flex-shrink: 0; width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, var(--success-500) 0%, var(--success-600) 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 0.9rem; box-shadow: var(--shadow-sm), var(--glow-success);'>6</div>
<div style='flex: 1; padding-top: 0.25rem; color: var(--gray-700);'>Upload that file here using the sidebar 👈</div>
</div>
</div>
<div style='margin-top: 1.5rem; padding: 1rem; background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%); border-radius: var(--radius-lg); border-left: 4px solid var(--primary-500);'>
<div style='display: flex; align-items: center; gap: 0.5rem;'>
<span style='font-size: 1.25rem;'>💡</span>
<span style='color: var(--gray-700); font-weight: 500;'><strong style='color: var(--gray-900);'>Tip:</strong> The CSV file should have columns like "First Name", "Last Name", "Company", "Position"</span>
</div>
</div>
</div>""", unsafe_allow_html=True)

        # Example queries in modern gradient cards
        st.markdown("### ✨ What You Can Ask")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""<div class='card' style='background: white; padding: var(--spacing-xl); border-radius: var(--radius-xl); border: 2px solid var(--gray-200); box-shadow: var(--shadow-md); height: 100%; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); position: relative; overflow: hidden;'>
<div style='position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, var(--primary-500) 0%, var(--secondary-500) 100%);'></div>
<div style='font-size: 2.5rem; margin-bottom: 1rem;'>🏢</div>
<h4 style='margin-bottom: 1rem; color: var(--gray-900); font-weight: 700; font-size: 1.15rem;'>By Industry</h4>
<p style='color: var(--gray-600); margin-bottom: 0.5rem; font-size: 0.95rem; line-height: 1.5;'>"Who works in venture capital?"</p>
<p style='color: var(--gray-600); font-size: 0.95rem; line-height: 1.5;'>"Show me people in tech companies"</p>
</div>""", unsafe_allow_html=True)

        with col2:
            st.markdown("""<div class='card' style='background: white; padding: var(--spacing-xl); border-radius: var(--radius-xl); border: 2px solid var(--gray-200); box-shadow: var(--shadow-md); height: 100%; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); position: relative; overflow: hidden;'>
<div style='position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, var(--secondary-500) 0%, var(--accent-500) 100%);'></div>
<div style='font-size: 2.5rem; margin-bottom: 1rem;'>👔</div>
<h4 style='margin-bottom: 1rem; color: var(--gray-900); font-weight: 700; font-size: 1.15rem;'>By Role</h4>
<p style='color: var(--gray-600); margin-bottom: 0.5rem; font-size: 0.95rem; line-height: 1.5;'>"Who is an engineer?"</p>
<p style='color: var(--gray-600); font-size: 0.95rem; line-height: 1.5;'>"Show me product managers"</p>
</div>""", unsafe_allow_html=True)

        with col3:
            st.markdown("""<div class='card' style='background: white; padding: var(--spacing-xl); border-radius: var(--radius-xl); border: 2px solid var(--gray-200); box-shadow: var(--shadow-md); height: 100%; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); position: relative; overflow: hidden;'>
<div style='position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, var(--accent-500) 0%, var(--primary-500) 100%);'></div>
<div style='font-size: 2.5rem; margin-bottom: 1rem;'>⭐</div>
<h4 style='margin-bottom: 1rem; color: var(--gray-900); font-weight: 700; font-size: 1.15rem;'>By Seniority</h4>
<p style='color: var(--gray-600); margin-bottom: 0.5rem; font-size: 0.95rem; line-height: 1.5;'>"Who is the most senior person?"</p>
<p style='color: var(--gray-600); font-size: 0.95rem; line-height: 1.5;'>"Show me top 5 leaders"</p>
</div>""", unsafe_allow_html=True)

    else:
        contacts_df = st.session_state['contacts_df']

        # Unified Search Interface - handles both search and analytics
        with st.form(key='unified_search_form', clear_on_submit=False):
            query = st.text_input(
                "Ask anything about your network...",
                placeholder='e.g., "Who works in venture capital?" or "What industry do I have most contacts in?"',
                label_visibility="collapsed",
                key="unified_search_query"
            )

            # Submit button (triggered by Enter or click)
            search_button = st.form_submit_button("🔍 Search", type="primary")

        # Example questions in expander
        with st.expander("💡 Example Questions", expanded=False):
            st.markdown("""
            **Search for People:**
            - Who works in venture capital?
            - Show me people in tech companies
            - Who is the most senior person?
            - Find engineers at Google

            **Network Analytics:**
            - What industry do I have most contacts in?
            - How many people work at tech companies?
            - Which companies are most represented?
            - What percentage of my contacts are in finance?
            - Summarize my network for me
            """)

        if search_button and query:
            # Classify query type
            query_type = classify_query_type(query)

            if query_type == "analytics":
                # Handle analytics query
                with st.spinner("🧠 AI is analyzing your network..."):
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
                        st.error(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
            else:
                # Handle search query (find people)
                # Phase 3B: Use new hybrid search for 95% cost reduction + 25x speed
                if HAS_NEW_SEARCH:
                    with st.spinner("⚡ Searching your network..."):
                        # Clear any previous analytics result
                        if 'analytics_result' in st.session_state:
                            del st.session_state['analytics_result']

                        try:
                            # Use new hybrid search
                            search_result = smart_search(query, contacts_df)

                            if search_result.get('use_legacy_gpt'):
                                # Complex query - fall back to old GPT search
                                st.caption("⚙️ Using AI reasoning for complex query...")
                                intent = extract_search_intent(query, contacts_df)

                                if intent:
                                    st.session_state['last_intent'] = intent
                                    filtered_df = filter_contacts(contacts_df, intent)
                                    st.session_state['filtered_df'] = filtered_df
                                    summary = generate_summary(filtered_df, intent)
                                    st.session_state['summary'] = summary
                            else:
                                # Fast hybrid search result
                                filtered_df = search_result.get('filtered_df', pd.DataFrame())
                                st.session_state['filtered_df'] = filtered_df

                                # Generate summary
                                if not filtered_df.empty:
                                    # Use new search summary
                                    summary_text = get_search_summary(search_result, query)
                                    tier_info = f" • Method: {search_result.get('tier_used', 'unknown')}"
                                    latency_info = f" • Time: {search_result.get('latency_ms', 0):.0f}ms"
                                    cached_info = " • ⚡ Cached" if search_result.get('cached') else ""

                                    summary = f"""
                                    <strong>Search Results for "{query}"</strong><br>
                                    ✅ Found {len(filtered_df)} matches{tier_info}{latency_info}{cached_info}
                                    """
                                else:
                                    summary = f"No results found for '{query}'"

                                st.session_state['summary'] = summary

                                # Show performance badge
                                if search_result.get('cached'):
                                    st.success(f"⚡ Instant search (cached) • {len(filtered_df)} results")
                                elif search_result.get('latency_ms', 0) < 100:
                                    st.success(f"⚡ Lightning fast ({search_result.get('latency_ms', 0):.0f}ms) • {len(filtered_df)} results")

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
                    with st.spinner("🔍 Searching your network..."):
                        intent = extract_search_intent(query, contacts_df)

                        if intent:
                            st.session_state['last_intent'] = intent

                            # Clear any previous analytics result
                            if 'analytics_result' in st.session_state:
                                del st.session_state['analytics_result']

                            # Debug: Show what the AI understood
                            with st.expander("🔍 Debug: What the AI understood from your query"):
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
            st.markdown("### 💡 AI Insights")
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

                # Selection header with action buttons and pagination info
                col_header1, col_header2, col_header3 = st.columns([2, 1, 1])
                with col_header1:
                    st.markdown("### 📋 Select Contacts")
                with col_header2:
                    st.markdown(f"<div style='text-align: right; padding-top: 0.5rem; color: #666;'>Page {current_page} of {total_pages}</div>", unsafe_allow_html=True)
                with col_header3:
                    select_all_page = st.checkbox("Select All on Page", key="select_all_page_checkbox")

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

                # Handle select all on page
                if select_all_page:
                    for i in range(start_idx, end_idx):
                        st.session_state['selected_contacts'].add(i)
                elif not select_all_page:
                    # Check if all on current page are selected, if so deselect
                    all_on_page_selected = all(i in st.session_state['selected_contacts'] for i in range(start_idx, end_idx))
                    if all_on_page_selected:
                        for i in range(start_idx, end_idx):
                            st.session_state['selected_contacts'].discard(i)

                # Display each contact as a selectable card
                for page_idx, (idx, row) in enumerate(page_contacts.iterrows()):
                    # Actual index in the full filtered_df
                    actual_idx = start_idx + page_idx
                    contact_selected = actual_idx in st.session_state['selected_contacts']

                    col1, col2 = st.columns([0.1, 0.9])

                    with col1:
                        if st.checkbox("", key=f"contact_{actual_idx}_{idx}", value=contact_selected, label_visibility="collapsed"):
                            st.session_state['selected_contacts'].add(actual_idx)
                        else:
                            st.session_state['selected_contacts'].discard(actual_idx)

                    with col2:
                        name = row.get('full_name', 'No Name')
                        job_position = row.get('position', 'No Position')
                        company = row.get('company', 'No Company')
                        email = row.get('email', '')

                        # Modern contact card with gradient border and hover effects
                        st.markdown(f"""
                        <div class='contact-card' style='
                            background: white;
                            padding: 1.25rem;
                            border-radius: var(--radius-xl);
                            border: 2px solid var(--gray-200);
                            margin-bottom: 0.75rem;
                            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                            box-shadow: var(--shadow-sm);
                            position: relative;
                            overflow: hidden;
                        '>
                            <div style='position: absolute; top: 0; left: 0; right: 0; height: 4px;
                                        background: linear-gradient(90deg, var(--primary-500) 0%, var(--secondary-500) 50%, var(--accent-500) 100%);
                                        opacity: 0;
                                        transition: opacity 0.3s ease;'
                                 class='card-gradient-bar'>
                            </div>

                            <div style='display: flex; align-items: flex-start; gap: 1rem;'>
                                <div style='flex-shrink: 0;
                                            width: 48px;
                                            height: 48px;
                                            border-radius: 50%;
                                            background: linear-gradient(135deg, var(--primary-500) 0%, var(--secondary-500) 100%);
                                            display: flex;
                                            align-items: center;
                                            justify-content: center;
                                            color: white;
                                            font-weight: 700;
                                            font-size: 1.25rem;
                                            box-shadow: var(--shadow-md);'>
                                    {name[0].upper() if name and name != 'No Name' else '?'}
                                </div>

                                <div style='flex: 1; min-width: 0;'>
                                    <div style='font-weight: 700;
                                                font-size: 1.1rem;
                                                color: var(--gray-900);
                                                margin-bottom: 0.35rem;
                                                line-height: 1.3;'>
                                        {name}
                                    </div>
                                    <div style='color: var(--gray-600);
                                                font-size: 0.95rem;
                                                font-weight: 500;
                                                margin-bottom: 0.35rem;
                                                line-height: 1.4;'>
                                        {job_position}
                                    </div>
                                    <div style='display: flex;
                                                align-items: center;
                                                gap: 0.5rem;
                                                flex-wrap: wrap;'>
                                        <span style='color: var(--gray-500);
                                                     font-size: 0.9rem;
                                                     display: inline-flex;
                                                     align-items: center;
                                                     gap: 0.25rem;'>
                                            🏢 {company}
                                        </span>
                                        {f'<span style="color: var(--gray-400);">•</span><span style="color: var(--primary-600); font-size: 0.85rem; font-weight: 500;">✉️ {email}</span>' if email else ''}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <style>
                        .contact-card:hover {{
                            transform: translateY(-3px) translateX(4px);
                            box-shadow: var(--shadow-xl);
                            border-color: var(--primary-300);
                        }}

                        .contact-card:hover .card-gradient-bar {{
                            opacity: 1;
                        }}
                        </style>
                        """, unsafe_allow_html=True)

                # Pagination controls
                if total_pages > 1:
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_prev, col_pages, col_next = st.columns([1, 3, 1])

                    with col_prev:
                        if st.button("⬅️ Previous", disabled=(current_page == 1), use_container_width=True):
                            st.session_state['current_page'] = max(1, current_page - 1)
                            st.rerun()

                    with col_pages:
                        # Show page numbers
                        page_buttons = []
                        # Show first page, current page -1, current page, current page +1, last page
                        pages_to_show = {1, max(1, current_page - 1), current_page, min(total_pages, current_page + 1), total_pages}
                        pages_to_show = sorted(pages_to_show)

                        cols = st.columns(len(pages_to_show))
                        for i, page_num in enumerate(pages_to_show):
                            with cols[i]:
                                if page_num == current_page:
                                    st.markdown(f"<div style='text-align: center; padding: 0.5rem; background: #1a1a1a; color: white; border-radius: 8px; font-weight: 600;'>{page_num}</div>", unsafe_allow_html=True)
                                else:
                                    if st.button(str(page_num), key=f"page_{page_num}", use_container_width=True):
                                        st.session_state['current_page'] = page_num
                                        st.rerun()

                    with col_next:
                        if st.button("Next ➡️", disabled=(current_page == total_pages), use_container_width=True):
                            st.session_state['current_page'] = min(total_pages, current_page + 1)
                            st.rerun()

                    st.markdown(f"<div style='text-align: center; color: #666; margin-top: 0.5rem; font-size: 0.9rem;'>Showing {start_idx + 1}-{end_idx} of {total_contacts} contacts</div>", unsafe_allow_html=True)

                # Action buttons for selected contacts
                if len(st.session_state['selected_contacts']) > 0:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown(f"**{len(st.session_state['selected_contacts'])} contact(s) selected**")

                    # Email customization options
                    st.markdown("<br>", unsafe_allow_html=True)

                    col_purpose, col_tone = st.columns(2)

                    with col_purpose:
                        email_purpose = st.selectbox(
                            "What's the purpose of your email?",
                            [
                                "🤝 Just catching up / Reconnecting",
                                "💼 I'm looking for a job",
                                "👥 I'm looking to hire",
                                "🚀 Pitching my startup/idea",
                                "💡 Asking for advice/mentorship",
                                "🔗 Making an introduction",
                                "☕ Requesting a coffee chat",
                                "📚 Seeking information/insights"
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
                        "💡 Additional context (optional)",
                        placeholder="e.g., 'We met at the Tech Conference 2023' or 'They mentored me during my internship' or 'We worked together on Project X'",
                        help="Add any personal context about your relationship or what you know about these connections. This helps create more authentic emails.",
                        height=100,
                        key="additional_context_input"
                    )

                    # Action buttons
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if st.button("📧 Generate Personalized Emails", use_container_width=True, type="primary"):
                            # Get selected contacts by position
                            selected_positions = sorted(list(st.session_state['selected_contacts']))
                            selected_df = filtered_df.iloc[selected_positions]

                            # Generate personalized emails with loading spinner
                            with st.spinner(f"✨ AI is writing {len(selected_df)} personalized email(s)..."):
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
                                    st.success(f"✅ Generated {len(selected_df)} personalized email draft(s)!")
                                except Exception as e:
                                    # Log failed email generation
                                    analytics.log_email_generation(
                                        num_contacts=len(selected_df),
                                        email_purpose=email_purpose,
                                        email_tone=email_tone,
                                        success=False,
                                        session_id=st.session_state['session_id']
                                    )
                                    st.error(f"❌ Failed to generate emails: {str(e)}")

                    with col2:
                        if st.button("📋 Copy Contact Info", use_container_width=True):
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

                            st.success("✅ Contact info copied! Check below.")

                    with col3:
                        # CSV export of selected
                        selected_positions = sorted(list(st.session_state['selected_contacts']))
                        selected_df = filtered_df.iloc[selected_positions]
                        csv = selected_df[display_cols].to_csv(index=False)
                        st.download_button(
                            label="📥 Export Selected",
                            data=csv,
                            file_name="selected_contacts.csv",
                            mime="text/csv",
                            use_container_width=True
                        )

                # Display generated email drafts with tabs
                if 'email_drafts' in st.session_state and st.session_state['email_drafts']:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("### 📧 Email Drafts")

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
                                    st.error("⚠️ There was an error generating this email. Please check your OpenAI API settings.")
                                else:
                                    st.info("💡 AI-generated draft - please personalize before sending!")
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
                            st.error("⚠️ There was an error generating this email. Please check your OpenAI API settings.")
                        else:
                            st.info("💡 AI-generated draft - please personalize before sending!")

                    if st.button("Clear All Email Drafts"):
                        del st.session_state['email_drafts']
                        if 'active_email_tab' in st.session_state:
                            del st.session_state['active_email_tab']
                        st.rerun()

                # Display copied contact info
                if 'contact_info' in st.session_state:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("### 📋 Contact Information")
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
                        label="📥 Download All as CSV",
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
                        label="📋 Download All as TXT",
                        data=text_output,
                        file_name="all_contacts.txt",
                        mime="text/plain",
                        use_container_width=True
                    )

        # === EXTENDED NETWORK SEARCH ===
        # Search in connected users' networks
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("## 🌐 Extended Network Search")
        st.markdown("Search contacts in your connections' networks and request introductions")

        # Get connections count
        connections = collaboration.get_user_connections(user_id, status='accepted')
        sharing_connections = [c for c in connections if c['network_sharing_enabled']]

        if sharing_connections:
            st.markdown(f"**Searching across {len(sharing_connections)} connected network(s)**")

            # Extended search form
            with st.form("extended_search_form"):
                ext_query = st.text_input(
                    "Search for people in extended network...",
                    placeholder='e.g., "Sarah Chen" or "Partner at Sequoia Capital"',
                    label_visibility="collapsed",
                    key="extended_search_query"
                )

                ext_search_button = st.form_submit_button("🔍 Search Extended Network", type="secondary")

            if ext_search_button and ext_query:
                with st.spinner("🔍 Searching connected networks..."):
                    # Get contacts from connected users
                    extended_contacts_df = collaboration.get_contacts_from_connected_users(user_id)

                    if not extended_contacts_df.empty:
                        # Filter by query
                        query_lower = ext_query.lower()
                        mask = (
                            extended_contacts_df['full_name'].fillna('').str.lower().str.contains(query_lower) |
                            extended_contacts_df['company'].fillna('').str.lower().str.contains(query_lower) |
                            extended_contacts_df['position'].fillna('').str.lower().str.contains(query_lower)
                        )

                        results = extended_contacts_df[mask]

                        if not results.empty:
                            st.success(f"✅ Found {len(results)} contact(s) in extended network!")

                            # Display results
                            for idx, row in results.head(20).iterrows():  # Limit to 20 for performance
                                col1, col2 = st.columns([3, 1])

                                with col1:
                                    st.markdown(f"""
                                    <div style='background: #f0f9ff; padding: 1.5rem; border-radius: 10px;
                                                border-left: 4px solid #3b82f6; margin-bottom: 1rem;'>
                                        <div style='font-weight: 600; font-size: 1.05rem; color: #1a1a1a; margin-bottom: 0.5rem;'>
                                            {row.get('full_name', 'Unknown')}
                                        </div>
                                        <div style='color: #666666; font-size: 0.95rem; margin-bottom: 0.3rem;'>
                                            {row.get('position', 'Position unknown')}
                                        </div>
                                        <div style='color: #999999; font-size: 0.9rem; margin-bottom: 0.8rem;'>
                                            {row.get('company', 'Company unknown')}
                                        </div>
                                        <div style='background: white; padding: 0.5rem; border-radius: 6px;'>
                                            <span style='color: #075985; font-size: 0.85rem; font-weight: 600;'>
                                                📇 In {row.get('owner_name', 'Unknown')}'s network
                                            </span>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)

                                with col2:
                                    st.markdown("<br>", unsafe_allow_html=True)
                                    # Request intro button
                                    if st.button(f"📨 Request Intro", key=f"req_intro_{idx}", use_container_width=True):
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

                            if len(results) > 20:
                                st.info(f"ℹ️ Showing first 20 of {len(results)} results. Refine your search for more specific matches.")

                        else:
                            st.info(f"No contacts found matching '{ext_query}' in extended network.")
                    else:
                        st.info("No contacts available in extended network yet.")

            # Show intro request form if contact selected
            if 'intro_request_contact' in st.session_state:
                contact = st.session_state['intro_request_contact']

                st.markdown("---")
                st.markdown("### 📨 Request Introduction")

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
                        submit_request = st.form_submit_button("📤 Send Request", type="primary", use_container_width=True)
                    with col2:
                        cancel_request = st.form_submit_button("❌ Cancel", use_container_width=True)

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
                                st.success(f"✅ Introduction request sent to {contact['connector_name']}!")
                                del st.session_state['intro_request_contact']
                                st.rerun()
                            else:
                                st.error(result['message'])

                    if cancel_request:
                        del st.session_state['intro_request_contact']
                        st.rerun()

        else:
            st.info("👥 Connect with other users to search their networks and request introductions!")
            st.markdown("""
            **How to build your extended network:**
            1. Go to the **Connections** page
            2. Search for people by name or organization
            3. Send connection requests
            4. Once connected, you can search each other's networks!
            """)

if __name__ == "__main__":
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        st.error("⚠️ OpenAI API key not found. Please set OPENAI_API_KEY in your .env file")
        st.stop()

    main()
