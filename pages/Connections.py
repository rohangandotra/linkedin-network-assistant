"""
Connections Page - Manage Network Connections
"""

import streamlit as st
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
import collaboration

# Page configuration
st.set_page_config(
    page_title="Connections - LinkedIn Network Assistant",
    page_icon="👥",
    layout="wide"
)

# Check authentication
if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
    st.error("⚠️ Please log in to access this page")
    st.stop()

user_id = st.session_state['user']['id']
user_name = st.session_state['user']['full_name']

# Header
st.markdown("# 👥 Network Connections")
st.markdown("Manage your professional network and collaboration partners")
st.markdown("---")

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["🤝 My Connections", "🔍 Find People", "📨 Pending Requests"])

# ======================
# TAB 1: MY CONNECTIONS
# ======================
with tab1:
    st.markdown("### My Connections")

    connections = collaboration.get_user_connections(user_id, status='accepted')

    if connections:
        st.markdown(f"**You have {len(connections)} connection(s)**")
        st.markdown("<br>", unsafe_allow_html=True)

        for conn in connections:
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"""
                <div style='background: white; padding: 1.5rem; border-radius: 10px;
                            border: 1px solid #e0e0e0; margin-bottom: 1rem;'>
                    <div style='font-weight: 600; font-size: 1.1rem; color: #1a1a1a; margin-bottom: 0.5rem;'>
                        {conn['full_name']}
                    </div>
                    <div style='color: #666666; font-size: 0.95rem; margin-bottom: 0.3rem;'>
                        {conn['organization'] if conn.get('organization') else 'No organization listed'}
                    </div>
                    <div style='color: #999999; font-size: 0.9rem;'>
                        {conn['email']}
                    </div>
                    <div style='margin-top: 0.8rem; padding: 0.5rem; background: #f0f9ff; border-radius: 6px;'>
                        <span style='color: #075985; font-size: 0.85rem;'>
                            {'🔓 Network sharing: ENABLED' if conn['network_sharing_enabled'] else '🔒 Network sharing: DISABLED'}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                # Network sharing toggle
                share_key = f"share_{conn['connection_id']}"
                current_sharing = conn['network_sharing_enabled']

                st.markdown("<br>", unsafe_allow_html=True)
                new_sharing = st.checkbox(
                    "Share my network",
                    value=current_sharing,
                    key=share_key,
                    help="Allow this connection to search your contacts and request introductions"
                )

                if new_sharing != current_sharing:
                    result = collaboration.update_network_sharing(conn['connection_id'], new_sharing)
                    if result['success']:
                        st.success("Updated!")
                        st.rerun()
                    else:
                        st.error(result['message'])

    else:
        st.info("👋 You don't have any connections yet. Use the 'Find People' tab to connect with others!")


# ======================
# TAB 2: FIND PEOPLE
# ======================
with tab2:
    st.markdown("### Find People to Connect With")
    st.markdown("Search by name or organization to find and connect with other users")

    with st.form("search_users_form"):
        search_query = st.text_input(
            "Search for people",
            placeholder="Enter name or organization...",
            label_visibility="collapsed"
        )

        search_button = st.form_submit_button("🔍 Search", type="primary")

    if search_button and search_query:
        results = collaboration.search_users(search_query, user_id)

        if results:
            st.markdown(f"### Found {len(results)} user(s)")
            st.markdown("<br>", unsafe_allow_html=True)

            for user in results:
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"""
                    <div style='background: white; padding: 1.5rem; border-radius: 10px;
                                border: 1px solid #e0e0e0; margin-bottom: 1rem;'>
                        <div style='font-weight: 600; font-size: 1.1rem; color: #1a1a1a; margin-bottom: 0.5rem;'>
                            {user['full_name']}
                        </div>
                        <div style='color: #666666; font-size: 0.95rem; margin-bottom: 0.3rem;'>
                            {user.get('organization', 'No organization listed')}
                        </div>
                        <div style='color: #999999; font-size: 0.9rem;'>
                            {user['email']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("📤 Send Connection Request", key=f"connect_{user['id']}", use_container_width=True):
                        result = collaboration.send_connection_request(user_id, user['id'])
                        if result['success']:
                            st.success("Connection request sent!")
                            st.rerun()
                        else:
                            st.error(result['message'])

        else:
            st.info(f"No users found matching '{search_query}'")

    # Show example
    with st.expander("💡 How to find people"):
        st.markdown("""
        **Search tips:**
        - Search by full name: "John Smith"
        - Search by organization: "Google", "Stanford University"
        - Results show users who have signed up for LinkedIn Network Assistant

        **After connecting:**
        - You can search each other's networks
        - Request introductions to contacts
        - Share knowledge and opportunities
        """)


# ======================
# TAB 3: PENDING REQUESTS
# ======================
with tab3:
    st.markdown("### Pending Connection Requests")
    st.markdown("Accept or decline requests from people who want to connect with you")
    st.markdown("<br>", unsafe_allow_html=True)

    pending_requests = collaboration.get_pending_connection_requests(user_id)

    if pending_requests:
        st.markdown(f"**You have {len(pending_requests)} pending request(s)**")
        st.markdown("<br>", unsafe_allow_html=True)

        for req in pending_requests:
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.markdown(f"""
                <div style='background: #fffbeb; padding: 1.5rem; border-radius: 10px;
                            border: 1px solid #fbbf24; margin-bottom: 1rem;'>
                    <div style='font-weight: 600; font-size: 1.1rem; color: #1a1a1a; margin-bottom: 0.5rem;'>
                        {req['requester_name']}
                    </div>
                    <div style='color: #666666; font-size: 0.95rem; margin-bottom: 0.3rem;'>
                        {req.get('requester_organization', 'No organization listed')}
                    </div>
                    <div style='color: #999999; font-size: 0.9rem;'>
                        {req['requester_email']}
                    </div>
                    <div style='margin-top: 0.8rem; color: #78716c; font-size: 0.85rem;'>
                        Requested: {req['requested_at'][:10]}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                # Share network checkbox
                share_network = st.checkbox(
                    "Share my network",
                    value=True,
                    key=f"share_req_{req['connection_id']}",
                    help="Allow them to see your contacts"
                )

            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                col_accept, col_decline = st.columns(2)

                with col_accept:
                    if st.button("✅", key=f"accept_{req['connection_id']}", use_container_width=True, help="Accept"):
                        result = collaboration.accept_connection_request(req['connection_id'], share_network)
                        if result['success']:
                            st.success("Accepted!")
                            st.rerun()
                        else:
                            st.error(result['message'])

                with col_decline:
                    if st.button("❌", key=f"decline_{req['connection_id']}", use_container_width=True, help="Decline"):
                        result = collaboration.decline_connection_request(req['connection_id'])
                        if result['success']:
                            st.info("Declined")
                            st.rerun()
                        else:
                            st.error(result['message'])

    else:
        st.info("📭 No pending connection requests")

# Sidebar info
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🤝 About Connections")
    st.markdown("""
    **Why connect?**
    - Search each other's networks
    - Request warm introductions
    - Collaborate on opportunities

    **Privacy:**
    - You control who sees your network
    - Toggle sharing per connection
    - Disconnect anytime
    """)
