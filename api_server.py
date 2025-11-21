"""
FastAPI server that exposes Streamlit app logic as REST endpoints
This allows the Next.js frontend to use the same intelligent logic
without duplicating code.

Usage:
    uvicorn api_server:app --reload --port 8001
"""
import os
import io
import json
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import existing Streamlit logic
from auth import (
    get_contact_count,
    save_contacts_to_db,
    load_user_contacts,
    get_supabase_client
)

# Create FastAPI app
app = FastAPI(
    title="6th Degree AI API",
    description="Backend API exposing intelligent contact management and search",
    version="1.0.0"
)

# CORS middleware to allow Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://sixthdegree.app",
        "https://code-e4wnb72uj-rohangandotras-projects.vercel.app",
        "https://*.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# AUTH MIDDLEWARE
# ============================================================================

async def get_current_user_id(x_user_id: Optional[str] = Header(None)) -> str:
    """
    Extract user ID from request header

    For now, we trust the Next.js frontend to send the correct user_id.
    The Next.js app has already authenticated the user with Supabase.

    TODO: Later, upgrade to JWT token verification for better security
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-ID header")

    return x_user_id

# ============================================================================
# CSV PARSING (from app.py)
# ============================================================================

def parse_linkedin_csv_api(file_content: bytes) -> pd.DataFrame:
    """
    Parse LinkedIn CSV export - intelligent version from Streamlit app

    Features:
    - Auto-detects header row (skips metadata)
    - Flexible column name matching
    - Creates full_name from first_name + last_name
    - Handles various encodings
    """
    try:
        # Convert bytes to file-like object
        file_obj = io.BytesIO(file_content)

        # Read first 10 lines to find headers
        lines = []
        for i, line in enumerate(file_obj):
            try:
                decoded_line = line.decode('utf-8', errors='ignore').strip()
                lines.append(decoded_line)
                if i >= 10:
                    break
            except:
                continue

        # Find the row that looks like LinkedIn headers
        header_row = 0
        linkedin_indicators = ['first name', 'last name', 'company', 'position', 'email']

        for i, line in enumerate(lines):
            line_lower = line.lower()
            matches = sum(1 for indicator in linkedin_indicators if indicator in line_lower)
            if matches >= 2:
                header_row = i
                break

        # Read CSV with correct header row
        file_obj.seek(0)

        try:
            df = pd.read_csv(
                file_obj,
                encoding='utf-8',
                skiprows=header_row,
                on_bad_lines='skip'
            )
        except Exception:
            file_obj.seek(0)
            df = pd.read_csv(
                file_obj,
                encoding='latin-1',
                skiprows=header_row,
                on_bad_lines='skip'
            )

        if df is None or df.empty:
            raise ValueError("CSV file appears to be empty or has no data rows")

        # Normalize column names
        df.columns = df.columns.str.strip().str.lower()

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
            raise ValueError(
                f"This doesn't look like a LinkedIn Connections export. "
                f"Found columns: {', '.join(df.columns.tolist())}"
            )

        return df

    except Exception as e:
        raise ValueError(f"Error parsing CSV: {str(e)}")

# ============================================================================
# EMAIL ENRICHMENT (from services/email_enrichment.py)
# ============================================================================

def enrich_contacts_from_email_api(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Infer company names from email domains when company field is empty
    Returns: (enriched_df, stats_dict)
    """
    try:
        from services.email_enrichment import enrich_contacts_from_email
        return enrich_contacts_from_email(df)
    except ImportError:
        # Fallback: basic enrichment
        enriched = 0
        if 'email' in df.columns and 'company' in df.columns:
            for idx, row in df.iterrows():
                if pd.isna(row['company']) or row['company'] == '':
                    email = row['email']
                    if email and '@' in email:
                        domain = email.split('@')[1].split('.')[0]
                        df.at[idx, 'company'] = domain.title()
                        enriched += 1

        return df, {'enriched': enriched, 'total': len(df)}

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class UploadResponse(BaseModel):
    success: bool
    message: str
    num_contacts: int
    enriched_count: int
    preview: List[Dict[str, Any]]

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 50

class SearchResponse(BaseModel):
    success: bool
    results: List[Dict[str, Any]]
    total: int

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "6th Degree AI API",
        "version": "1.0.0"
    }

@app.post("/api/contacts/upload", response_model=UploadResponse)
async def upload_contacts(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    """
    Upload and parse LinkedIn CSV

    Features:
    - Intelligent header detection
    - Flexible column matching
    - Email-based company enrichment
    - Saves to user's Supabase account
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")

        # Read file content
        content = await file.read()

        # Parse CSV using intelligent parser
        df = parse_linkedin_csv_api(content)

        # Enrich contacts from email domains
        df, enrichment_stats = enrich_contacts_from_email_api(df)

        # Save to database
        save_result = save_contacts_to_db(user_id, df)

        if not save_result['success']:
            raise HTTPException(status_code=500, detail=save_result.get('error', 'Failed to save contacts'))

        # Create preview (first 5 contacts)
        preview_cols = [col for col in ['full_name', 'position', 'company', 'email'] if col in df.columns]
        preview = df[preview_cols].head(5).to_dict('records')

        return UploadResponse(
            success=True,
            message=f"Successfully uploaded {len(df)} contacts",
            num_contacts=len(df),
            enriched_count=enrichment_stats.get('enriched', 0),
            preview=preview
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/api/contacts")
async def get_contacts(
    user_id: str = Depends(get_current_user_id)
):
    """Get user's contacts from database"""
    try:
        contacts_df = load_user_contacts(user_id)

        if contacts_df is None or contacts_df.empty:
            return {
                "success": True,
                "contacts": [],
                "total": 0
            }

        # Convert DataFrame to list of dicts
        contacts = contacts_df.to_dict('records')

        return {
            "success": True,
            "contacts": contacts,
            "total": len(contacts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch contacts: {str(e)}")

@app.get("/api/contacts/count")
async def get_contact_count_endpoint(user_id: str = Depends(get_current_user_id)):
    """Get count of user's contacts"""
    try:
        count = get_contact_count(user_id)
        return {
            "success": True,
            "count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search", response_model=SearchResponse)
async def search_contacts(
    request: SearchRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    AI-powered natural language search

    Uses the same intelligent search from Streamlit:
    - OpenAI-powered query understanding
    - Fuzzy matching
    - Industry knowledge
    """
    try:
        # Get user's contacts as DataFrame
        df = load_user_contacts(user_id)

        if df is None or df.empty:
            return SearchResponse(
                success=True,
                results=[],
                total=0
            )

        # Try to import and use the intelligent search
        try:
            from services.integrated_search import search_contacts_integrated
            results = search_contacts_integrated(request.query, df, limit=request.limit)
        except ImportError:
            # Fallback: basic search
            query_lower = request.query.lower()
            mask = (
                df['full_name'].str.lower().str.contains(query_lower, na=False) |
                df['company'].str.lower().str.contains(query_lower, na=False) |
                df['position'].str.lower().str.contains(query_lower, na=False)
            )
            results = df[mask].head(request.limit).to_dict('records')

        return SearchResponse(
            success=True,
            results=results,
            total=len(results)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
