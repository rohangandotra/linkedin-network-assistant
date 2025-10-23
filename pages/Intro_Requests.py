"""
Intro Requests Page - Manage Introduction Requests
"""

import streamlit as st
import sys
import os
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
import collaboration
from openai import OpenAI

# Page configuration
st.set_page_config(
    page_title="Intro Requests - LinkedIn Network Assistant",
    page_icon="📨",
    layout="wide"
)

# Check authentication
if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
    st.error("⚠️ Please log in to access this page")
    st.stop()

user_id = st.session_state['user']['id']
user_name = st.session_state['user']['full_name']

# Initialize OpenAI client
def get_openai_api_key():
    """Get OpenAI API key from Streamlit secrets or environment variable"""
    try:
        if 'OPENAI_API_KEY' in st.secrets:
            key = st.secrets["OPENAI_API_KEY"]
            key = key.strip().replace('\n', '').replace('\r', '').replace(' ', '')
            if key and len(key) > 20:
                return key
    except Exception:
        pass

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        api_key = api_key.strip().replace('\n', '').replace('\r', '').replace(' ', '')
        if len(api_key) > 20:
            return key

    return None

client = None
def get_client():
    global client
    if client is None:
        client = OpenAI(api_key=get_openai_api_key(), timeout=30.0, max_retries=2)
    return client

# Header
st.markdown("# 📨 Introduction Requests")
st.markdown("Manage introduction requests you've sent and received")
st.markdown("---")

# Tabs
tab1, tab2 = st.tabs(["📤 Sent Requests", "📥 Received Requests"])

# ======================
# TAB 1: SENT REQUESTS
# ======================
with tab1:
    st.markdown("### Requests You've Sent")
    st.markdown("Track introduction requests you've asked others to make")
    st.markdown("<br>", unsafe_allow_html=True)

    sent_requests = collaboration.get_sent_intro_requests(user_id)

    if sent_requests:
        for req in sent_requests:
            # Determine status color and icon
            status = req['status']
            if status == 'pending':
                status_color = '#f59e0b'
                status_icon = '⏳'
            elif status == 'accepted':
                status_color = '#10b981'
                status_icon = '✅'
            elif status == 'declined':
                status_color = '#ef4444'
                status_icon = '❌'
            elif status == 'completed':
                status_color = '#3b82f6'
                status_icon = '🎉'
            elif status == 'cancelled':
                status_color = '#6b7280'
                status_icon = '⛔'
            else:
                status_color = '#999'
                status_icon = '❓'

            st.markdown(f"""
            <div style='background: white; padding: 1.5rem; border-radius: 10px;
                        border-left: 4px solid {status_color}; margin-bottom: 1.5rem;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                <div style='display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;'>
                    <div>
                        <div style='font-weight: 600; font-size: 1.1rem; color: #1a1a1a;'>
                            {status_icon} {status.upper()}
                        </div>
                    </div>
                    <div style='color: #999; font-size: 0.85rem;'>
                        {req['created_at'][:10]}
                    </div>
                </div>

                <div style='margin-bottom: 1rem;'>
                    <div style='color: #666; font-size: 0.9rem; margin-bottom: 0.3rem;'>REQUESTING INTRO TO:</div>
                    <div style='font-weight: 600; font-size: 1.05rem; color: #1a1a1a;'>{req['target_name']}</div>
                    <div style='color: #666; font-size: 0.95rem;'>
                        {req.get('target_position', 'Position unknown')} at {req.get('target_company', 'Company unknown')}
                    </div>
                </div>

                <div style='margin-bottom: 1rem;'>
                    <div style='color: #666; font-size: 0.9rem; margin-bottom: 0.3rem;'>VIA:</div>
                    <div style='font-weight: 600; color: #1a1a1a;'>
                        {req['users']['full_name']} ({req['users']['email']})
                    </div>
                </div>

                <div style='background: #f9fafb; padding: 1rem; border-radius: 6px; margin-bottom: 1rem;'>
                    <div style='color: #666; font-size: 0.85rem; margin-bottom: 0.5rem; font-weight: 600;'>YOUR MESSAGE:</div>
                    <div style='color: #333; font-size: 0.9rem; line-height: 1.6;'>{req['request_message']}</div>
                </div>

                {f'''
                <div style='background: #fef2f2; padding: 1rem; border-radius: 6px; border: 1px solid #fecaca;'>
                    <div style='color: #991b1b; font-size: 0.85rem; margin-bottom: 0.5rem; font-weight: 600;'>RESPONSE:</div>
                    <div style='color: #991b1b; font-size: 0.9rem;'>{req.get('response_message', 'No response provided')}</div>
                </div>
                ''' if status == 'declined' and req.get('response_message') else ''}

                {f'''
                <div style='background: #f0fdf4; padding: 1rem; border-radius: 6px; border: 1px solid #86efac;'>
                    <div style='color: #166534; font-size: 0.85rem; margin-bottom: 0.5rem; font-weight: 600;'>STATUS:</div>
                    <div style='color: #166534; font-size: 0.9rem;'>Introduction has been made! 🎉</div>
                </div>
                ''' if status == 'completed' else ''}

                {f'''
                <div style='background: #f5f5f5; padding: 1rem; border-radius: 6px; border: 1px solid #d1d5db;'>
                    <div style='color: #4b5563; font-size: 0.85rem; margin-bottom: 0.5rem; font-weight: 600;'>CANCELLED:</div>
                    <div style='color: #4b5563; font-size: 0.9rem;'>{req.get('cancelled_reason', 'Request was cancelled')}</div>
                </div>
                ''' if status == 'cancelled' and req.get('cancelled_reason') else ''}
            </div>
            """, unsafe_allow_html=True)

    else:
        st.info("📭 You haven't sent any introduction requests yet")
        st.markdown("""
        **How to request an intro:**
        1. Go to the main app page
        2. Search for a person in the extended network
        3. Click "Request Intro" button
        4. Fill out the request form
        """)


