# 📚 LinkedIn Network Assistant - Complete Technical Documentation

**Last Updated:** October 22, 2025
**Version:** 2.0
**Author:** Built with Claude Code

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Tech Stack](#architecture--tech-stack)
3. [Complete Feature List](#complete-feature-list)
4. [File Structure](#file-structure)
5. [Setup & Installation](#setup--installation)
6. [Core Components Deep Dive](#core-components-deep-dive)
7. [AI Integration Details](#ai-integration-details)
8. [Analytics System](#analytics-system)
9. [UI/UX Design System](#uiux-design-system)
10. [Known Issues & Fixes](#known-issues--fixes)
11. [Deployment Guide](#deployment-guide)
12. [Future Plans](#future-plans)
13. [Troubleshooting](#troubleshooting)
14. [API Costs & Management](#api-costs--management)
15. [Security & Privacy](#security--privacy)

---

## Project Overview

### What is this?

The LinkedIn Network Assistant is an AI-powered web application that helps users intelligently search and reach out to their LinkedIn connections. It uses OpenAI's GPT-4 to understand natural language queries and generate personalized outreach emails.

### Core Value Proposition

- **Intelligent Search**: Ask questions like "Who works in venture capital?" instead of manual filtering
- **AI-Powered Understanding**: The AI knows that Google is a tech company, Goldman Sachs is finance, etc.
- **Personalized Emails**: Generate context-aware outreach emails with custom tone and purpose
- **Analytics Dashboard**: Track usage, costs, and engagement metrics

### Key Metrics (as of current version)

- Built for: Individual users (single-user mode)
- Contacts supported: Unlimited
- Search speed: < 2 seconds
- Email generation: ~5-10 seconds per contact
- Cost per search: ~$0.02
- Cost per email: ~$0.02

---

## Architecture & Tech Stack

### Frontend

**Framework**: Streamlit 1.28.0+
- Chosen for rapid prototyping and built-in UI components
- Handles state management via `st.session_state`
- Real-time reactive updates

**Styling**: Custom CSS injected via `st.markdown()`
- Dark mode support with toggle
- Mobile-responsive design (down to 320px width)
- Premium aesthetic with Inter font family
- Smooth animations and transitions

### Backend

**Language**: Python 3.9+

**Core Libraries**:
- `openai>=1.12.0` - GPT-4 API integration
- `pandas>=2.0.0` - Data manipulation
- `python-dotenv>=1.0.0` - Environment variable management
- `requests>=2.31.0` - HTTP diagnostics

**Data Storage** (current):
- Session-based (in-memory via `st.session_state`)
- Local JSON logs for analytics (`logs/` directory)
- No persistent database (yet)

### AI/ML

**Model**: GPT-4 Turbo Preview (`gpt-4-turbo-preview`)
- Used for both search intent extraction and email generation
- Temperature: 0.3 for search (deterministic), 0.7 for emails (creative)
- JSON mode for structured search intent

### Hosting

**Platform**: Streamlit Cloud (free tier)
- Automatic deployments from GitHub
- HTTPS by default
- Secrets management for API keys

**Repository**: GitHub
- Private repository
- Git-based version control
- Manual deployments via push to main branch

---

## Complete Feature List

### ✅ Implemented Features

#### 1. CSV Upload & Parsing
- **What**: Upload LinkedIn Connections.csv export
- **How**: Intelligent header detection, skips metadata rows
- **Supports**: Multiple encodings (UTF-8, Latin-1), bad line handling
- **Columns mapped**: First Name, Last Name, Company, Position, Email, Connected On
- **Error handling**: User-friendly instructions if parsing fails

#### 2. Intelligent Natural Language Search
- **What**: Ask questions in plain English about your network
- **Examples**:
  - "Who works in tech?"
  - "Show me engineers"
  - "Who is the most senior person?"
  - "Find people in venture capital"
- **How it works**:
  1. User query sent to GPT-4
  2. AI uses world knowledge to categorize companies/roles
  3. Returns structured JSON with matching criteria
  4. Filters contacts based on AI's understanding
  5. Optionally ranks by seniority

#### 3. Seniority Ranking
- **What**: Automatically ranks contacts by job title seniority
- **Scoring system**:
  - C-level/Founders: 100 points (CEO, CTO, CFO, Founder)
  - Executives: 85-95 points (VP, SVP, EVP)
  - Partners: 80-90 points (General Partner, Managing Partner)
  - Directors: 70 points
  - Principals/Staff: 60-65 points
  - Senior/Lead: 45-50 points
  - Managers: 40-45 points
  - Individual Contributors: 25-35 points
- **Triggered by**: Queries like "most senior", "top 5 leaders", "highest level"

#### 4. Contact Selection & Pagination
- **Pagination**: 10 contacts per page
- **Select all**: Checkbox to select all on current page
- **Individual selection**: Checkbox per contact
- **Persistent selection**: Selections preserved across page navigation
- **Page navigation**: Previous/Next buttons + direct page number links
- **Display**: Shows X-Y of Z contacts

#### 5. Personalized Email Generation
- **Purpose options** (8 types):
  - Just catching up / Reconnecting
  - I'm looking for a job
  - I'm looking to hire
  - Pitching my startup/idea
  - Asking for advice/mentorship
  - Making an introduction
  - Requesting a coffee chat
  - Seeking information/insights

- **Tone options** (5 types):
  - Friendly & Casual
  - Professional & Formal
  - Enthusiastic & Energetic
  - Direct & Brief
  - Humble & Respectful

- **Additional Context** (NEW):
  - Free-form text area for personal relationship details
  - Examples: "We met at Tech Conference 2023", "They mentored me"
  - AI weaves context naturally into email

- **Email structure**:
  - Subject line
  - 2-3 short paragraphs
  - References current role/company
  - Clear call-to-action
  - Uses placeholders like [YOUR NAME] for customization

- **Tabbed display**: Each contact gets their own tab for easy review

#### 6. Export Functionality
- **Selected contacts as CSV**: Download checked contacts
- **All results as CSV**: Download entire search result
- **All results as TXT**: Plain text format
- **Contact info copy**: Copy-paste formatted list

#### 7. Dark Mode
- **Toggle**: 🌙 icon in top-right corner
- **Persistence**: Saved in session state
- **Coverage**:
  - Full background change (#0a0a0a)
  - All text colors inverted
  - Form inputs, buttons, dataframes styled
  - Tabs, expanders, cards all themed
- **Implementation**: CSS injected conditionally in `main()` function

#### 8. Analytics Dashboard
- **Location**: `pages/Analytics.py` (password-protected)
- **Password**: Set via Streamlit secrets or environment variable
- **Metrics tracked**:
  - Total searches, emails generated, uploads, exports
  - Unique sessions
  - Avg searches per session
  - Avg emails per session
  - Search-to-email conversion rate
  - Estimated API costs
  - Popular email purposes and tones
  - Recent search queries
  - Time-based metrics (first/last activity, days active)

- **Visualizations**:
  - KPI cards for key metrics
  - Cost tracking with per-session breakdown
  - Conversion funnel
  - Feature usage charts
  - Export to CSV

#### 9. Diagnostic Tools
- **Location**: Sidebar "Diagnostics" section
- **Tests**:
  - API key validation
  - Direct HTTP test to OpenAI API
  - OpenAI SDK test
  - Timeout and retry logic testing
- **Error details**: Expandable sections with full error messages and tracebacks

#### 10. Mobile Responsive Design
- **Breakpoints**:
  - 480px: Extra small phones
  - 768px: Tablets and small laptops
  - 1024px: Medium laptops
  - 1200px+: Desktop (max-width container)

- **Mobile optimizations**:
  - Reduced title size (3.2rem → 2rem)
  - Stacked columns
  - Full-width buttons
  - Compact cards and spacing
  - 16px input font size (prevents iOS zoom)
  - Auto-collapsed sidebar

---

## File Structure

```
prd-to-app/
├── app.py                          # Main application file (1,657 lines)
├── analytics.py                    # Analytics logging module (338 lines)
├── requirements.txt                # Python dependencies
├── .env                           # Local environment variables (not in git)
├── .gitignore                     # Git ignore rules
├── .streamlit/
│   └── config.toml                # Streamlit theme configuration
├── pages/
│   └── Analytics.py               # Analytics dashboard page (password-protected)
├── logs/                          # Analytics data (local only)
│   ├── search_queries.jsonl       # One JSON object per line
│   ├── interactions.jsonl         # CSV uploads, email gens, exports
│   └── analytics_summary.json     # Computed metrics
├── SOCIAL_NETWORK_PLAN.md         # Future feature planning document
├── TECHNICAL_DOCUMENTATION.md     # This file
└── README.md                      # User-facing documentation (if created)
```

---

## Setup & Installation

### Prerequisites

1. **Python 3.9+** installed
2. **OpenAI API Key** with credits
3. **Git** for version control
4. **LinkedIn data export** (Connections.csv)

### Local Development Setup

#### Step 1: Clone the repository

```bash
git clone https://github.com/rohangandotra/linkedin-network-assistant.git
cd linkedin-network-assistant
```

#### Step 2: Install dependencies

```bash
pip3 install -r requirements.txt
```

#### Step 3: Create `.env` file

```bash
# Create .env in project root
touch .env
```

Add your OpenAI API key:

```env
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
```

**IMPORTANT**: The app automatically strips whitespace, newlines, and spaces from the API key to handle TOML formatting issues.

#### Step 4: Run locally

```bash
python3 -m streamlit run app.py
```

Or for headless mode:

```bash
STREAMLIT_EMAIL="" python3 -m streamlit run app.py --server.headless=true
```

The app will open at `http://localhost:8501`

### Streamlit Cloud Deployment

#### Step 1: Push to GitHub

```bash
git add .
git commit -m "Initial deployment"
git push origin main
```

#### Step 2: Create Streamlit Cloud app

1. Go to https://share.streamlit.io
2. Click "New app"
3. Select your GitHub repo
4. Main file path: `app.py`
5. Click "Deploy"

#### Step 3: Add secrets

In Streamlit Cloud dashboard:
1. Click "⚙️ Settings"
2. Go to "Secrets" tab
3. Add:

```toml
OPENAI_API_KEY = "sk-proj-YOUR_KEY_HERE"
ANALYTICS_PASSWORD = "your_password_here"
```

**CRITICAL**: Make sure API key is on ONE LINE. No line breaks or it will fail with "InvalidHeader" error.

#### Step 4: Restart app

Click "⚙️ → Reboot app" to apply secrets.

---

## Core Components Deep Dive

### 1. CSV Parsing (`parse_linkedin_csv()`)

**Location**: `app.py`, lines 553-672

**Purpose**: Intelligently parse LinkedIn CSV exports that may have metadata rows.

**How it works**:

1. **Header Detection**:
   - Reads first 10 lines
   - Searches for lines containing LinkedIn column indicators
   - Looks for keywords: 'first name', 'last name', 'company', 'position', 'email'
   - Requires at least 2 matches to confirm header row

2. **Multi-encoding support**:
   - Tries UTF-8 first
   - Falls back to Latin-1 if UTF-8 fails
   - Uses `on_bad_lines='skip'` to handle corrupted rows

3. **Column normalization**:
   - Converts all column names to lowercase
   - Maps common variations:
     - 'first name' → 'first_name'
     - 'title' → 'position'
     - 'email address' → 'email'

4. **Full name generation**:
   - Combines first_name + last_name
   - Strips whitespace
   - Stored in 'full_name' column

5. **Validation**:
   - Checks for at least one required column
   - Required columns: full_name, first_name, company, position
   - Shows error with instructions if validation fails

**Error Handling**:
- Shows expandable instructions on parse failure
- Links to LinkedIn data download page
- Explains expected column format

### 2. Search Intent Extraction (`extract_search_intent()`)

**Location**: `app.py`, lines 674-751

**Purpose**: Convert natural language queries into structured search criteria using AI.

**How it works**:

1. **Context Building**:
   - Extracts all unique companies from dataset
   - Extracts all unique positions (first 20 shown to AI)
   - Provides context about user's network composition

2. **AI Prompt**:
   - System prompt explains AI's role as intelligent search assistant
   - Instructs AI to use world knowledge (e.g., "Google is tech")
   - Provides examples of how to interpret queries
   - Requests JSON response format

3. **Response Structure**:
   ```json
   {
     "matching_companies": ["Google", "Meta", "Amazon"],
     "matching_position_keywords": ["engineer", "manager"],
     "matching_name_keywords": ["Sarah"],
     "requires_ranking": true,
     "ranking_criteria": "seniority",
     "limit_results": 5,
     "summary": "Looking for senior engineers in tech companies"
   }
   ```

4. **Intelligence Features**:
   - **Industry categorization**: "tech" → Google, Meta, Microsoft, Amazon, etc.
   - **Role understanding**: "engineer" matches "Software Engineer", "Senior Engineer", etc.
   - **Seniority queries**: "most senior" triggers ranking algorithm
   - **Limit handling**: "top 3" sets limit_results to 3

5. **Model settings**:
   - Model: `gpt-4-turbo-preview`
   - Temperature: 0.3 (deterministic)
   - Response format: JSON object

**Error Handling**:
- Catches specific OpenAI errors (quota, rate limit, timeout)
- Provides user-friendly guidance for each error type
- Shows full error in expandable section for debugging

### 3. Contact Filtering (`filter_contacts()`)

**Location**: `app.py`, lines 753-790

**Purpose**: Apply AI-generated search criteria to the contact dataset.

**How it works**:

1. **Initialize empty mask**: `pd.Series([False] * len(df))`

2. **Company filtering**:
   - Case-insensitive exact match: `df['company'].str.lower() == company.lower()`
   - Partial match fallback: `df['company'].str.contains(company.lower())`
   - Uses OR logic: `final_mask |= company_mask`

3. **Position filtering**:
   - Searches for keywords in position title
   - Case-insensitive: `df['position'].str.lower().str.contains(keyword)`
   - OR logic across all keywords

4. **Name filtering**:
   - Searches in 'full_name' column
   - Only used when query asks for specific person

5. **Ranking**:
   - If `requires_ranking=true`, calls `rank_by_seniority()`
   - Applies `limit_results` if specified

**Result**: Filtered DataFrame with only matching contacts.

### 4. Seniority Ranking (`rank_by_seniority()`)

**Location**: `app.py`, lines 792-854

**Purpose**: Sort contacts by job title seniority level.

**Scoring dictionary**:
```python
seniority_keywords = {
    # C-level and founders
    'ceo': 100, 'chief executive': 100, 'founder': 100,
    'cto': 95, 'cfo': 95, 'coo': 95, 'cmo': 95,

    # Executive level
    'president': 90, 'vp': 85, 'svp': 87, 'evp': 88,

    # Partner level
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
    'engineer': 30, 'developer': 30, 'analyst': 30,
    'designer': 30, 'scientist': 35, 'researcher': 35,
}
```

**Algorithm**:
1. For each position, search for keywords
2. Take **highest** matching score (not cumulative)
3. Sort by score descending
4. Apply limit if specified
5. Remove score column before returning

**Example**:
- "Senior Software Engineer" → 50 points (from "senior")
- "VP of Engineering" → 85 points (from "vp")
- "CEO & Founder" → 100 points (from "ceo")

### 5. Email Generation (`generate_personalized_emails()`)

**Location**: `app.py`, lines 885-972

**Purpose**: Generate personalized outreach emails for selected contacts using GPT-4.

**Function signature**:
```python
def generate_personalized_emails(
    selected_contacts,           # DataFrame of contacts
    email_purpose="🤝 Just catching up / Reconnecting",
    email_tone="Friendly & Casual",
    additional_context=""        # NEW: User-provided context
):
```

**Purpose mapping** (user selection → AI instruction):
```python
purpose_instructions = {
    "🤝 Just catching up / Reconnecting":
        "reconnect and catch up. Keep it casual and friendly.",
    "💼 I'm looking for a job":
        "explore job opportunities at their company or ask for referrals. Be professional but humble.",
    # ... etc for all 8 purposes
}
```

**Tone mapping**:
```python
tone_instructions = {
    "Friendly & Casual":
        "Use a warm, friendly tone like you're texting a friend. Keep it light and conversational.",
    "Professional & Formal":
        "Use formal business language. Be polished and professional throughout.",
    # ... etc for all 5 tones
}
```

**Additional Context handling** (NEW):
```python
context_section = ""
if additional_context and additional_context.strip():
    context_section = f"""
ADDITIONAL CONTEXT ABOUT OUR RELATIONSHIP:
{additional_context.strip()}

IMPORTANT: Use this context to make the email more personal and authentic.
Reference specific details if they're relevant to this person.
"""
```

**AI Prompt structure**:
```
Write a personalized outreach email to this person from my LinkedIn network:

Name: {name}
Current Role: {position}
Company: {company}

EMAIL PURPOSE: {purpose_instruction}
TONE: {tone_instruction}
{context_section if provided}

The email should:
1. Be brief and conversational (2-3 short paragraphs)
2. Mention their current role/company naturally
3. Align with the stated purpose above
4. Match the specified tone perfectly
5. If additional context was provided, naturally weave in personal details
6. Include a clear call-to-action appropriate for the purpose
7. Be warm and genuine, not salesy or pushy
8. Use placeholders like [YOUR NAME] and [YOUR COMPANY/ROLE] that I can fill in

Return the email with a subject line.
```

**Model settings**:
- Model: `gpt-4-turbo-preview`
- Temperature: 0.7 (creative but not random)
- System message: "You are a helpful assistant that writes warm, personalized networking emails."

**Output format**:
```python
{
    "name": "John Doe",
    "email": "john@example.com",
    "position": "Senior Engineer",
    "company": "Google",
    "email_text": "Subject: ...\n\nHey John,\n\n..."
}
```

**Error handling**:
- Try/except around each email generation
- On error, returns email dict with `"error": True`
- Shows error message in email_text field

### 6. Analytics System (`analytics.py`)

**Location**: `analytics.py`, 338 lines

**Purpose**: Track user behavior and calculate metrics without sending data externally.

**Log files** (JSONL format - one JSON per line):

1. **search_queries.jsonl**:
   ```json
   {
     "timestamp": "2025-10-22T14:30:00",
     "type": "search",
     "query": "Who works in tech?",
     "results_count": 15,
     "intent": {...},
     "session_id": "uuid-here"
   }
   ```

2. **interactions.jsonl**:
   ```json
   {
     "timestamp": "2025-10-22T14:32:00",
     "type": "email_generation",
     "num_contacts": 3,
     "email_purpose": "💼 I'm looking for a job",
     "email_tone": "Professional & Formal",
     "success": true,
     "session_id": "uuid-here"
   }
   ```

**Key functions**:

- `log_search_query()` - Called after each search
- `log_email_generation()` - Called after email generation attempt
- `log_csv_upload()` - Called after CSV upload attempt
- `log_contact_export()` - Called when exporting contacts
- `get_analytics_summary()` - Computes all metrics from logs

**Metrics computed**:

```python
{
    # Core metrics
    "total_searches": 42,
    "total_emails_generated": 18,
    "total_uploads": 3,
    "total_exports": 5,

    # Engagement
    "unique_sessions": 8,
    "avg_searches_per_session": 5.25,
    "avg_emails_per_session": 2.25,

    # Conversion
    "search_to_email_conversion": 42.5,  # percentage
    "avg_contacts_per_email_batch": 3.2,

    # Costs (estimated)
    "total_api_calls": 60,
    "estimated_cost_usd": 1.20,  # $0.02 per call
    "avg_cost_per_session": 0.15,

    # Feature usage
    "popular_purposes": {"💼 I'm looking for a job": 10, ...},
    "popular_tones": {"Professional & Formal": 8, ...},
    "popular_search_queries": [...],

    # Time-based
    "first_activity": "2025-10-15T10:00:00",
    "last_activity": "2025-10-22T14:32:00",
    "days_active": 8
}
```

**Privacy note**:
- All data stored locally in `logs/` folder
- No external analytics services used
- Logs can be deleted anytime by removing `logs/` folder
- Does NOT log personal contact information (names, emails, etc.)

---

## AI Integration Details

### OpenAI Client Setup

**Location**: `app.py`, lines 19-60

**Lazy initialization pattern**:
```python
client = None  # Global variable

def get_client():
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
```

**Why lazy?** Prevents initialization errors on app startup. Client is only created when first API call is made.

### API Key Handling

**Multi-source support**:
1. Try Streamlit Cloud secrets first (`st.secrets["OPENAI_API_KEY"]`)
2. Fall back to environment variable (`os.getenv("OPENAI_API_KEY")`)

**Critical fix for Streamlit Cloud**:
```python
key = st.secrets["OPENAI_API_KEY"]
# CRITICAL: Strip whitespace and newlines from TOML format
key = key.strip().replace('\n', '').replace('\r', '').replace(' ', '')
```

**Why?** Streamlit Cloud's TOML format can split long strings across lines, adding newline characters that break the API key.

### API Call Configuration

**Search intent extraction**:
```python
response = get_client().chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ],
    temperature=0.3,  # Low temperature for consistent results
    response_format={"type": "json_object"}  # Forces JSON response
)
```

**Email generation**:
```python
response = get_client().chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that writes warm, personalized networking emails."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.7  # Higher temperature for creative writing
)
```

### Timeout & Retry Logic

```python
OpenAI(
    api_key=get_openai_api_key(),
    timeout=30.0,      # 30 second timeout
    max_retries=2      # Retry failed requests twice
)
```

**Why needed?** Streamlit Cloud can have network hiccups. Retries prevent temporary failures.

### Cost Estimation

**Current model**: GPT-4 Turbo Preview
- Input: ~$0.01 per 1K tokens
- Output: ~$0.03 per 1K tokens

**Estimated costs per operation**:
- Search query: ~$0.02 (includes company list + query + response)
- Email generation: ~$0.02 per email

**Annual cost for moderate use**:
- 50 searches/month: $1.00/month = $12/year
- 20 emails/month: $0.40/month = $4.80/year
- **Total**: ~$17/year for individual use

---

## Analytics System

### Dashboard Access

**URL**: `https://your-app-url.streamlit.app/Analytics`

**Password Protection**:
```python
# In Analytics.py
ANALYTICS_PASSWORD = os.getenv("ANALYTICS_PASSWORD") or st.secrets.get("ANALYTICS_PASSWORD", "")

if 'analytics_authenticated' not in st.session_state:
    password_input = st.text_input("Enter analytics password:", type="password")
    if st.button("Login"):
        if password_input == ANALYTICS_PASSWORD:
            st.session_state['analytics_authenticated'] = True
            st.rerun()
        else:
            st.error("Incorrect password")
    st.stop()
```

### Metrics Displayed

**KPI Cards** (4 main metrics):
1. Total Searches
2. Emails Generated
3. Unique Sessions
4. Estimated Cost

**Conversion Metrics**:
- Search → Email conversion rate
- Avg searches per session
- Avg emails per session
- Avg contacts per email batch

**Cost Tracking**:
- Total API calls
- Total estimated cost
- Cost per session
- Cost breakdown by operation type

**Feature Usage**:
- Most popular email purposes (bar chart)
- Most popular email tones (bar chart)
- Recent search queries (table)

**Export**:
- Download full analytics as CSV
- Includes all raw data from logs

### Log Rotation

**Current**: No automatic rotation (files grow indefinitely)

**Future consideration**: Implement log rotation after 10,000 entries or 90 days.

---

## UI/UX Design System

### Color Palette

**Light mode** (default):
```css
--background: #fafafa
--text-primary: #0a0a0a
--text-secondary: #666666
--text-tertiary: #999999
--border: #e0e0e0
--card-bg: white
--button-bg: #1a1a1a
--button-hover: #000000
```

**Dark mode**:
```css
--background: #0a0a0a
--text-primary: #ffffff
--text-secondary: #b0b0b0
--text-tertiary: #666666
--border: #2a2a2a
--card-bg: #1a1a1a
--button-bg: #ffffff
--button-hover: #e0e0e0
```

### Typography

**Font family**: Inter (Google Fonts)
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
```

**Font sizes**:
- H1 (desktop): 3.2rem (51.2px)
- H1 (mobile): 2rem (32px)
- Subtitle: 1.15rem (18.4px)
- Body: 1rem (16px)
- Small: 0.9rem (14.4px)

**Font weights**:
- Regular: 400
- Medium: 500
- Semibold: 600
- Bold: 700
- Extra bold: 800 (titles only)

### Component Styling

**Buttons**:
```css
background: #1a1a1a
color: white
border: none
border-radius: 12px
padding: 0.85rem 2.5rem
font-weight: 600
transition: all 0.2s ease

/* Hover */
background: #000000
transform: translateY(-1px)
box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15)
```

**Input fields**:
```css
border-radius: 12px
border: 2px solid #e0e0e0
padding: 1rem 1.5rem
font-size: 1rem
transition: all 0.2s ease

/* Focus */
border-color: #1a1a1a
box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.05)
```

**Cards**:
```css
background: white
padding: 1.5rem
border-radius: 12px
border: 1px solid #e0e0e0
box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04)
```

**Tabs** (highly visible):
```css
/* Inactive tab */
background: white
border: 2px solid #e0e0e0
border-radius: 8px
padding: 12px 24px
font-weight: 600

/* Active tab */
background: #1a1a1a
color: white
border-color: #1a1a1a
box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15)
```

### Animations

**Fade-in on load**:
```css
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(15px); }
    to { opacity: 1; transform: translateY(0); }
}

.main > div {
    animation: fadeIn 0.5s ease-out;
}
```

**Button hover**:
```css
transition: all 0.2s ease
transform: translateY(-1px)  /* On hover */
```

### Responsive Breakpoints

**Mobile (max-width: 768px)**:
- Title size reduced
- Columns stack vertically
- Full-width buttons
- Compact spacing
- Font size 16px on inputs (prevents iOS zoom)

**Tablet (769px - 1024px)**:
- Medium title size
- Two-column layout where possible
- Container max-width: 900px

**Desktop (1025px+)**:
- Full three-column layout
- Container max-width: 1200px
- Optimal spacing and typography

---

## Known Issues & Fixes

### Issue 1: Dark Mode Background Not Working
**Problem**: Dark mode toggle changed text color but background stayed light.

**Root cause**: CSS only targeted `.main` selector, but Streamlit has multiple container layers.

**Fix**:
```css
/* Target ALL Streamlit containers */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"],
.main,
.stApp {
    background-color: #0a0a0a !important;
    background: #0a0a0a !important;
}
```

**Lesson**: Streamlit's DOM structure requires comprehensive selector targeting.

### Issue 2: API Key "InvalidHeader" Error on Streamlit Cloud
**Problem**: API calls failed with "InvalidHeader" error only on Streamlit Cloud, worked locally.

**Root cause**: Streamlit Cloud secrets TOML format split the long API key across multiple lines, embedding newline characters.

**Fix**:
```python
key = st.secrets["OPENAI_API_KEY"]
# Strip ALL whitespace, newlines, and spaces
key = key.strip().replace('\n', '').replace('\r', '').replace(' ', '')
```

**Lesson**: Always sanitize secrets loaded from TOML files.

### Issue 3: TypeError - 'str' object cannot be interpreted as an integer
**Problem**: `st.dataframe()` and `st.button()` crashed with TypeError after Streamlit update.

**Root cause**: Streamlit deprecated `width="stretch"` parameter, now expects integer or `use_container_width=True`.

**Fix**:
```python
# Before (BROKEN):
st.dataframe(df, width="stretch")
st.button("Click me", width="stretch")

# After (FIXED):
st.dataframe(df, use_container_width=True)
st.button("Click me", use_container_width=True)
```

**Files affected**: 6 locations in `app.py`

**Lesson**: Monitor Streamlit changelog for breaking API changes.

### Issue 4: ValueError - too many values to unpack (expected 2)
**Problem**: Pagination crashed with "too many values to unpack" error.

**Root cause**: Incorrect tuple unpacking in `enumerate()` + `iterrows()`.

**Fix**:
```python
# Before (BROKEN):
for page_idx, (contact_idx, (idx, row)) in enumerate(page_contacts.iterrows()):

# After (FIXED):
for page_idx, (idx, row) in enumerate(page_contacts.iterrows()):
```

**Explanation**: `iterrows()` returns `(index, row)` (2 values), not 3. The `actual_idx` is calculated separately.

**Lesson**: Understand pandas iterators return types.

### Issue 5: CSV Parsing Fails with LinkedIn Exports
**Problem**: Some LinkedIn CSV files failed to parse due to metadata rows at the top.

**Root cause**: LinkedIn sometimes adds 2-3 rows of metadata before the actual headers.

**Fix**: Intelligent header detection
```python
# Find the row that looks like LinkedIn headers
header_row = 0
linkedin_indicators = ['first name', 'last name', 'company', 'position', 'email']

for i, line in enumerate(lines):
    line_lower = line.lower()
    # Check if this line contains multiple LinkedIn column indicators
    matches = sum(1 for indicator in linkedin_indicators if indicator in line_lower)
    if matches >= 2:  # If we find at least 2 LinkedIn column names, this is the header
        header_row = i
        break

# Now read CSV with correct header row
df = pd.read_csv(uploaded_file, skiprows=header_row)
```

**Lesson**: Always validate file format assumptions.

### Issue 6: Analytics Page Not Appearing in Sidebar
**Problem**: `Analytics.py` exists but doesn't show in sidebar navigation.

**Status**: PARTIALLY SOLVED

**Attempted fixes**:
1. Renamed to `1_Analytics.py` (with number prefix)
2. Renamed back to `Analytics.py` (without prefix)
3. Verified file has no syntax errors
4. File compiles successfully with `python3 -m py_compile`

**Current hypothesis**: Streamlit Cloud caching issue

**Workaround**: Hard refresh (Cmd+Shift+R) or reboot app in Streamlit Cloud dashboard

**Lesson**: Streamlit multipage apps can have caching quirks on Cloud platform.

---

## Deployment Guide

### Pre-deployment Checklist

✅ **Code**:
- [ ] All tests passing locally
- [ ] No hardcoded API keys or secrets
- [ ] `.env` file in `.gitignore`
- [ ] `requirements.txt` up to date

✅ **Secrets**:
- [ ] OpenAI API key valid and has credits
- [ ] Analytics password set (if using analytics)
- [ ] All secrets in `.env` locally
- [ ] All secrets configured in Streamlit Cloud

✅ **Configuration**:
- [ ] `.streamlit/config.toml` exists
- [ ] Theme settings configured
- [ ] Server settings (if any) configured

### Deployment Steps

#### 1. Commit all changes

```bash
git status
git add .
git commit -m "Descriptive commit message"
```

#### 2. Push to GitHub

```bash
git push origin main
```

#### 3. Streamlit Cloud auto-deploys

- Watch deployment logs in Streamlit Cloud dashboard
- Typical deployment time: 2-3 minutes
- Green checkmark when complete

#### 4. Verify deployment

**Test checklist**:
- [ ] App loads without errors
- [ ] CSV upload works
- [ ] Search returns results
- [ ] Email generation works
- [ ] Dark mode toggle works
- [ ] Analytics page accessible (if implemented)
- [ ] Mobile responsive (test on phone)

#### 5. Monitor errors

**Where to check**:
- Streamlit Cloud logs (📊 Logs tab)
- OpenAI API dashboard (for usage/errors)
- Analytics dashboard (for user errors)

### Rollback Procedure

If deployment breaks:

```bash
# Find last working commit
git log --oneline

# Revert to that commit
git revert <commit-hash>
git push origin main
```

Or use Streamlit Cloud's "Reboot app" to previous version.

### Environment-specific Configuration

**Local development**:
```python
# Uses .env file
OPENAI_API_KEY=sk-...
```

**Streamlit Cloud**:
```toml
# Uses .streamlit/secrets.toml (configured in dashboard)
OPENAI_API_KEY = "sk-..."
ANALYTICS_PASSWORD = "password123"
```

**Code handles both**:
```python
def get_openai_api_key():
    # Try Streamlit Cloud secrets first
    try:
        if 'OPENAI_API_KEY' in st.secrets:
            return st.secrets["OPENAI_API_KEY"].strip()
    except Exception:
        pass

    # Fall back to environment variable
    return os.getenv("OPENAI_API_KEY", "").strip()
```

---

## Future Plans

### Phase 1: Basic Multi-User (MVP)
**Timeline**: 3-4 weeks
**Goal**: Each user has their own account

**Features**:
- User registration (email + password)
- Login/logout
- User profiles (name, email)
- Persist CSV uploads per user
- Each user sees only their own data

**Tech Stack**:
- Supabase (Auth + Database)
- PostgreSQL for user data
- Migrate session state to database

**Database Schema**:
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_verified BOOLEAN DEFAULT FALSE,
    plan_tier VARCHAR(50) DEFAULT 'free'
);

CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    full_name VARCHAR(255),
    company VARCHAR(255),
    position VARCHAR(255),
    email VARCHAR(255),
    connected_on DATE,
    last_updated TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_contacts_user_id ON contacts(user_id);
CREATE INDEX idx_contacts_company ON contacts(company);
```

**Success Criteria**:
- 10+ registered users
- Users can login across devices
- CSV data persists

### Phase 2: User Connections
**Timeline**: 2-3 weeks
**Goal**: Users can connect with each other

**Features**:
- Send connection requests (by email)
- Accept/reject requests
- View list of connections
- Basic privacy settings (allow network search: yes/no)

**Database Schema**:
```sql
CREATE TABLE connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    connected_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending', -- pending, accepted, rejected, blocked
    permissions JSONB DEFAULT '{"can_search_network": true, "can_request_intros": true}',
    created_at TIMESTAMP DEFAULT NOW(),
    accepted_at TIMESTAMP,
    UNIQUE(user_id, connected_user_id)
);
```

**Success Criteria**:
- 5+ user connections established
- Users can toggle privacy settings
- Connection requests work smoothly

### Phase 3: Network Search
**Timeline**: 2-3 weeks
**Goal**: Search across connected users' networks

**Implementation**:
```python
def search_networks(user_id, query):
    # 1. Get user's own contacts
    own_contacts = search_contacts(user_id, query)

    # 2. Get connected users who allow network search
    connected_users = get_connected_users(
        user_id,
        permission="can_search_network"
    )

    # 3. Search each connected user's network
    network_contacts = []
    for connected_user in connected_users:
        contacts = search_contacts(connected_user.id, query)
        # Tag with source user
        contacts['source_user'] = connected_user.name
        network_contacts.append(contacts)

    # 4. Merge and rank results
    return merge_and_rank(own_contacts, network_contacts)
```

**UI Enhancements**:
- Tag each result with network source ("From Sarah's network")
- Filter by network ("Show only Sarah's contacts")
- De-duplicate contacts appearing in multiple networks
- Show aggregate stats ("Searched 5 networks, 247 total contacts")

**Success Criteria**:
- Users successfully find contacts in friends' networks
- Search performance < 2 seconds
- UI clearly shows result sources

### Phase 4: Introduction Requests
**Timeline**: 3-4 weeks
**Goal**: Request introductions through connections

**Workflow**:
```
1. Alice searches across networks
2. Alice finds Bob in Sarah's network
3. Alice clicks "Request Introduction"
4. Alice writes message explaining why
5. Sarah receives notification
6. Sarah can:
   - Approve (forward to Bob with her endorsement)
   - Reject (with optional reason)
   - Ask for more info
7. If approved, Bob receives intro request
8. Bob can accept or decline
9. If accepted, Alice gets Bob's contact info
```

**Database Schema**:
```sql
CREATE TABLE introduction_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requester_id UUID REFERENCES users(id),
    intermediary_id UUID REFERENCES users(id),
    target_contact_id UUID REFERENCES contacts(id),
    status VARCHAR(50) DEFAULT 'pending', -- pending, approved, rejected, completed
    message TEXT,
    intermediary_note TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    responded_at TIMESTAMP
);
```

**Notification System**:
- Email notifications (SendGrid/AWS SES)
- In-app notifications
- Real-time updates (Supabase Realtime)

**Success Criteria**:
- 10+ introduction requests sent
- >50% approval rate
- Users report successful connections

### Phase 5: Polish & Scale
**Timeline**: 3-4 weeks
**Goal**: Production-ready, scalable platform

**Features**:
- Advanced privacy controls (granular permissions)
- Billing/credits system (Stripe integration)
- Email notifications (transactional + marketing)
- Mobile-responsive design (PWA)
- Performance optimization (caching, indexes)
- Network graph visualization (D3.js)
- Analytics for users ("Your network impact")
- API rate limiting and abuse prevention

**Infrastructure**:
```
Frontend: Migrate to Next.js (for better SEO, auth)
Backend API: FastAPI
Database: PostgreSQL (AWS RDS or Supabase)
File Storage: S3/CloudFlare R2
Auth: Supabase Auth or Auth0
Email: SendGrid
Hosting: Railway or Render
CDN: CloudFlare
Monitoring: Sentry + DataDog
```

**Estimated Monthly Costs** (1000 active users):
- Database: $25-50/month
- Backend hosting: $15-30/month
- File storage: $5-10/month
- Email service: $10-20/month
- Auth service: $0-25/month
- **Total: $55-135/month**

**At 10,000 users: $200-500/month**

**Success Criteria**:
- 100+ active users
- <500ms page load times
- Payment system working
- Revenue > costs

### Alternative: "Share Link" Feature (Simple MVP)
**Timeline**: 1 week
**Goal**: Validate core value prop without full social network

**Features**:
- User can generate a shareable link to their network
- Link includes filters (e.g., "Tech companies only")
- Anyone with link can search that network
- User can revoke link anytime

**Pros**:
- Much faster to build
- Validates core value prop
- No database needed yet
- No auth needed yet

**Cons**:
- Less viral (no network effect)
- No introduction flow
- Security concerns (link can be shared widely)

**Implementation**:
```python
# Generate shareable link
link_id = generate_unique_id()
st.session_state[f'shared_network_{link_id}'] = {
    'contacts': filtered_contacts,
    'expires': datetime.now() + timedelta(days=30)
}

# Share URL
share_url = f"https://your-app.streamlit.app?share={link_id}"
```

---

## Troubleshooting

### Common Errors

#### "OpenAI API key not found"

**Symptoms**: App shows error on startup

**Causes**:
1. `.env` file missing or empty
2. Streamlit Cloud secrets not configured
3. API key has whitespace/newlines

**Fix**:
```bash
# Local
echo "OPENAI_API_KEY=sk-proj-YOUR_KEY" > .env

# Streamlit Cloud
# Go to Settings → Secrets → Add:
OPENAI_API_KEY = "sk-proj-YOUR_KEY"
```

#### "Insufficient quota" or "Invalid API key"

**Symptoms**: API calls fail with quota error

**Causes**:
1. OpenAI account has no credits
2. Billing not set up
3. API key revoked/expired

**Fix**:
1. Go to https://platform.openai.com/account/billing
2. Add payment method
3. Add at least $5 credit
4. Generate new API key if expired

#### "Connection error" or "Timeout"

**Symptoms**: API calls fail intermittently

**Causes**:
1. Network issues
2. OpenAI API outage
3. Streamlit Cloud network hiccup

**Fix**:
1. Check OpenAI status: https://status.openai.com
2. Increase timeout in code:
   ```python
   OpenAI(api_key=..., timeout=60.0)
   ```
3. Retry the operation

#### "CSV parsing failed"

**Symptoms**: Error when uploading CSV

**Causes**:
1. Wrong file format (not LinkedIn export)
2. CSV has unexpected structure
3. File encoding issue

**Fix**:
1. Download correct file from LinkedIn:
   - Go to linkedin.com/mypreferences/d/download-my-data
   - Request archive (not "Want something in particular?")
   - Extract ZIP
   - Upload **Connections.csv**
2. Open CSV in text editor to verify columns
3. Expected columns: First Name, Last Name, Company, Position

#### "Dark mode background not working"

**Symptoms**: Text turns light but background stays light

**Fix**: Already fixed in latest version. Update to latest:
```bash
git pull origin main
```

#### "Analytics page not showing in sidebar"

**Symptoms**: Analytics.py exists but page doesn't appear

**Fix**:
1. Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
2. Clear browser cache
3. Reboot app in Streamlit Cloud dashboard
4. Check file is named `Analytics.py` or `1_Analytics.py`

### Debugging Tips

#### Enable debug mode

```python
# In app.py, add at top:
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### View Streamlit Cloud logs

1. Go to Streamlit Cloud dashboard
2. Click on your app
3. Click "📊 Logs" tab
4. Filter by "Error" or "Warning"

#### Test API connection locally

```python
# Create test_api.py
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[{"role": "user", "content": "Say 'test successful'"}],
    max_tokens=10
)

print(response.choices[0].message.content)
```

Run:
```bash
python3 test_api.py
```

#### Check session state

```python
# Add to app.py for debugging
st.write("Session state:", st.session_state)
```

---

## API Costs & Management

### Current Pricing (OpenAI GPT-4 Turbo)

**Model**: `gpt-4-turbo-preview`

**Input**: $0.01 per 1,000 tokens
**Output**: $0.03 per 1,000 tokens

**Estimated tokens per operation**:
- Search query: ~500 input + 200 output = 700 tokens
- Email generation: ~300 input + 500 output = 800 tokens

**Cost per operation**:
- Search: ~$0.02
- Email: ~$0.02

### Usage Estimates

**Individual user** (moderate use):
- 50 searches/month × $0.02 = $1.00
- 20 emails/month × $0.02 = $0.40
- **Total: $1.40/month** or **$16.80/year**

**Power user** (heavy use):
- 200 searches/month × $0.02 = $4.00
- 100 emails/month × $0.02 = $2.00
- **Total: $6.00/month** or **$72/year**

**10 users sharing** (moderate use each):
- 500 searches/month × $0.02 = $10.00
- 200 emails/month × $0.02 = $4.00
- **Total: $14/month** or **$168/year**

### Cost Control Strategies

#### 1. Monitor usage in analytics

```python
# Analytics dashboard shows:
- Total API calls
- Estimated cost
- Cost per session
```

#### 2. Set usage limits (future)

```python
# Implement rate limiting
MAX_SEARCHES_PER_DAY = 50
MAX_EMAILS_PER_DAY = 20

if user_searches_today >= MAX_SEARCHES_PER_DAY:
    st.error("Daily search limit reached. Try again tomorrow.")
    st.stop()
```

#### 3. Cache results (future)

```python
# Cache search results to avoid redundant API calls
@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_search(query, contacts_hash):
    return extract_search_intent(query, contacts_df)
```

#### 4. Use cheaper models for simple tasks (future)

```python
# Use GPT-3.5 for simple searches, GPT-4 for complex
if query_complexity == "simple":
    model = "gpt-3.5-turbo"  # $0.0015 per 1K tokens
else:
    model = "gpt-4-turbo-preview"  # $0.01 per 1K tokens
```

### Billing Setup

**Step 1: Add payment method**
1. Go to https://platform.openai.com/account/billing
2. Click "Add payment method"
3. Enter credit card details

**Step 2: Add credits**
1. Click "Add to credit balance"
2. Minimum: $5 (lasts ~3-6 months for individual use)
3. Recommended: $10-20 for peace of mind

**Step 3: Set spending limits**
1. Go to "Usage limits"
2. Set hard limit (e.g., $10/month)
3. Set email alert at 80% ($8/month)

### Tracking Actual Costs

**OpenAI Dashboard**:
1. Go to https://platform.openai.com/account/usage
2. View usage by:
   - Day
   - Model
   - Total cost

**Export usage data**:
1. Click "Export"
2. Download CSV
3. Analyze in Excel/Google Sheets

**In-app analytics**:
- Check `logs/analytics_summary.json`
- Look for `"estimated_cost_usd"`

---

## Security & Privacy

### Data Storage

**What is stored**:
- ✅ CSV files: In session state (memory), cleared on session end
- ✅ Analytics logs: Local JSON files (`logs/` folder)
- ✅ Generated emails: In session state, cleared on session end
- ❌ Personal contact info: NOT stored persistently
- ❌ User passwords: None (no auth yet)

**Where is data stored**:
- **Local development**: Your computer only
- **Streamlit Cloud**: Temporary session storage, cleared after inactivity
- **Analytics**: Local `logs/` folder (not synced to cloud)

### Data Sent to OpenAI

**What is sent**:
- ✅ Search queries (e.g., "Who works in tech?")
- ✅ Company names from your contacts
- ✅ Position titles from your contacts
- ✅ Contact names for email generation
- ❌ Email addresses: NOT sent to OpenAI
- ❌ Phone numbers: NOT included in prompts

**OpenAI's data policy**:
- API calls are NOT used for training by default (as of 2024)
- Data retained for 30 days for abuse monitoring
- Then deleted

**Opting out of retention**:
1. Go to https://platform.openai.com/account/data-controls
2. Enable "Opt out of data retention"

### API Key Security

**Never commit API keys to Git**:
```bash
# .gitignore includes:
.env
*.env
secrets.toml
```

**Rotate keys regularly**:
1. Generate new key every 3-6 months
2. Revoke old key immediately after updating

**Use environment-specific keys**:
- Development: One key
- Production: Different key
- Easier to track usage and rotate

### Privacy Compliance

**Current status**: NOT GDPR/CCPA compliant (no persistent storage)

**For multi-user version**, need:
- Privacy Policy
- Terms of Service
- Cookie consent banner
- Data deletion flow (GDPR "right to be forgotten")
- Data export flow (GDPR "right to portability")
- User consent for data processing
- Data breach notification process

**Legal review cost**: $2,000-5,000 for startup-grade compliance

### Security Best Practices

**For production**:
1. ✅ Use HTTPS (Streamlit Cloud has this)
2. ✅ Environment variables for secrets
3. ✅ Password protect analytics page
4. ❌ Add rate limiting (TODO)
5. ❌ Add CSRF protection (TODO)
6. ❌ Add input validation (partially done)
7. ❌ Add SQL injection prevention (no SQL yet)

---

## Development Workflow

### Git Workflow

**Branching strategy**:
```bash
main          # Production branch (deploys to Streamlit Cloud)
└─ feature/X  # Feature branches (optional for larger features)
```

**Typical workflow**:
```bash
# 1. Make changes
git status
git diff

# 2. Stage changes
git add app.py analytics.py

# 3. Commit with descriptive message
git commit -m "Add additional context field for email personalization"

# 4. Push to GitHub (triggers auto-deploy)
git push origin main

# 5. Monitor deployment in Streamlit Cloud dashboard
```

### Testing Checklist

**Before each deployment**:
- [ ] Test CSV upload with real LinkedIn export
- [ ] Test search with various queries
- [ ] Test email generation with different purposes/tones
- [ ] Test dark mode toggle
- [ ] Test on mobile device
- [ ] Test analytics page (if implemented)
- [ ] Check for console errors in browser
- [ ] Verify API costs are reasonable

### Code Review Checklist

**Before committing**:
- [ ] No hardcoded secrets
- [ ] No commented-out debug code
- [ ] Consistent code style
- [ ] Functions have docstrings
- [ ] Complex logic has comments
- [ ] No `print()` statements (use `st.write()` or logging)
- [ ] Error handling for all API calls
- [ ] User-friendly error messages

---

## Appendix

### Full Dependency List

```txt
streamlit>=1.28.0       # Web framework
openai>=1.12.0          # OpenAI API client
pandas>=2.0.0           # Data manipulation
python-dotenv>=1.0.0    # Environment variables
requests>=2.31.0        # HTTP client for diagnostics
```

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-proj-...

# Optional
ANALYTICS_PASSWORD=your_password_here
```

### Useful Commands

```bash
# Run locally
python3 -m streamlit run app.py

# Run in headless mode (no browser)
STREAMLIT_EMAIL="" python3 -m streamlit run app.py --server.headless=true

# Check Python version
python3 --version

# Check Streamlit version
python3 -m streamlit version

# Install/update dependencies
pip3 install -r requirements.txt

# Freeze current dependencies
pip3 freeze > requirements.txt

# Check for syntax errors
python3 -m py_compile app.py

# Format code (if using black)
black app.py analytics.py

# Git shortcuts
git status
git log --oneline
git diff HEAD~1  # Compare with last commit
```

### Contact & Support

**For issues**:
- GitHub Issues: https://github.com/rohangandotra/linkedin-network-assistant/issues
- Claude Code: https://github.com/anthropics/claude-code/issues

**For OpenAI API**:
- Status: https://status.openai.com
- Docs: https://platform.openai.com/docs
- Support: help.openai.com

**For Streamlit**:
- Docs: https://docs.streamlit.io
- Community: https://discuss.streamlit.io

---

## Changelog

### v2.0 (October 22, 2025)
- ✨ Added additional context field for email personalization
- 🐛 Fixed pagination tuple unpacking error
- 🐛 Fixed `width="stretch"` TypeError (replaced with `use_container_width=True`)
- 🐛 Fixed upload text spacing and alignment
- 🐛 Fixed dark mode background not applying to all containers
- 📊 Added comprehensive analytics dashboard
- 🌙 Added dark mode toggle with persistent state
- 📄 Added pagination (10 contacts per page)
- 📝 Created complete technical documentation

### v1.0 (October 15, 2025)
- 🎉 Initial release
- 🔍 Natural language search
- 📧 AI-powered email generation
- 📊 Basic analytics logging
- 🎨 Premium UI design
- 📱 Mobile responsive

---

**END OF DOCUMENTATION**

*This document is comprehensive as of October 22, 2025. For updates, check the Git commit history.*
