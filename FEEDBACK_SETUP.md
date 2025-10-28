# 📝 Feedback System Setup Guide

## Overview
Added a clean, Flow-styled feedback form that appears in the sidebar on every page. Users can report bugs, request features, or provide general feedback.

---

## 🗄️ Database Setup (REQUIRED)

### Step 1: Create Feedback Table in Supabase

1. Go to your Supabase project: https://supabase.com/dashboard
2. Navigate to **SQL Editor**
3. Run the migration script from: `supabase_migrations/004_feedback_table.sql`

Or copy this SQL:

```sql
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Feedback content
    feedback_text TEXT NOT NULL,
    feedback_type VARCHAR(50) DEFAULT 'general',
    page_context VARCHAR(200),

    -- User info
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Status tracking
    status VARCHAR(20) DEFAULT 'new',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes
CREATE INDEX idx_feedback_status ON feedback(status);
CREATE INDEX idx_feedback_user_id ON feedback(user_id);
CREATE INDEX idx_feedback_created_at ON feedback(created_at DESC);
CREATE INDEX idx_feedback_type ON feedback(feedback_type);

-- Enable RLS
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;

-- Allow anyone to submit feedback
CREATE POLICY "Anyone can submit feedback"
    ON feedback
    FOR INSERT
    TO authenticated, anon
    WITH CHECK (true);

-- Users can view their own feedback
CREATE POLICY "Users can view own feedback"
    ON feedback
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());
```

### Step 2: Verify Table Creation

Run this query to confirm:
```sql
SELECT * FROM feedback LIMIT 1;
```

---

## ✨ Features

### **User Experience:**
- ✅ Always accessible in sidebar (collapsible expander)
- ✅ Clean Flow design (no emojis, subtle borders)
- ✅ 4 feedback types: Bug Report, Feature Request, General Feedback, Praise
- ✅ Works for both logged-in and anonymous users
- ✅ Optional email collection for anonymous feedback
- ✅ Automatic page context tracking
- ✅ Success/error messages
- ✅ Form clears after submission

### **Data Collected:**
- Feedback text
- Feedback type
- Page context (which page user was on)
- User ID (if logged in)
- User email (if provided)
- Timestamp

### **Privacy & Security:**
- Anonymous users can submit without account
- Email is optional for anonymous users
- Row Level Security enabled
- Users can only view their own feedback
- Admin can query all feedback via service role

---

## 📊 Viewing Feedback (Admin)

### Method 1: Supabase Dashboard
1. Go to Supabase → **Table Editor**
2. Select `feedback` table
3. View all submissions with filters:
   - Filter by `status`: new, reviewed, resolved
   - Filter by `feedback_type`: bug_report, feature_request, etc.
   - Sort by `created_at` (newest first)

### Method 2: SQL Query
```sql
-- View all new feedback
SELECT
    created_at,
    feedback_type,
    page_context,
    user_email,
    feedback_text,
    status
FROM feedback
WHERE status = 'new'
ORDER BY created_at DESC
LIMIT 50;

-- Count feedback by type
SELECT
    feedback_type,
    COUNT(*) as count
FROM feedback
GROUP BY feedback_type
ORDER BY count DESC;

-- Recent bug reports
SELECT
    created_at,
    page_context,
    feedback_text,
    user_email
FROM feedback
WHERE feedback_type = 'bug_report'
    AND status = 'new'
ORDER BY created_at DESC;
```

### Method 3: Python (Future)
You can build an admin dashboard in Streamlit:

```python
import feedback

# Get all feedback
all_feedback = feedback.get_all_feedback(status='new', limit=100)

# Display in table
import pandas as pd
df = pd.DataFrame(all_feedback)
st.dataframe(df)

# Update status
feedback.update_feedback_status(feedback_id='uuid-here', new_status='reviewed')
```

---

## 🔧 Configuration

### Email Notifications (Optional)
To get notified when feedback is submitted, set up a Supabase webhook:

1. Go to Supabase → **Database** → **Webhooks**
2. Create new webhook:
   - **Name:** Feedback Notification
   - **Table:** feedback
   - **Events:** INSERT
   - **Type:** HTTP Request
   - **URL:** Your notification endpoint (Slack, Discord, email service)

### Fallback Logging
If database is unavailable, feedback is logged to `feedback_log.txt` locally as a fallback.

---

## 🎨 Customization

### Change Feedback Types
Edit `app.py` line 1798-1801:
```python
feedback_type = st.selectbox(
    "Type of feedback",
    ["Bug Report", "Feature Request", "General Feedback", "Praise", "Question"],  # Add more
    key="feedback_type_select"
)
```

### Change Expander Title
Edit `app.py` line 1795:
```python
with st.expander("💬 Feedback & Support"):  # Customize text
```

### Add More Context
Edit `feedback.py` to capture more metadata:
```python
metadata = {
    'browser': 'Chrome',  # Detect from user agent
    'screen_size': '1920x1080',  # Get from JavaScript
    'contacts_count': len(contacts_df)
}
```

---

## 📈 Usage Analytics

Track feedback trends over time:

```sql
-- Feedback volume by day
SELECT
    DATE(created_at) as date,
    COUNT(*) as submissions
FROM feedback
GROUP BY DATE(created_at)
ORDER BY date DESC
LIMIT 30;

-- Most common pages with issues
SELECT
    page_context,
    COUNT(*) as issue_count
FROM feedback
WHERE feedback_type = 'bug_report'
GROUP BY page_context
ORDER BY issue_count DESC;

-- Response time (average time to resolve)
SELECT
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at)) / 3600) as avg_hours_to_resolve
FROM feedback
WHERE status = 'resolved'
    AND updated_at IS NOT NULL;
```

---

## 🚀 Next Steps

1. ✅ Run database migration (see Step 1 above)
2. ✅ Test feedback form on live app
3. ✅ Submit test feedback as both logged-in and anonymous user
4. ✅ Verify feedback appears in Supabase dashboard
5. ⏭️ Set up email notifications (optional)
6. ⏭️ Build admin feedback dashboard (Phase 5)

---

## 🐛 Troubleshooting

### "Error submitting feedback"
**Cause:** Database table doesn't exist or RLS policies blocking insert
**Fix:**
1. Verify table exists: `SELECT * FROM feedback LIMIT 1;`
2. Check RLS policies allow INSERT for anon users
3. Check Supabase logs for detailed error

### Feedback not appearing in database
**Cause:** RLS policy too restrictive
**Fix:** Verify policy allows INSERT:
```sql
-- Check policies
SELECT * FROM pg_policies WHERE tablename = 'feedback';
```

### Form doesn't clear after submit
**Cause:** Session state not updating
**Fix:** Check Streamlit version supports session state key updates

---

## 📝 Files Created

1. `feedback.py` - Feedback submission logic
2. `supabase_migrations/004_feedback_table.sql` - Database schema
3. `FEEDBACK_SETUP.md` - This guide
4. `app.py` (modified) - Added feedback widget to sidebar

---

**Status:** ✅ Ready to deploy
**Last Updated:** 2024-10-27
