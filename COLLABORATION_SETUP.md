# Collaboration Feature Setup Instructions

## Overview
The collaboration feature enables users to:
- Connect with other users
- Search each other's networks
- Request warm introductions
- Manage introduction requests

## Step 1: Run Database Schema

1. Open Supabase Dashboard: https://supabase.com/dashboard
2. Select your project
3. Go to **SQL Editor** in the left sidebar
4. Click **New Query**
5. Copy the entire contents of `collaboration_schema.sql`
6. Paste into the SQL editor
7. Click **Run** button
8. Verify success - you should see "Success. No rows returned"

## Step 2: Verify Tables Created

In the SQL Editor, run these queries to verify:

```sql
-- Check user_connections table
SELECT * FROM user_connections LIMIT 1;

-- Check intro_requests table
SELECT * FROM intro_requests LIMIT 1;

-- Check if organization column was added
SELECT id, email, full_name, organization FROM users LIMIT 5;
```

You should see empty tables (no error messages).

## Step 3: Test Row Level Security (RLS)

The schema includes RLS policies to ensure users can only see their own data. Verify they were created:

```sql
-- View policies for user_connections
SELECT * FROM pg_policies WHERE tablename = 'user_connections';

-- View policies for intro_requests
SELECT * FROM pg_policies WHERE tablename = 'intro_requests';
```

You should see policies for SELECT, INSERT, and UPDATE operations.

## Step 4: Local Testing

1. **Start the app:**
   ```bash
   streamlit run app.py
   ```

2. **Create test accounts:**
   - Create Account #1:
     - Name: Test User 1
     - Organization: Test Company A
     - Email: test1@example.com
     - Password: test123

   - Create Account #2:
     - Name: Test User 2
     - Organization: Test Company B
     - Email: test2@example.com
     - Password: test123

3. **Test Connection Flow:**
   - Login as User 1
   - Upload a CSV with contacts
   - Go to **Connections** page
   - Click "Find People" tab
   - Search for "Test User 2"
   - Send connection request
   - Logout

   - Login as User 2
   - Upload a different CSV with contacts
   - Go to **Connections** page
   - Click "Pending Requests" tab
   - Accept User 1's request
   - Check "Share my network" checkbox

4. **Test Extended Network Search:**
   - Stay logged in as User 2
   - Go to main app page
   - Scroll to "Extended Network Search" section
   - Search for someone from User 1's contacts
   - Click "Request Intro"
   - Fill out request form
   - Submit

5. **Test Intro Requests:**
   - Logout and login as User 1
   - Go to **Intro Requests** page
   - Click "Received Requests" tab
   - You should see User 2's intro request
   - Click "Accept & Generate Intro Email"
   - Review AI-generated email
   - Mark as sent

## Step 5: Deploy to Production

1. **Commit changes:**
   ```bash
   git add .
   git commit -m "Add collaboration feature: connections, extended search, intro requests"
   git push origin main
   ```

2. **Verify Streamlit Cloud deployment:**
   - Streamlit Cloud will automatically redeploy
   - Wait 2-3 minutes for deployment
   - Visit your app URL

3. **Test on production:**
   - Create a new account
   - Upload contacts
   - Test connection flow
   - Test extended search

## Features Overview

### 1. Connections Page (pages/Connections.py)
- **My Connections**: View and manage connections
- **Find People**: Search users by name/organization
- **Pending Requests**: Accept/decline connection requests
- **Network Sharing**: Toggle sharing per connection

### 2. Intro Requests Page (pages/Intro_Requests.py)
- **Sent Requests**: Track intro requests you've made
- **Received Requests**: Manage requests to make intros
- **AI Email Generation**: Auto-generate intro emails
- **Status Tracking**: pending/accepted/declined/completed/cancelled

### 3. Extended Network Search (main app)
- Search contacts from connected users' networks
- Request introductions with context
- See whose network each contact is in

## Database Schema

### user_connections
- Tracks connections between users
- Statuses: pending, accepted, declined
- Network sharing permission per connection
- Bidirectional relationships

### intro_requests
- Tracks introduction requests
- Stores target contact details (survives deletion)
- Auto-cancels if contact deleted (trigger)
- Statuses: pending, accepted, declined, completed, cancelled

## Privacy & Security

- **Row Level Security (RLS)**: Users can only access their own data
- **Network Sharing Control**: Users choose who sees their network
- **Per-Connection Permissions**: Toggle sharing individually
- **Contact Deletion Protection**: Requests auto-cancel if contact deleted

## Troubleshooting

### "relation does not exist" error
- SQL schema wasn't run properly
- Re-run `collaboration_schema.sql` in Supabase SQL Editor

### RLS policy violations
- Check if RLS policies were created
- Run: `SELECT * FROM pg_policies WHERE tablename IN ('user_connections', 'intro_requests');`

### Organization field missing
- Run: `ALTER TABLE users ADD COLUMN IF NOT EXISTS organization VARCHAR(255);`

### Contacts not showing in extended search
- Check network_sharing_enabled is TRUE
- Verify connection status is 'accepted'
- Check both users have uploaded contacts

### Intro request not appearing
- Check connector_id matches actual user ID
- Verify connection exists and is accepted
- Check RLS policies allow user to see request

## Testing Checklist

- [ ] SQL schema runs without errors
- [ ] New users can register with organization
- [ ] Users can search for each other
- [ ] Connection requests can be sent/accepted/declined
- [ ] Network sharing toggle works
- [ ] Extended network search finds contacts
- [ ] Intro request form submits successfully
- [ ] Intro requests appear in receiver's page
- [ ] AI generates intro emails
- [ ] Requests can be accepted/declined
- [ ] Contact deletion cancels pending requests
- [ ] RLS prevents unauthorized access

## Next Steps (Future Enhancements)

1. **Email Notifications**
   - Send email when connection request received
   - Notify when intro request received
   - Notify when intro request accepted/declined

2. **In-App Notifications**
   - Badge count for pending requests
   - Real-time updates

3. **Advanced Search**
   - Filter by industry, role, location
   - Boolean operators (AND, OR, NOT)
   - Save searches

4. **Analytics**
   - Connection growth over time
   - Intro request success rate
   - Network overlap visualization

5. **Granular Contact Sharing**
   - Share specific contacts instead of entire network
   - Tag-based sharing (share only "investors", etc.)

## Support

If you encounter issues:
1. Check browser console for errors (F12 → Console tab)
2. Check Streamlit logs for backend errors
3. Verify database connection in Supabase dashboard
4. Review RLS policies are correctly set up
