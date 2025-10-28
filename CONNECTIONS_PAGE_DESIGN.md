# 🌐 Connections Page - Complete Design Specification

## 📋 Current State Analysis

### What Exists (Backend):
✅ **collaboration.py module** - Fully functional with:
- `send_connection_request()` - Creates pending connection
- `accept_connection_request()` - Accepts request
- `decline_connection_request()` - Declines request
- `get_user_connections()` - Gets accepted connections
- `get_pending_connection_requests()` - Gets incoming requests
- `search_users()` - Find other 6th Degree users
- Extended network search & intro requests

### What's Missing (Frontend):
❌ **No Connections Page UI** - Users can't:
- Find other 6th Degree users
- Send connection requests
- See/accept/decline incoming requests
- Manage their connections
- View connection request history

### What Happens Now When You Send a Request:
```python
# Current flow in collaboration.py:
send_connection_request(user_id, target_user_id)
  ↓
Creates row in user_connections table with status='pending'
  ↓
...nothing else happens (no UI to accept/view it)
```

**PROBLEM:** Request is created but recipient has NO WAY to see or accept it!

---

## 🎯 User Stories & Flows

### Story 1: "I want to connect with another user"
**As a** logged-in user
**I want to** find and connect with other 6th Degree users
**So that** I can search their networks and request introductions

**Current Pain:** Can't do this at all - no UI exists

**Desired Flow:**
```
1. User clicks "Connections" in navigation
2. Sees "Find People" tab
3. Searches: "John Smith" or "Acme Inc"
4. Sees results: John Smith (john@acme.com) - Acme Inc - 450 contacts
5. Clicks "Send Connection Request"
6. Optional: Add personal message
7. Sees success: "Connection request sent to John Smith!"
8. John gets notified (email + in-app badge)
```

### Story 2: "Someone wants to connect with me"
**As a** user
**I want to** see who wants to connect
**So that** I can accept/decline and grow my network

**Current Pain:** Requests are created but user can't see them

**Desired Flow:**
```
1. Jane sends connection request to me
2. I see notification badge: "Connections (1)"
3. Click "Connections" → "Pending Requests" tab
4. See: Jane Smith wants to connect
   - Jane Smith (jane@startup.com)
   - Series AI - 234 contacts
   - Requested 2 hours ago
   - Optional message: "Hey! We met at TechCrunch..."
5. I can:
   - Accept (with option to share my network)
   - Decline (no explanation needed)
   - Ignore (stays pending)
```

### Story 3: "I want to manage my connections"
**As a** user
**I want to** see all my connections
**So that** I can manage network sharing permissions

**Desired Flow:**
```
1. Click "Connections" → "My Connections" tab
2. See list of all connected users:
   - John Smith (john@acme.com) - Acme Inc
   - Connected: March 15, 2024
   - Network sharing: ON ✓
   - 450 contacts shared
3. I can:
   - Toggle network sharing on/off
   - Remove connection
   - Search their network (button)
```

---

## 🎨 Page Design - Flow Principles

### Tab Structure:
```
┌─────────────────────────────────────────────────┐
│ Connections                                      │
├─────────────────────────────────────────────────┤
│ [My Connections] [Find People] [Requests (2)]   │  ← Tabs
├─────────────────────────────────────────────────┤
│                                                  │
│  Content based on selected tab                  │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Tab 1: My Connections (Default)
**Goal:** View and manage accepted connections

**Layout:**
```
My Connections (12)

🔍 [Search connections...]                     [+ Find People]

┌─────────────────────────────────────────────────────────┐
│ John Smith                        [Search Network]  [⋮] │
│ VP Engineering at Acme Inc                              │
│ john@acme.com                                           │
│ Connected: Mar 15, 2024 • 450 contacts shared          │
│ ✓ Network sharing enabled                              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Sarah Chen                        [Search Network]  [⋮] │
│ Partner at Sequoia Capital                             │
│ sarah@sequoia.com                                       │
│ Connected: Feb 3, 2024 • 892 contacts shared           │
│ ✓ Network sharing enabled                              │
└─────────────────────────────────────────────────────────┘

Empty State (if no connections):
┌─────────────────────────────────────────────────────┐
│  Build Your Network                                 │
│                                                     │
│  Connect with other 6th Degree users to:           │
│  • Search their LinkedIn networks                  │
│  • Request warm introductions                      │
│  • Discover new opportunities                      │
│                                                     │
│  [Find People to Connect]                          │
└─────────────────────────────────────────────────────┘
```

**Card Actions Menu ([⋮]):**
- View profile
- Search their network
- Toggle network sharing
- Remove connection

### Tab 2: Find People
**Goal:** Discover and connect with other users

**Layout:**
```
Find People

