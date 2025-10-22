import streamlit as st
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import analytics module
sys.path.append(str(Path(__file__).parent.parent))
import analytics

# Page configuration
st.set_page_config(
    page_title="Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# Premium CSS styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Main background */
    .main {
        background: #fafafa;
    }

    /* KPI Card Styling */
    .kpi-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        margin-bottom: 1rem;
    }

    .kpi-value {
        font-size: 2.5rem;
        font-weight: 800;
        color: #1a1a1a;
        margin: 0;
        line-height: 1;
    }

    .kpi-label {
        font-size: 0.9rem;
        color: #666666;
        margin-top: 0.5rem;
        font-weight: 500;
    }

    .kpi-change {
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }

    .kpi-positive {
        color: #10b981;
    }

    .kpi-negative {
        color: #ef4444;
    }

    /* Section headers */
    h1 {
        color: #0a0a0a !important;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        margin-bottom: 0.5rem !important;
    }

    h2, h3 {
        color: #1a1a1a !important;
        font-weight: 700 !important;
    }

    /* Metrics container */
    .metric-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 2rem 0;
    }

    /* Streamlit metric styling fixes */
    [data-testid="stMetric"] {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }

    [data-testid="stMetricLabel"] {
        color: #666666 !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
    }

    [data-testid="stMetricValue"] {
        color: #1a1a1a !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetricDelta"] {
        font-size: 0.85rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Password Protection
if 'analytics_authenticated' not in st.session_state:
    st.session_state['analytics_authenticated'] = False

if not st.session_state['analytics_authenticated']:
    st.markdown("<h1>🔒 Analytics Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 1.1rem;'>This page is password protected</p>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    password = st.text_input("Enter password:", type="password", key="analytics_password")

    if st.button("Unlock Analytics"):
        # Get password from Streamlit secrets or use default for local dev
        try:
            correct_password = st.secrets.get("ANALYTICS_PASSWORD", "admin123")
        except:
            correct_password = os.getenv("ANALYTICS_PASSWORD", "admin123")

        if password == correct_password:
            st.session_state['analytics_authenticated'] = True
            st.success("✅ Access granted!")
            st.rerun()
        else:
            st.error("❌ Incorrect password")

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("💡 **Note:** Set the `ANALYTICS_PASSWORD` in Streamlit Cloud secrets to change the password.")
    st.stop()

# Header
st.markdown("<h1>📊 Analytics Dashboard</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color: #666; font-size: 1.1rem;'>📈 Cumulative insights across ALL user sessions</p>", unsafe_allow_html=True)

# Refresh button and logout
col1, col2, col3 = st.columns([5, 1, 1])
with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()
with col3:
    if st.button("🔒 Lock", use_container_width=True):
        st.session_state['analytics_authenticated'] = False
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# Get analytics data
try:
    summary = analytics.get_analytics_summary()

    # North Star Metrics
    st.markdown("### 🎯 North Star Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class='kpi-card'>
            <div class='kpi-value'>{summary['unique_sessions']}</div>
            <div class='kpi-label'>Unique Sessions</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        conversion = round(summary['search_to_email_conversion'], 1)
        st.markdown(f"""
        <div class='kpi-card'>
            <div class='kpi-value'>{conversion}%</div>
            <div class='kpi-label'>Search → Email Conversion</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        avg_emails = round(summary['avg_emails_per_session'], 1)
        st.markdown(f"""
        <div class='kpi-card'>
            <div class='kpi-value'>{avg_emails}</div>
            <div class='kpi-label'>Avg Emails per Session</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        cost = summary['estimated_cost_usd']
        st.markdown(f"""
        <div class='kpi-card'>
            <div class='kpi-value'>${cost}</div>
            <div class='kpi-label'>Total API Cost (Est.)</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Engagement Metrics
    st.markdown("### 📈 Engagement Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Searches",
            value=summary['total_searches'],
            delta=f"{round(summary['avg_searches_per_session'], 1)} per session"
        )

    with col2:
        st.metric(
            label="Emails Generated",
            value=summary['total_emails_generated'],
            delta=f"{round(summary.get('avg_contacts_per_email_batch', 0), 1)} avg per batch"
        )

    with col3:
        st.metric(
            label="CSV Uploads",
            value=summary['successful_uploads'],
            delta=f"{summary['failed_uploads']} failed" if summary['failed_uploads'] > 0 else "All successful",
            delta_color="inverse" if summary['failed_uploads'] > 0 else "normal"
        )

    with col4:
        st.metric(
            label="Exports",
            value=summary['total_exports'],
            delta=f"Avg {round(summary['avg_results_per_search'], 1)} results/search"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Cost Analysis
    st.markdown("### 💰 Cost Analysis")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Total API Calls",
            value=summary['total_api_calls'],
            delta=f"≈ ${summary['estimated_cost_usd']} total cost"
        )

    with col2:
        st.metric(
            label="Cost per Session",
            value=f"${summary['avg_cost_per_session']}",
            delta="Estimated average"
        )

    with col3:
        # Calculate cost per email
        cost_per_email = round(summary['estimated_cost_usd'] / summary['total_emails_generated'], 3) if summary['total_emails_generated'] > 0 else 0
        st.metric(
            label="Cost per Email",
            value=f"${cost_per_email}",
            delta="Fully personalized AI email"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Feature Usage
    st.markdown("### 🎨 Feature Usage")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Most Popular Email Purposes**")
        if summary['popular_purposes']:
            for purpose, count in sorted(summary['popular_purposes'].items(), key=lambda x: x[1], reverse=True):
                st.markdown(f"- {purpose}: **{count}** times")
        else:
            st.info("No email generation data yet")

    with col2:
        st.markdown("**Most Popular Email Tones**")
        if summary['popular_tones']:
            for tone, count in sorted(summary['popular_tones'].items(), key=lambda x: x[1], reverse=True):
                st.markdown(f"- {tone}: **{count}** times")
        else:
            st.info("No email generation data yet")

    st.markdown("<br>", unsafe_allow_html=True)

    # Recent Search Queries
    st.markdown("### 🔍 Recent Search Queries")

    if summary['popular_search_queries']:
        recent_searches = summary['popular_search_queries'][-10:][::-1]  # Last 10, reverse chronological

        for search in recent_searches:
            timestamp = datetime.fromisoformat(search['timestamp']).strftime("%Y-%m-%d %H:%M")
            st.markdown(f"""
            <div style='background: white; padding: 1rem; border-radius: 8px; border: 1px solid #e0e0e0; margin-bottom: 0.5rem;'>
                <div style='color: #1a1a1a; font-weight: 600;'>"{search['query']}"</div>
                <div style='color: #999; font-size: 0.85rem; margin-top: 0.3rem;'>
                    {timestamp} • {search['results']} results
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No search queries yet. Upload a CSV and try searching!")

    st.markdown("<br>", unsafe_allow_html=True)

    # Time Range
    if summary['first_activity']:
        st.markdown("### 📅 Activity Timeline")
        col1, col2, col3 = st.columns(3)

        with col1:
            first_date = datetime.fromisoformat(summary['first_activity']).strftime("%Y-%m-%d %H:%M")
            st.metric("First Activity", first_date)

        with col2:
            last_date = datetime.fromisoformat(summary['last_activity']).strftime("%Y-%m-%d %H:%M")
            st.metric("Last Activity", last_date)

        with col3:
            st.metric("Days Active", summary['days_active'])

    # Privacy Notice
    st.markdown("---")
    st.markdown(analytics.get_privacy_note())

    # Export Analytics
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📥 Export Data")

    import json
    analytics_json = json.dumps(summary, indent=2)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📊 Download Analytics (JSON)",
            data=analytics_json,
            file_name=f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            width="stretch"
        )

    with col2:
        if st.button("🗑️ Clear All Logs", width="stretch", type="secondary"):
            if st.session_state.get('confirm_clear'):
                analytics.clear_logs()
                st.success("All logs cleared!")
                st.session_state['confirm_clear'] = False
                st.rerun()
            else:
                st.session_state['confirm_clear'] = True
                st.warning("Click again to confirm clearing all logs")

except Exception as e:
    st.error(f"Error loading analytics: {str(e)}")
    st.info("Analytics will appear once you start using the app. Upload a CSV and run some searches!")
