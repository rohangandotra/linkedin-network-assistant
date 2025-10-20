# LinkedIn Network Assistant

An AI-powered assistant that helps you find and understand your network instantly by asking natural questions, not typing filters.

## What It Does

Upload your LinkedIn contacts and ask questions like:
- "Who in my network works in venture capital?"
- "Who's based at Google or Meta?"
- "Who might be a good intro to investors in AI?"

The AI understands your question, searches your network, and shows you relevant contacts with smart summaries.

## Quick Start Guide

### Step 1: Get Your OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-...`)

### Step 2: Set Up the Project

Open your terminal and run these commands:

```bash
cd ~/prd-to-app
```

Create a `.env` file with your API key:
```bash
echo "OPENAI_API_KEY=your_actual_key_here" > .env
```

Replace `your_actual_key_here` with the key you copied.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

If you don't have pip, install it first:
```bash
python3 -m ensurepip --upgrade
```

### Step 4: Export Your LinkedIn Contacts

1. Go to LinkedIn.com
2. Click "My Network" → "Connections"
3. Click "Manage synced and imported contacts" (top right)
4. Click "Export contacts"
5. Download the CSV file

Or use the sample file included: `sample_contacts.csv`

### Step 5: Run the App

```bash
streamlit run app.py
```

A browser window will open automatically at http://localhost:8501

### Step 6: Use the App

1. Click "Browse files" in the sidebar
2. Upload your LinkedIn CSV file (or the sample_contacts.csv)
3. Wait for contacts to load
4. Type a question like: "Who works in venture capital?"
5. Click "Search"
6. View results and export if needed!

## Example Questions to Try

- "Who in my network works in venture capital?"
- "Show me people at Google or Meta"
- "Who worked with me at Wayfair?"
- "Find contacts who are investors"
- "Who might know about AI?"
- "Show me engineers at startups"

## Features

- **Natural Language Search**: Ask questions in plain English
- **AI-Powered Parsing**: GPT-4 understands your intent
- **Smart Summaries**: Get overview of results with key insights
- **Export Results**: Download filtered contacts as CSV or text
- **Privacy-First**: All data stays local, nothing stored

## Troubleshooting

### "OpenAI API key not found"
- Make sure you created the `.env` file in the `~/prd-to-app` folder
- Check that you pasted your actual API key (starts with `sk-`)
- Restart the app after creating `.env`

### "Error parsing CSV"
- Make sure you uploaded a LinkedIn CSV export
- Try the sample_contacts.csv file first to test
- LinkedIn CSV format: should have columns like "First Name", "Last Name", "Company", "Position"

### "Module not found" errors
- Run: `pip install -r requirements.txt`
- Make sure you're in the right directory: `cd ~/prd-to-app`

### App won't start
- Make sure Streamlit is installed: `pip install streamlit`
- Try: `python3 -m streamlit run app.py`

## Project Structure

```
prd-to-app/
├── app.py                  # Main application
├── requirements.txt        # Python dependencies
├── .env                    # Your API key (you create this)
├── .env.example           # Template for .env file
├── sample_contacts.csv    # Sample data for testing
├── PRD.md                 # Product requirements
└── README.md              # This file
```

## Tech Stack

- **Frontend**: Streamlit (Python web framework)
- **AI**: OpenAI GPT-4 Turbo
- **Data Processing**: Pandas
- **Deployment Ready**: Can deploy to Streamlit Cloud for free

## Future Enhancements (V2)

- Live LinkedIn API integration
- Chrome extension for instant search
- AI-powered intro suggestions
- Contact interaction memory
- Semantic search with vector database

## Cost Estimate

- OpenAI API: ~$0.01-0.03 per search (GPT-4 Turbo)
- Free tier gives you enough credits to test thoroughly
- Each search uses ~1000-2000 tokens

## Support

Having issues? Check:
1. Is Python 3.8+ installed? Run: `python3 --version`
2. Is the .env file in the right location?
3. Is your API key valid and has credits?

## License

MIT License - free to use and modify!

---

Built based on the PRD in PRD.md