┌─────────────────────────────────────────────────────────┐
│ 🔍 Search by name or organization                      │
│ [Search users...]                                       │
└─────────────────────────────────────────────────────────┘

Results (342 users):

┌─────────────────────────────────────────────────────────┐
│ John Smith                               [Connect]      │
│ VP Engineering at Acme Inc                              │
│ john@acme.com                                           │
│ 450 contacts                                            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Sarah Chen                               [Pending]      │
│ Partner at Sequoia Capital                             │
│ sarah@sequoia.com                                       │
│ 892 contacts • Request sent Mar 20                     │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Mike Johnson                             [Connected ✓]  │
│ CTO at TechCorp                                         │
│ mike@techcorp.com                                       │
│ 234 contacts • Connected since Feb 15                  │
└─────────────────────────────────────────────────────────┘

Empty State (no search):
┌─────────────────────────────────────────────────────────┐
│  Discover Your Network                                  │
│                                                         │
│  Search for people you know who use 6th Degree:        │
│  • Colleagues from current/past companies              │
│  • Classmates and alumni                               │
│  • Industry connections                                 │
│                                                         │
│  Try searching: "Acme Inc" or "John Smith"            │
└─────────────────────────────────────────────────────────┘
```

**Connect Button Flow:**
```
Click [Connect]
  ↓
Modal appears:
┌─────────────────────────────────────────────────┐
│ Connect with John Smith?                       │
├─────────────────────────────────────────────────┤
│                                                 │
│ Personal message (optional):                   │
│ ┌─────────────────────────────────────────────┐│
│ │ Hi John! We both worked at...             ││
│ └─────────────────────────────────────────────┘│
│                                                 │
│ ☐ Share my network (John can search my        │
│    contacts and request introductions)         │
│                                                 │
│ [Cancel]                    [Send Request]     │
└─────────────────────────────────────────────────┘
  ↓
Success message: "Connection request sent!"
Button changes to: [Pending]
```

### Tab 3: Requests
**Goal:** Review and respond to incoming connection requests

**Layout:**
```
Connection Requests (2 pending)

┌─────────────────────────────────────────────────────────┐
│ Jane Smith                   [Accept] [Decline]         │
│ Founder at Startup AI                                   │
│ jane@startup.com • 234 contacts                        │
│ Requested: 2 hours ago                                  │
│                                                         │
│ Message: "Hey! We met at TechCrunch. Would love to    │
│ connect and explore collaboration opportunities."      │
│                                                         │
│ ☐ Share my network with Jane                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Robert Davis                 [Accept] [Decline]         │
│ VC at Andreessen Horowitz                              │
│ robert@a16z.com • 1,203 contacts                       │
│ Requested: 1 day ago                                    │
│                                                         │
│ ☐ Share my network with Robert                        │
└─────────────────────────────────────────────────────────┘

Recently Responded:
┌─────────────────────────────────────────────────────────┐
│ Mike Chen                                    [✓ Accepted]│
│ Connected 3 days ago                                    │
└─────────────────────────────────────────────────────────┘

Empty State (no pending):
┌─────────────────────────────────────────────────────────┐
│  No Pending Requests                                    │
│                                                         │
│  You're all caught up! When someone wants to connect, │
│  you'll see their request here.                        │
│                                                         │
│  [Find People to Connect]                              │
└─────────────────────────────────────────────────────────┘
```

**Accept Flow:**
```
Click [Accept]
  ↓
Modal (optional):
┌─────────────────────────────────────────────────┐
│ Accept Connection from Jane Smith?            │
├─────────────────────────────────────────────────┤
│                                                 │
│ ☑ Share my network with Jane                  │
│   (Jane can search your contacts and request  │
│    introductions)                              │
│                                                 │
│ Send welcome message (optional):               │
│ ┌─────────────────────────────────────────────┐│
│ │ Welcome! Happy to connect.                ││
│ └─────────────────────────────────────────────┘│
│                                                 │
│ [Cancel]                        [Accept]       │
└─────────────────────────────────────────────────┘
  ↓
Success: "You're now connected with Jane Smith!"
Request moves to "Recently Responded"
Jane gets email notification
```

**Decline Flow:**
```
Click [Decline]
  ↓
Confirmation:
┌─────────────────────────────────────────────────┐
│ Decline request from Jane Smith?              │
├─────────────────────────────────────────────────┤
│                                                 │
│ Jane won't be notified, but the request will  │
│ be removed.                                     │
│                                                 │
│ [Cancel]                        [Decline]      │
└─────────────────────────────────────────────────┘
  ↓
