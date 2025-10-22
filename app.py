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

# Import analytics module
import analytics

# Load environment variables
load_dotenv()

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

# Premium CSS styling - Clean & Modern
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Main background - Clean white */
    .main {
        background: #fafafa;
    }

    /* Content container */
    .block-container {
        padding-top: 3rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    /* Sidebar styling - Elegant dark */
    section[data-testid="stSidebar"] {
        background: #1a1a1a;
        border-right: 1px solid #2a2a2a;
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 2rem;
    }

    /* Sidebar text */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label {
        color: #e0e0e0 !important;
    }

    section[data-testid="stSidebar"] .stMarkdown {
        color: #b0b0b0 !important;
    }

    /* Title styling - Bold black */
    h1 {
        color: #0a0a0a !important;
        font-size: 3.2rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.03em;
        margin-bottom: 0.5rem !important;
        line-height: 1.1 !important;
    }

    /* Subtitle/description */
    .subtitle {
        color: #666666;
        font-size: 1.15rem;
        font-weight: 400;
        margin-bottom: 3rem;
        letter-spacing: -0.01em;
    }

    /* Search input styling - Clean minimal */
    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        padding: 1rem 1.5rem;
        font-size: 1rem;
        transition: all 0.2s ease;
        background: white;
        color: #1a1a1a;
    }

    .stTextInput > div > div > input:focus {
        border-color: #1a1a1a;
        box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.05);
        outline: none;
    }

    .stTextInput > div > div > input::placeholder {
        color: #999999;
    }

    /* Button styling - Bold black */
    .stButton > button {
        background: #1a1a1a;
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.85rem 2.5rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.2s ease;
        letter-spacing: -0.01em;
    }

    .stButton > button:hover {
        background: #000000;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    /* Form submit button styling */
    .stFormSubmitButton > button {
        background: #1a1a1a;
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.85rem 2.5rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.2s ease;
        letter-spacing: -0.01em;
    }

    .stFormSubmitButton > button:hover {
        background: #000000;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    /* File uploader */
    .stFileUploader {
        background: #2a2a2a;
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #3a3a3a;
    }

    /* Dataframe styling */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e0e0e0;
    }

    /* Success/Info boxes */
    .stSuccess {
        background: #f0fdf4;
        border: 1px solid #86efac;
        border-radius: 12px;
        padding: 1rem;
        color: #166534;
    }

    .stInfo {
        background: #f0f9ff;
        border: 1px solid #7dd3fc;
        border-radius: 12px;
        padding: 1rem;
        color: #075985;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        background: #f5f5f5;
        border-radius: 10px;
        font-weight: 600;
        color: #1a1a1a;
        border: 1px solid #e0e0e0;
    }

    /* Results summary - Clean card */
    .results-summary {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }

    /* Download buttons - Outlined style */
    .stDownloadButton > button {
        background: white;
        color: #1a1a1a;
        border: 2px solid #1a1a1a;
        border-radius: 12px;
        padding: 0.7rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s ease;
        letter-spacing: -0.01em;
    }

    .stDownloadButton > button:hover {
        background: #1a1a1a;
        color: white;
        transform: translateY(-1px);
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Section headers */
    h2, h3 {
        color: #1a1a1a !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }

    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(15px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .main > div {
        animation: fadeIn 0.5s ease-out;
    }

    /* Markdown text */
    .main .stMarkdown {
        color: #4a4a4a;
    }

    /* Dividers */
    hr {
        border-color: #e0e0e0;
        margin: 2rem 0;
    }

    /* ============================================
       MOBILE RESPONSIVE STYLES
       ============================================ */

    @media (max-width: 768px) {
        /* Reduce title size on mobile */
        h1 {
            font-size: 2rem !important;
        }

        .subtitle {
            font-size: 1rem;
            margin-bottom: 2rem;
        }

        /* Make content container more compact */
        .block-container {
            padding-top: 1.5rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        /* Make sidebar take less space when open */
        section[data-testid="stSidebar"] {
            width: 280px !important;
        }

        /* Better button sizing on mobile */
        .stButton > button,
        .stFormSubmitButton > button {
            width: 100%;
            padding: 1rem 1.5rem;
            font-size: 1rem;
        }

        /* Stack columns vertically on mobile */
        .row-widget.stColumns {
            flex-direction: column !important;
        }

        /* Full width inputs on mobile */
        .stTextInput > div > div > input {
            width: 100%;
            font-size: 16px !important; /* Prevents zoom on iOS */
        }

        /* Smaller headings on mobile */
        h2, h3, h4 {
            font-size: 1.3rem !important;
        }

        /* Compact dataframe on mobile */
        .stDataFrame {
            font-size: 0.9rem;
        }

        /* Better card spacing on mobile */
        .results-summary {
            padding: 1rem;
            font-size: 0.95rem;
        }

        /* Download buttons stack vertically */
        .stDownloadButton > button {
            width: 100%;
            margin-bottom: 0.5rem;
        }

        /* Reduce padding in example cards */
        .main .stMarkdown div[style*="padding: 2rem"] {
            padding: 1.5rem !important;
        }
    }

    /* Extra small devices (phones in portrait) */
    @media (max-width: 480px) {
        h1 {
            font-size: 1.75rem !important;
        }

        .subtitle {
            font-size: 0.95rem;
        }

        .block-container {
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }

        /* Even more compact on very small screens */
        .stButton > button,
        .stFormSubmitButton > button {
            padding: 0.85rem 1rem;
            font-size: 0.95rem;
        }
    }

    /* Tablet and smaller laptops */
    @media (min-width: 769px) and (max-width: 1024px) {
        h1 {
            font-size: 2.5rem !important;
        }

        .block-container {
            max-width: 900px;
        }
    }

    /* ============================================
       TAB STYLING - Make tabs highly visible
       ============================================ */

    /* Tab container */
    .stTabs {
        background: white;
        border-radius: 12px;
        padding: 0.5rem;
        border: 1px solid #e0e0e0;
    }

    /* Tab buttons */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: #f5f5f5;
        padding: 8px;
        border-radius: 10px;
    }

    .stTabs [data-baseweb="tab"] {
        background: white;
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        color: #1a1a1a;
        font-size: 1rem;
        transition: all 0.2s ease;
    }

    /* Hover state */
    .stTabs [data-baseweb="tab"]:hover {
        background: #fafafa;
        border-color: #999999;
        transform: translateY(-1px);
    }

    /* Active tab - very visible */
    .stTabs [aria-selected="true"] {
        background: #1a1a1a !important;
        color: white !important;
        border-color: #1a1a1a !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    }

    /* Tab panel content */
    .stTabs [data-baseweb="tab-panel"] {
        padding: 1.5rem 0.5rem;
    }

    /* Make tab text more visible */
    .stTabs button[role="tab"] {
        color: #1a1a1a !important;
        font-weight: 600 !important;
    }

    .stTabs button[role="tab"][aria-selected="true"] {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Dark mode CSS overrides (conditionally applied)
if st.session_state.get('dark_mode', False):
    st.markdown("""
    <style>
        /* Dark Mode Overrides */
        .main {
            background: #0a0a0a !important;
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

        .main .stMarkdown {
            color: #b0b0b0 !important;
        }

        /* Input fields */
        .stTextInput > div > div > input {
            background: #1a1a1a !important;
            color: #e0e0e0 !important;
            border-color: #2a2a2a !important;
        }

        .stTextInput > div > div > input:focus {
            border-color: #4a4a4a !important;
            box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.05) !important;
        }

        .stTextInput > div > div > input::placeholder {
            color: #666666 !important;
        }

        /* Buttons */
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

        .stFormSubmitButton > button:hover {
            background: #e0e0e0 !important;
        }

        /* Download buttons */
        .stDownloadButton > button {
            background: #1a1a1a !important;
            color: #e0e0e0 !important;
            border-color: #4a4a4a !important;
        }

        .stDownloadButton > button:hover {
            background: #2a2a2a !important;
            color: #ffffff !important;
        }

        /* Cards and containers */
        .results-summary {
            background: #1a1a1a !important;
            border-color: #2a2a2a !important;
        }

        .stDataFrame {
            border-color: #2a2a2a !important;
        }

        /* Expanders */
        .streamlit-expanderHeader {
            background: #1a1a1a !important;
            color: #e0e0e0 !important;
            border-color: #2a2a2a !important;
        }

        /* Tabs */
        .stTabs {
            background: #1a1a1a !important;
            border-color: #2a2a2a !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            background: #0a0a0a !important;
        }

        .stTabs [data-baseweb="tab"] {
            background: #1a1a1a !important;
            color: #b0b0b0 !important;
        }

        .stTabs [data-baseweb="tab"]:hover {
            background: #2a2a2a !important;
            color: #ffffff !important;
        }

        /* Success/Info boxes */
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

        /* Dividers */
        hr {
            border-color: #2a2a2a !important;
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

def generate_personalized_emails(selected_contacts, email_purpose="🤝 Just catching up / Reconnecting", email_tone="Friendly & Casual"):
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

        # Use AI to generate a personalized email
        prompt = f"""Write a personalized outreach email to this person from my LinkedIn network:

Name: {name}
Current Role: {position}
Company: {company}

EMAIL PURPOSE: {purpose_instruction}
TONE: {tone_instruction}

The email should:
1. Be brief and conversational (2-3 short paragraphs)
2. Mention their current role/company naturally
3. Align with the stated purpose above
4. Match the specified tone perfectly
5. Include a clear call-to-action appropriate for the purpose
6. Be warm and genuine, not salesy or pushy
7. Use placeholders like [YOUR NAME] and [YOUR COMPANY/ROLE] that I can fill in

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

# Main app
def main():
    # Hero section with premium styling
    st.markdown("<h1>LinkedIn Network Assistant</h1>", unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Unlock the power of your network with AI-driven insights</p>', unsafe_allow_html=True)

    # Sidebar for CSV upload
    with st.sidebar:
        # Dark mode toggle at the top
        st.markdown("### 🎨 Appearance")
        dark_mode_toggle = st.toggle(
            "Dark Mode",
            value=st.session_state.get('dark_mode', False),
            key="dark_mode_toggle",
            help="Toggle between light and dark mode"
        )

        # Update dark mode state if toggle changed
        if dark_mode_toggle != st.session_state.get('dark_mode', False):
            st.session_state['dark_mode'] = dark_mode_toggle
            st.rerun()

        st.markdown("---")

        st.markdown("### 📤 Upload Contacts")
        st.markdown("Export your LinkedIn contacts as CSV and upload here.")
        st.markdown("---")

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
                    st.success(f"✅ Loaded {len(df)} contacts")

                    # Log CSV upload
                    analytics.log_csv_upload(
                        file_name=uploaded_file.name,
                        num_contacts=len(df),
                        success=True,
                        session_id=st.session_state['session_id']
                    )

                    # Show preview
                    with st.expander("👀 Preview contacts"):
                        display_cols = [col for col in ['full_name', 'position', 'company'] if col in df.columns]
                        st.dataframe(df[display_cols].head(10), width="stretch")
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
        st.markdown("💡 **Tip:** Try asking questions like:")
        st.markdown("- Who works in tech?")
        st.markdown("- Who is the most senior?")
        st.markdown("- Show me engineers")

        # Diagnostic section for debugging connection issues
        st.markdown("---")
        st.markdown("### 🔧 Diagnostics")
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

    # Main content area
    if 'contacts_df' not in st.session_state:
        # Empty state with examples
        st.markdown("""
        <div style='text-align: center; padding: 0.5rem 0 2rem 0;'>
            <h2 style='color: #718096; font-weight: 400;'>👈 Upload your LinkedIn contacts to get started</h2>
        </div>
        """, unsafe_allow_html=True)

        # LinkedIn Download Instructions
        st.markdown("### 📥 How to Get Your LinkedIn Data")
        st.markdown("""
        <div style='background: #f0f9ff; padding: 1.5rem; border-radius: 12px; border: 1px solid #7dd3fc; margin-bottom: 2rem;'>
            <div style='color: #1a1a1a; font-weight: 600; font-size: 1.1rem; margin-bottom: 1rem;'>
                Follow these simple steps:
            </div>
            <div style='color: #333; line-height: 1.8;'>
                <strong>1.</strong> Go to <a href='https://www.linkedin.com/mypreferences/d/download-my-data' target='_blank' style='color: #0066cc;'>LinkedIn Data Download</a><br>
                <strong>2.</strong> Click <strong>"Request archive"</strong> (the big button at the top)<br>
                <strong>3.</strong> LinkedIn will email you in <strong>10-15 minutes</strong> when your data is ready<br>
                <strong>4.</strong> Download the <strong>ZIP file</strong> from the email<br>
                <strong>5.</strong> Extract/unzip it and find the <strong>Connections.csv</strong> file<br>
                <strong>6.</strong> Upload that file here using the sidebar 👈
            </div>
            <div style='margin-top: 1rem; padding: 0.75rem; background: white; border-radius: 8px; color: #666; font-size: 0.9rem;'>
                💡 <strong>Tip:</strong> The CSV file should have columns like "First Name", "Last Name", "Company", "Position"
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Example queries in premium cards
        st.markdown("### ✨ What You Can Ask")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            <div style='background: white; padding: 2rem; border-radius: 12px; height: 100%;
                        border: 1px solid #e0e0e0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);'>
                <h4 style='margin-bottom: 1rem; color: #1a1a1a;'>🏢 By Industry</h4>
                <p style='color: #666666; margin-bottom: 0.5rem;'>"Who works in venture capital?"</p>
                <p style='color: #666666;'>"Show me people in tech companies"</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div style='background: white; padding: 2rem; border-radius: 12px; height: 100%;
                        border: 1px solid #e0e0e0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);'>
                <h4 style='margin-bottom: 1rem; color: #1a1a1a;'>👔 By Role</h4>
                <p style='color: #666666; margin-bottom: 0.5rem;'>"Who is an engineer?"</p>
                <p style='color: #666666;'>"Show me product managers"</p>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown("""
            <div style='background: white; padding: 2rem; border-radius: 12px; height: 100%;
                        border: 1px solid #e0e0e0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);'>
                <h4 style='margin-bottom: 1rem; color: #1a1a1a;'>⭐ By Seniority</h4>
                <p style='color: #666666; margin-bottom: 0.5rem;'>"Who is the most senior person?"</p>
                <p style='color: #666666;'>"Show me top 5 leaders"</p>
            </div>
            """, unsafe_allow_html=True)

    else:
        contacts_df = st.session_state['contacts_df']

        # Search interface with form for enter key support
        with st.form(key='search_form', clear_on_submit=False):
            query = st.text_input(
                "Ask anything about your network...",
                placeholder='e.g., "Who in my network works in venture capital?"',
                label_visibility="collapsed",
                key="search_query"
            )

            # Submit button (triggered by Enter or click)
            search_button = st.form_submit_button("🔍 Search", type="primary")

        if search_button and query:
            with st.spinner("Searching your network..."):
                # Extract intent
                intent = extract_search_intent(query, contacts_df)

                if intent:
                    st.session_state['last_intent'] = intent

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

        # Display results
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
                for page_idx, (contact_idx, (idx, row)) in enumerate(page_contacts.iterrows()):
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

                        st.markdown(f"""
                        <div style='background: white; padding: 1rem; border-radius: 10px;
                                    border: 1px solid #e0e0e0; margin-bottom: 0.5rem;'>
                            <div style='font-weight: 600; font-size: 1.05rem; color: #1a1a1a; margin-bottom: 0.3rem;'>
                                {name}
                            </div>
                            <div style='color: #666666; font-size: 0.95rem; margin-bottom: 0.2rem;'>
                                {job_position}
                            </div>
                            <div style='color: #999999; font-size: 0.9rem;'>
                                {company} {('• ' + email) if email else ''}
                            </div>
                        </div>
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

                    # Action buttons
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if st.button("📧 Generate Personalized Emails", width="stretch", type="primary"):
                            # Get selected contacts by position
                            selected_positions = sorted(list(st.session_state['selected_contacts']))
                            selected_df = filtered_df.iloc[selected_positions]

                            # Generate personalized emails with loading spinner
                            with st.spinner(f"✨ AI is writing {len(selected_df)} personalized email(s)..."):
                                try:
                                    email_drafts = generate_personalized_emails(selected_df, email_purpose, email_tone)
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
                        if st.button("📋 Copy Contact Info", width="stretch"):
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
                            width="stretch"
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
                        width="stretch"
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
                        width="stretch"
                    )

if __name__ == "__main__":
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        st.error("⚠️ OpenAI API key not found. Please set OPENAI_API_KEY in your .env file")
        st.stop()

    main()