# ======================
# TAB 2: RECEIVED REQUESTS
# ======================
with tab2:
    st.markdown("### Requests You've Received")
    st.markdown("People asking you to make introductions")
    st.markdown("<br>", unsafe_allow_html=True)

    received_requests = collaboration.get_received_intro_requests(user_id, status='pending')

    if received_requests:
        st.markdown(f"**You have {len(received_requests)} pending intro request(s)**")
        st.markdown("<br>", unsafe_allow_html=True)

        for req in received_requests:
            with st.container():
                st.markdown(f"""
                <div style='background: #fffbeb; padding: 1.5rem; border-radius: 10px;
                            border-left: 4px solid #f59e0b; margin-bottom: 1.5rem;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                    <div style='margin-bottom: 1rem;'>
                        <div style='color: #666; font-size: 0.9rem; margin-bottom: 0.3rem;'>FROM:</div>
                        <div style='font-weight: 600; font-size: 1.05rem; color: #1a1a1a;'>
                            {req['users']['full_name']} ({req['users']['email']})
                        </div>
                        <div style='color: #999; font-size: 0.85rem; margin-top: 0.3rem;'>
                            Requested: {req['created_at'][:10]}
                        </div>
                    </div>

                    <div style='margin-bottom: 1rem;'>
                        <div style='color: #666; font-size: 0.9rem; margin-bottom: 0.3rem;'>WANTS TO MEET:</div>
                        <div style='font-weight: 600; font-size: 1.05rem; color: #1a1a1a;'>{req['target_name']}</div>
                        <div style='color: #666; font-size: 0.95rem;'>
                            {req.get('target_position', 'Position unknown')} at {req.get('target_company', 'Company unknown')}
                        </div>
                        <div style='color: #999; font-size: 0.9rem;'>
                            {req.get('target_email', 'No email provided')}
                        </div>
                    </div>

                    <div style='background: white; padding: 1rem; border-radius: 6px; margin-bottom: 1rem;'>
                        <div style='color: #666; font-size: 0.85rem; margin-bottom: 0.5rem; font-weight: 600;'>WHY THEY WANT THE INTRO:</div>
                        <div style='color: #333; font-size: 0.9rem; line-height: 1.6;'>{req['request_message']}</div>
                    </div>

                    {f'''
                    <div style='background: white; padding: 1rem; border-radius: 6px;'>
                        <div style='color: #666; font-size: 0.85rem; margin-bottom: 0.5rem; font-weight: 600;'>CONTEXT FOR YOU:</div>
                        <div style='color: #333; font-size: 0.9rem; line-height: 1.6;'>{req.get('context_for_connector', 'No additional context provided')}</div>
                    </div>
                    ''' if req.get('context_for_connector') else ''}
                </div>
                """, unsafe_allow_html=True)

                # Actions
                st.markdown("#### Your Response:")

                col1, col2 = st.columns([3, 1])

                with col1:
                    # Generate intro email button
                    if st.button(f"✅ Accept & Generate Intro Email", key=f"gen_email_{req['id']}", type="primary", use_container_width=True):
                        with st.spinner("🤖 AI is writing the introduction email..."):
                            try:
                                # Generate intro email using AI
                                prompt = f"""Write a warm, professional double opt-in introduction email.

REQUESTER: {req['users']['full_name']} ({req['users']['email']})
TARGET: {req['target_name']} at {req['target_company']} ({req.get('target_email', 'email')})
YOUR NAME: {user_name}

REQUESTER'S MESSAGE:
{req['request_message']}

Write a brief introduction email (2-3 short paragraphs) that:
1. Introduces both parties
2. Explains why they should connect
3. Suggests they take it from here
4. Is warm and professional

Start with subject line, then the email body."""

                                response = get_client().chat.completions.create(
                                    model="gpt-4-turbo-preview",
                                    messages=[
                                        {"role": "system", "content": "You are a helpful assistant that writes warm, professional introduction emails."},
                                        {"role": "user", "content": prompt}
                                    ],
                                    temperature=0.7,
                                    max_tokens=400
                                )

                                intro_email = response.choices[0].message.content

                                # Store in session state
                                st.session_state[f'intro_email_{req["id"]}'] = intro_email

                                # Mark as accepted
                                result = collaboration.accept_intro_request(req['id'])

                                if result['success']:
                                    st.success("✅ Request accepted!")
                                    st.rerun()

                            except Exception as e:
                                st.error(f"Error generating email: {str(e)}")

                    # Show generated email if available
                    if f'intro_email_{req["id"]}' in st.session_state:
                        st.markdown("#### 📧 Generated Introduction Email:")
                        st.text_area(
                            "Copy this email and send it:",
                            value=st.session_state[f'intro_email_{req["id"]}'],
                            height=300,
                            key=f"email_display_{req['id']}"
                        )

                        if st.button(f"✓ Mark as Sent", key=f"mark_sent_{req['id']}"):
                            result = collaboration.mark_intro_completed(req['id'])
                            if result['success']:
                                st.success("Marked as completed!")
                                del st.session_state[f'intro_email_{req["id"]}']
                                st.rerun()

                with col2:
                    # Decline button
                    if st.button(f"❌ Decline", key=f"decline_{req['id']}", use_container_width=True):
                        st.session_state[f'show_decline_{req["id"]}'] = True
                        st.rerun()

                    # Show decline form if button clicked
                    if st.session_state.get(f'show_decline_{req["id"]}', False):
                        decline_reason = st.text_area(
                            "Reason (optional):",
                            placeholder="e.g., I don't know this person well enough, or I think a direct reach-out would be better",
                            key=f"decline_reason_{req['id']}",
                            height=100
                        )

                        if st.button("Confirm Decline", key=f"confirm_decline_{req['id']}"):
                            result = collaboration.decline_intro_request(req['id'], decline_reason)
                            if result['success']:
                                st.info("Request declined")
                                if f'show_decline_{req["id"]}' in st.session_state:
                                    del st.session_state[f'show_decline_{req["id"]}']
                                st.rerun()
                            else:
                                st.error(result['message'])

                st.markdown("---")

    else:
        st.info("📭 No pending introduction requests")
        st.markdown("""
        When someone requests an introduction through you, it will appear here.

        **What happens when you accept?**
        - AI generates a warm intro email for you
        - You review and send it manually
        - Both parties are connected!
        """)

    # Show completed/declined requests in expander
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📜 View Past Requests (Accepted/Declined)"):
        all_requests = collaboration.get_received_intro_requests(user_id, status=None)
        past_requests = [r for r in all_requests if r['status'] != 'pending']

        if past_requests:
            for req in past_requests:
                status_emoji = '✅' if req['status'] == 'accepted' or req['status'] == 'completed' else '❌'
                st.markdown(f"""
                **{status_emoji} {req['users']['full_name']}** wanted intro to **{req['target_name']}**
                _Status: {req['status']} on {req.get('responded_at', req.get('created_at'))[:10]}_
                """)
                st.markdown("---")
        else:
            st.info("No past requests")

# Sidebar
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📨 About Intro Requests")
    st.markdown("""
    **Making Intros:**
    - Review each request carefully
    - AI helps write intro emails
    - You send the email manually

    **Best Practices:**
    - Only make intros you're comfortable with
    - Add personal context
    - Do double opt-ins (ask both parties first)
    """)