Request removed silently (no notification sent)
```

---

## 🔔 Notification System

### Notification Badge:
```
Navbar:  Connections (2)  ← Shows count of pending requests
                ↑
         Red badge when > 0
```

### Email Notifications:

**When you receive a connection request:**
```
Subject: [6th Degree] John Smith wants to connect

Hi Sarah,

John Smith (VP Engineering at Acme Inc) wants to connect with you on 6th Degree.

Message from John:
"We both worked at Tech Corp and I'd love to collaborate..."

View Request: [https://6thdegree.streamlit.app/connections?tab=requests]

---
6th Degree - Get the most out of your network
```

**When your request is accepted:**
```
Subject: [6th Degree] Jane Smith accepted your connection

Hi John,

Good news! Jane Smith accepted your connection request.

You can now:
• Search Jane's network (892 contacts)
• Request introductions
• Collaborate and discover opportunities

View Connection: [https://6thdegree.streamlit.app/connections]

---
6th Degree - Get the most out of your network
```

---

## 🎨 Flow Design Specifications

### Colors:
```css
--connection-card-bg: #ffffff
--connection-card-border: #e7e5e4 (1px solid)
--connection-card-hover: #fafaf9

--badge-pending: #fbbf24 (yellow)
--badge-accepted: #10b981 (green)
--badge-declined: #6b7280 (gray)

--button-connect: var(--primary) #1d4ed8
--button-accept: #10b981 (green)
--button-decline: #6b7280 (gray)
```

### Typography:
```css
Card name: 1.125rem, 600 weight, --text-primary
Card subtitle: 0.9375rem, 400 weight, --text-secondary
Card meta: 0.875rem, 400 weight, --text-tertiary
Badge: 0.8125rem, 600 weight
```

### Spacing:
```css
Card padding: var(--space-6)
Card margin-bottom: var(--space-4)
Card border-radius: var(--radius-lg) (12px)
Tab padding: var(--space-4)
```

### Buttons:
```css
Primary (Connect, Accept):
  - Background: var(--primary)
  - Text: white
  - Border-radius: 9999px (pill)
  - Padding: 0.5rem 1.5rem
  - Hover: scale(1.02), shadow increase

Secondary (Decline, Cancel):
  - Background: white
  - Text: --text-secondary
  - Border: 1px solid --border-light
  - Same pill shape

Disabled (Pending):
  - Background: --bg-tertiary
  - Text: --text-tertiary
  - Not clickable
```

---

## 🔧 Technical Implementation

### 1. Database Schema (Already Exists):
```sql
user_connections table:
- id (UUID)
- user_id (requester)
- connected_user_id (target)
- status (pending, accepted, declined)
- network_sharing_enabled (boolean)
- requested_at (timestamp)
- accepted_at (timestamp)
- declined_at (timestamp)
- message (text) - optional personal message
```

**ISSUE:** `message` column doesn't exist yet - need migration

### 2. Backend Functions (Already Exist):
✅ `search_users()` - Find users
✅ `send_connection_request()` - Send request
✅ `accept_connection_request()` - Accept
✅ `decline_connection_request()` - Decline
✅ `get_user_connections()` - Get connections
✅ `get_pending_connection_requests()` - Get incoming requests

**MISSING:**
❌ `get_sent_connection_requests()` - See outgoing pending requests
❌ Email notification system

### 3. Frontend Components Needed:
```python
# New file: pages/Connections.py or section in app.py

def show_connections_page():
    """Main connections page with tabs"""
    tabs = st.tabs(["My Connections", "Find People", "Requests"])

    with tabs[0]:
        show_my_connections()

    with tabs[1]:
        show_find_people()

    with tabs[2]:
        show_pending_requests()

def show_my_connections():
    """List of accepted connections"""

def show_find_people():
    """Search for users to connect"""

def show_pending_requests():
    """Incoming connection requests"""
```

---

## 🚨 Critical Issues to Fix

### Issue 1: Missing Message Field
**Problem:** Users can't add personal message when sending request
**Fix:** Add migration:
```sql
ALTER TABLE user_connections
ADD COLUMN request_message TEXT;
```

### Issue 2: No Email Notifications
**Problem:** Users don't know when they get requests/acceptances
**Fix:** Implement email system using SendGrid/AWS SES

### Issue 3: No Outgoing Request Visibility
**Problem:** Users can't see their pending outgoing requests
**Fix:** Add function:
```python
def get_sent_connection_requests(user_id: str, status: str = 'pending'):
    """Get connection requests sent by user"""
```

### Issue 4: Network Sharing Default
**Problem:** Currently defaults to TRUE when sending request
**Fix:** Let sender choose during request, recipient during acceptance

---

## 📊 User Flow Diagrams

### Complete Connection Flow:
```
Alice (wants to connect)          Bob (receives request)
      │                                  │
      ├─1. Searches "Bob"               │
      ├─2. Clicks "Connect"             │
      ├─3. Writes message (optional)    │
      ├─4. Chooses network sharing      │
      ├─5. Sends request                │
      │         │                        │
      │         └──[creates pending]───>├─6. Gets email notification
      │                                  ├─7. Sees badge: Connections (1)
      │                                  ├─8. Opens Requests tab
      │                                  ├─9. Reads Alice's message
      │                                  ├─10. Chooses network sharing
      │                                  ├─11. Clicks "Accept"
      │                                  │
      │<─[updates to accepted]──────────┘
      │                                  │
      ├─12. Gets email: "Bob accepted!" │
      ├─13. Can now search Bob's network│
      │                                  ├─14. Can now search Alice's network
      │                                  │
      ├────────[Connected]──────────────┤
```

---

## 🎯 MVP Scope (Phase 1)

### Must Have (Week 1):
✅ **Tab 1: My Connections**
- List accepted connections
- Show contact count
- Toggle network sharing
- Remove connection

✅ **Tab 2: Find People**
- Search users by name/org
- Send connection request
- Add optional message
- See status (Pending/Connected)

✅ **Tab 3: Requests**
- List pending incoming requests
- Accept with network sharing option
- Decline silently
- Show recently responded

✅ **Remove Emojis**
- Change "🌐 Extended Network" → "Extended Network"
- Apply Flow design throughout

### Should Have (Week 2):
📧 **Email Notifications**
- Request received
- Request accepted
- Request declined (optional)

🔔 **In-App Notifications**
- Badge count on Connections nav
- Toast notifications

📊 **Analytics**
- Track connection growth
- Network size stats

### Could Have (Future):
💬 **Messaging System**
- Direct messaging between connections
- Group conversations

🔍 **Advanced Search**
- Filter by industry
- Filter by location
- Filter by connection count

👥 **Mutual Connections**
- "You both know: John, Sarah, Mike"
- Connection path visualization

🎁 **Connection Suggestions**
- "People you may know"
- Based on mutual connections
- Based on organization

---

## 🚀 Implementation Checklist

### Phase 1: Core Connections Page
- [ ] Remove emoji from "Extended Network" heading (line 2596)
- [ ] Create `get_sent_connection_requests()` in collaboration.py
- [ ] Add `request_message` column to database
- [ ] Create Connections page layout with 3 tabs
- [ ] Implement My Connections tab (list, toggle sharing)
- [ ] Implement Find People tab (search, connect button)
- [ ] Implement Requests tab (accept/decline)
- [ ] Add notification badge to navbar
- [ ] Apply Flow design (no emojis, clean cards)
- [ ] Test all flows end-to-end

### Phase 2: Notifications & Polish
- [ ] Set up SendGrid/SES for emails
- [ ] Create email templates (request received, accepted)
- [ ] Implement email sending in collaboration.py
- [ ] Add toast notifications for actions
- [ ] Add loading states
- [ ] Add empty states with CTAs
- [ ] Mobile responsiveness

### Phase 3: Advanced Features
- [ ] Connection suggestions
- [ ] Mutual connections display
- [ ] Advanced search filters
- [ ] Analytics dashboard
- [ ] Export connections list

---

## 💡 Recommendations

### 1. **Start Simple**
Build Tab 1, 2, 3 first WITHOUT email notifications. Get the core flow working, then add emails.

### 2. **Focus on UX**
The connection request flow should feel like LinkedIn - familiar and intuitive:
- Personal messages make requests feel warmer
- Network sharing choice gives control
- Silent declines avoid awkwardness

### 3. **Network Effects**
Every new user makes the platform more valuable. Encourage connections by:
- Showing contact count next to each user
- Highlighting mutual connections (future)
- Making connection easy (one-click)

### 4. **Privacy First**
Users should control:
- Who can see their contacts (network sharing toggle)
- Who can connect (future: connection approval settings)
- What data is visible (future: profile privacy)

---

## 📝 Next Steps

**Immediate (Today):**
1. Remove emoji from Extended Network section
2. Create connections page mockup with all 3 tabs
3. Test current backend functions work
4. Add `request_message` column to database

**This Week:**
5. Implement My Connections tab
6. Implement Find People tab
7. Implement Requests tab
8. Add notification badge
9. End-to-end testing

**Next Week:**
10. Email notification system
11. Polish and bug fixes
12. Deploy to production

---

**Ready to build?** Let's start with removing the emoji and creating the basic 3-tab layout structure. Want me to proceed?
