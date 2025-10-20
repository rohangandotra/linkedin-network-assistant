1️⃣ Product Vision

“An AI-powered assistant that helps you find and understand your network 
instantly — by asking natural questions, not typing filters.”

You upload or sync your LinkedIn contacts. The assistant can answer 
queries like:

“Who in my network works in venture capital?”

“Who’s based in Toronto and worked with me at Wayfair?”

“Who might be a good intro to investors in AI?”

2️⃣ Core User Flows (V1)
Flow	Description	Tools Needed
1. Upload LinkedIn CSV	User downloads contacts CSV → uploads to app	
Streamlit UI + CSV parser
2. Ask a question	Natural query (“Who do I know in VC?”)	OpenAI API 
(gpt-4-turbo)
3. AI parses + filters contacts	Model extracts intent (industry = VC, 
etc.)	Simple Python filtering
4. Results summary	Show top matches with profile info	Streamlit 
display
5. Export or copy list	User can copy text or download filtered list	
CSV output

Optional stretch goals later:

Chrome extension for “Search my LinkedIn”

Memory (the model learns who you interact with most)

Suggested intros or follow-ups

3️⃣ Technical Architecture (POC)
Layer	Tool	Description
Frontend	Streamlit	Quick interactive UI
Backend	Python + OpenAI API	Query parsing and filtering
Data	CSV upload (LinkedIn export)	Local storage only (privacy-safe)
Deployment	Streamlit Cloud / Vercel	Simple hosting for demo
Optional	Pinecone / FAISS	If you want semantic search later

You can literally build this in a day using Streamlit + GPT.

4️⃣ MVP Requirements
Feature	Must-Have?	Description
Upload CSV	✅	Parse name, title, company, location
Natural language search	✅	“Who in my network is in venture?”
Display results	✅	Table with name + title + link
Summary	✅	“You have 6 people in VC, mostly in Toronto.”
Export	Optional	CSV or text copy
5️⃣ Key Metrics (to Track)
Metric	Goal
Onboarding success (CSV upload works)	90%
Query success (correct intent parsing)	80%
User satisfaction (“Would use again”)	70%
Waitlist signups (from demo page)	100+ in 2 weeks
6️⃣ Future Roadmap
Phase	Features	Goal
V1 (POC)	Upload CSV + Chat search	Validate idea
V2 (MVP)	Live LinkedIn API sync + summaries	Grow beta user 
base
V3 (Product)	AI recommendations, intro helper	Raise seed
7️⃣ Monetization Options (Later)
Model	Why it fits
Freemium	Free for basic search, pay for insights
Subscription ($10–20/mo)	Professionals will pay for time saved
B2B / Team plans	Shared network intelligence for small teams
Recruiter / VC tier	Enhanced enrichment & analytics
8️⃣ Elevator Pitch (For Deck or Investors)

“LinkedIn lets you search — but not think.
Our AI assistant helps professionals instantly find who they know, who 
they should reach out to, and how to leverage their network — without 
manual filters or Boolean searches.”
