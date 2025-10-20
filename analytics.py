"""
Analytics and Logging Module for LinkedIn Network Assistant

This module provides structured logging for user interactions and search queries.
All data is stored locally in JSON format for easy analysis and privacy.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Configuration
LOGS_DIR = Path("logs")
SEARCH_LOG_FILE = LOGS_DIR / "search_queries.jsonl"  # JSONL format for append-only
INTERACTION_LOG_FILE = LOGS_DIR / "interactions.jsonl"
ANALYTICS_SUMMARY_FILE = LOGS_DIR / "analytics_summary.json"

def ensure_logs_directory():
    """Create logs directory if it doesn't exist"""
    LOGS_DIR.mkdir(exist_ok=True)

def log_search_query(
    query: str,
    results_count: int,
    intent: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None
):
    """
    Log a search query with results

    Args:
        query: The user's natural language search query
        results_count: Number of contacts found
        intent: Parsed intent from AI (companies, roles, keywords, etc.)
        session_id: Optional session identifier
    """
    ensure_logs_directory()

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "search",
        "query": query,
        "results_count": results_count,
        "intent": intent,
        "session_id": session_id
    }

    # Append to JSONL file (one JSON object per line)
    with open(SEARCH_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry) + '\n')

def log_email_generation(
    num_contacts: int,
    email_purpose: str,
    email_tone: str,
    success: bool,
    session_id: Optional[str] = None
):
    """
    Log email generation activity

    Args:
        num_contacts: Number of emails generated
        email_purpose: Purpose selected (job seeking, hiring, etc.)
        email_tone: Tone selected (casual, formal, etc.)
        success: Whether generation succeeded
        session_id: Optional session identifier
    """
    ensure_logs_directory()

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "email_generation",
        "num_contacts": num_contacts,
        "email_purpose": email_purpose,
        "email_tone": email_tone,
        "success": success,
        "session_id": session_id
    }

    with open(INTERACTION_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry) + '\n')

def log_csv_upload(
    file_name: str,
    num_contacts: int,
    success: bool,
    error_message: Optional[str] = None,
    session_id: Optional[str] = None
):
    """
    Log CSV upload activity

    Args:
        file_name: Name of uploaded file
        num_contacts: Number of contacts loaded
        success: Whether upload succeeded
        error_message: Error message if failed
        session_id: Optional session identifier
    """
    ensure_logs_directory()

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "csv_upload",
        "file_name": file_name,
        "num_contacts": num_contacts,
        "success": success,
        "error_message": error_message,
        "session_id": session_id
    }

    with open(INTERACTION_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry) + '\n')

def log_contact_export(
    export_type: str,
    num_contacts: int,
    session_id: Optional[str] = None
):
    """
    Log when user exports contacts

    Args:
        export_type: Type of export (selected, all, contact_info, etc.)
        num_contacts: Number of contacts exported
        session_id: Optional session identifier
    """
    ensure_logs_directory()

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "export",
        "export_type": export_type,
        "num_contacts": num_contacts,
        "session_id": session_id
    }

    with open(INTERACTION_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry) + '\n')

def get_analytics_summary() -> Dict[str, Any]:
    """
    Generate summary analytics from logs

    Returns:
        Dictionary with analytics metrics
    """
    ensure_logs_directory()

    summary = {
        "total_searches": 0,
        "total_emails_generated": 0,
        "total_uploads": 0,
        "total_exports": 0,
        "popular_purposes": {},
        "popular_tones": {},
        "avg_results_per_search": 0,
        "last_updated": datetime.now().isoformat()
    }

    # Read search queries
    if SEARCH_LOG_FILE.exists():
        with open(SEARCH_LOG_FILE, 'r', encoding='utf-8') as f:
            searches = [json.loads(line) for line in f if line.strip()]
            summary["total_searches"] = len(searches)
            if searches:
                summary["avg_results_per_search"] = sum(s["results_count"] for s in searches) / len(searches)

    # Read interactions
    if INTERACTION_LOG_FILE.exists():
        with open(INTERACTION_LOG_FILE, 'r', encoding='utf-8') as f:
            interactions = [json.loads(line) for line in f if line.strip()]

            for interaction in interactions:
                if interaction["type"] == "email_generation":
                    summary["total_emails_generated"] += interaction["num_contacts"]

                    purpose = interaction.get("email_purpose", "unknown")
                    summary["popular_purposes"][purpose] = summary["popular_purposes"].get(purpose, 0) + 1

                    tone = interaction.get("email_tone", "unknown")
                    summary["popular_tones"][tone] = summary["popular_tones"].get(tone, 0) + 1

                elif interaction["type"] == "csv_upload":
                    if interaction["success"]:
                        summary["total_uploads"] += 1

                elif interaction["type"] == "export":
                    summary["total_exports"] += 1

    # Save summary
    with open(ANALYTICS_SUMMARY_FILE, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    return summary

def get_recent_searches(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent search queries

    Args:
        limit: Maximum number of searches to return

    Returns:
        List of recent search entries
    """
    ensure_logs_directory()

    if not SEARCH_LOG_FILE.exists():
        return []

    with open(SEARCH_LOG_FILE, 'r', encoding='utf-8') as f:
        searches = [json.loads(line) for line in f if line.strip()]

    # Return most recent searches
    return searches[-limit:]

def clear_logs():
    """
    Clear all log files (use with caution!)
    """
    if SEARCH_LOG_FILE.exists():
        os.remove(SEARCH_LOG_FILE)
    if INTERACTION_LOG_FILE.exists():
        os.remove(INTERACTION_LOG_FILE)
    if ANALYTICS_SUMMARY_FILE.exists():
        os.remove(ANALYTICS_SUMMARY_FILE)

# Privacy note
def get_privacy_note() -> str:
    """Return privacy information about logging"""
    return """
    📊 Analytics & Privacy:
    - All data is stored locally in the 'logs/' folder
    - No data is sent to external servers (except OpenAI API for search/emails)
    - Logs contain: search queries, interaction counts, timestamps
    - Logs DO NOT contain: names, emails, or personal contact data
    - You can delete logs anytime by removing the 'logs/' folder
    """
