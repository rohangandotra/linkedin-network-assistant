# Phase 3B: Search Improvements - Comprehensive Plan
## Making the Best Possible Search Model

---

## 🎯 Executive Summary

**Goal:** Transform the LinkedIn network search into a best-in-class search experience with:
- Instant, relevant results ranked by importance
- Typo tolerance and fuzzy matching
- Cost-effective (reduce OpenAI API costs by 90%)
- Fast (sub-100ms response time)
- Intelligent understanding of user intent
- Analytics to continuously improve search quality

**Current Problems:**
1. ❌ No relevance ranking (all results equal weight)
2. ❌ Expensive ($0.02-0.03 per search via OpenAI)
3. ❌ Slow (2-5 seconds per search due to API latency)
4. ❌ No typo tolerance ("Gogle" won't find "Google")
5. ❌ No caching (same query hits API repeatedly)
6. ❌ Limited field weighting (name = company = position)
7. ❌ No synonym handling ("Software Engineer" ≠ "SWE")

---

## 📊 Current Search Implementation Analysis

### How Search Works Today (app.py:682-924)

**Step 1: Query Classification**
```python
classify_query_type(query) → "search" or "analytics"
```
- Detects if user wants people (search) or insights (analytics)
- Keywords: "who", "show me" → search | "how many", "breakdown" → analytics

**Step 2: AI Intent Extraction** (EXPENSIVE: $0.02-0.03 per call)
```python
extract_search_intent(query, contacts_df) → {
    "matching_companies": [...],
    "matching_position_keywords": [...],
    "matching_name_keywords": [...],
    "requires_ranking": bool,
    "summary": "..."
}
```
- Sends entire query + all companies + positions to GPT-4
- AI uses world knowledge to categorize companies by industry
- Example: "Who works in tech?" → AI identifies Google, Meta, Microsoft as tech

**Step 3: Binary Filtering** (NO RANKING)
```python
filter_contacts(df, intent) → filtered_df
```
- Loops through matching criteria
- Boolean OR logic: match ANY company OR ANY position keyword
- **Problem:** All results treated equally, no relevance score

**Step 4: Optional Seniority Ranking**
```python
rank_by_seniority(df) → sorted_df
```
- Only triggered for queries like "most senior person"
- Keyword-based scoring (CEO=100, VP=85, Engineer=30)

**Strengths:**
- ✅ Natural language understanding
- ✅ Uses AI's world knowledge (knows Google is tech)
- ✅ Handles complex queries well

**Weaknesses:**
- ❌ Every search costs $0.02-0.03
- ❌ Every search takes 2-5 seconds
- ❌ No relevance ranking
- ❌ No fuzzy matching
- ❌ No caching

---

## 🏗️ Proposed Solution: 3-Tier Hybrid Search Architecture

### Tier 1: Instant Search (Traditional Text Matching) - 95% of queries
**Cost:** $0 | **Speed:** <100ms

Use **BM25** (Best Match 25) algorithm - industry standard for text search
- Used by: Elasticsearch, Lucene, Solr
- Ranks results by relevance score
- Handles multi-field search (name, company, position)
- Supports field boosting (name matches > company matches)

```python
# Example: "John Google"
scores = {
    "John Smith @ Google": 15.2,  # High: name + company match
    "Jane Doe @ Google": 8.1,      # Medium: company match only
    "John Williams @ Meta": 6.4,   # Low: name match only
    "Sarah Johnson @ Apple": 0.0   # No match
}
```

**Add Fuzzy Matching:**
- Levenshtein distance for typos
- "Gogle" → "Google" (distance=1, allow)
- "Johm" → "John" (distance=1, allow)
- "Smoth" → "Smith" (distance=2, allow if close enough)

**Field Boosting Weights:**
```python
field_weights = {
    'full_name': 3.0,    # Name matches most important
    'company': 2.0,      # Company second
    'position': 1.5,     # Position third
    'email': 1.0         # Email least important
}
```

**When to use:** Simple keyword searches
- "John Smith"
- "Google engineers"
- "Meta VP"
- "Sarah"

**Implementation:** Use `rank-bm25` Python library

---

### Tier 2: Semantic Search (Embeddings) - 30% of queries
**Cost:** $0.001 per search | **Speed:** <500ms

Use **OpenAI embeddings** (text-embedding-3-small) for conceptual matching
- Pre-compute embeddings for all contacts once
- Store in database (1536-dimensional vector)
- At search time: embed query, find nearest neighbors
- Cost: $0.00002 per contact (one-time), $0.0001 per search

```python
# Example: User searches "machine learning expert"
# Semantic search finds:
1. "Senior ML Engineer @ OpenAI" (cosine_similarity=0.89)
2. "AI Researcher @ DeepMind" (0.87)
3. "Data Scientist - NLP @ Google" (0.84)
4. "Software Engineer @ Meta" (0.62) # Lower relevance

# Even though none contain exact phrase "machine learning expert"
```

**When to use:** Conceptual/semantic queries
- "machine learning expert" (finds ML Engineer, AI Researcher, Data Scientist)
- "startup founders" (finds CEO, Co-Founder, Entrepreneur)
- "creative roles" (finds Designer, Artist, Content Creator)

**Implementation:**
1. Generate embeddings for all contacts (concat name + company + position)
2. Store in new `contact_embeddings` table
3. At search: embed query, compute cosine similarity
4. Return top K matches

**Optimization:** Use FAISS or pgvector for fast similarity search

---

### Tier 3: AI-Powered Search (Current Approach) - 10% of queries
**Cost:** $0.02-0.03 per search | **Speed:** 2-5 seconds

Keep current GPT-4 intent extraction for complex queries
- Industry categorization ("who works in tech?")
- Multi-criteria ("senior engineers at tech companies")
- Analytical ("how many people work in finance?")

**When to use:** Complex queries requiring reasoning
- "Who works in tech?" (AI categorizes companies)
- "Most senior person in finance"
- "Engineers at pre-IPO startups"

**Optimization:** Add aggressive caching
```python
# Cache key: query + user_id + contacts_hash
# TTL: 1 hour for same query
cache[query_hash] = search_results
```

---

## 🎮 Search Routing Logic (Decision Tree)

```python
def intelligent_search(query, contacts_df):
    """
    Route query to appropriate search tier
    """

    # Step 1: Check cache first (all tiers)
    cached = check_search_cache(query, contacts_df)
    if cached:
        return cached  # Instant, $0

    # Step 2: Classify query complexity
    complexity = classify_query_complexity(query)

    if complexity == "simple":
        # Tier 1: Traditional BM25 search
        # Examples: "John", "Google", "engineer"
        results = bm25_search(query, contacts_df)
        score_threshold = 0.5

    elif complexity == "semantic":
        # Tier 2: Embedding-based search
        # Examples: "ML expert", "creative roles", "startup people"
        results = semantic_search(query, contacts_df)
        score_threshold = 0.7

    elif complexity == "complex":
        # Tier 3: AI-powered search
        # Examples: "senior tech people", "who works in finance?"
        results = ai_search(query, contacts_df)  # Current approach
        score_threshold = 0.0  # AI already filtered

    # Step 3: Combine with hybrid scoring if needed
    if complexity in ["simple", "semantic"]:
        # Optionally boost with quick AI check for ambiguous queries
        results = apply_hybrid_boost(results, query)

    # Step 4: Cache results
    cache_search_results(query, contacts_df, results)

    return results


def classify_query_complexity(query):
    """Determine which search tier to use"""

    query_lower = query.lower()

    # Simple patterns
    simple_patterns = [
        r'^[\w\s]+$',  # Just names/words: "John Smith", "Google"
        r'^\w+@\w+',   # Email-like: "john@google"
    ]
    if any(re.match(p, query_lower) for p in simple_patterns):
        return "simple"

    # Semantic patterns
    semantic_keywords = [
        'expert', 'specialist', 'creative', 'innovative', 'experienced',
        'skilled in', 'background in', 'passionate about', 'focused on'
    ]
    if any(kw in query_lower for kw in semantic_keywords):
        return "semantic"

    # Complex patterns
    complex_keywords = [
        'in tech', 'in finance', 'in healthcare',  # Industry queries
        'most senior', 'highest level', 'top',     # Ranking queries
        'how many', 'breakdown', 'analyze',        # Analytics queries
        'at startups', 'at big companies',         # Category queries
    ]
    if any(kw in query_lower for kw in complex_keywords):
        return "complex"

    # Default to semantic (middle ground)
    return "semantic"
```

---

## 🚀 Implementation Plan (Prioritized)

### Phase 3B.1: Foundation (Week 1) ⭐ START HERE
**Goal:** Build basic BM25 search with relevance ranking

**Tasks:**
1. Install dependencies:
   ```bash
   pip install rank-bm25 python-Levenshtein
   ```

2. Create `search_engine.py` module:
   ```python
   class ContactSearchEngine:
       def __init__(self, contacts_df):
           self.df = contacts_df
           self.build_bm25_index()

       def build_bm25_index(self):
           # Create searchable documents
           # Tokenize and index

       def search(self, query, top_k=20):
           # BM25 ranking
           # Return sorted by relevance
   ```

3. Add fuzzy matching for typos:
   ```python
   from Levenshtein import distance

   def fuzzy_match(term, candidates, threshold=2):
       matches = []
       for candidate in candidates:
           if distance(term, candidate) <= threshold:
               matches.append(candidate)
       return matches
   ```

4. Implement field boosting:
   ```python
   # Name matches get 3x weight
   # Company matches get 2x weight
   # Position matches get 1.5x weight
   ```

5. Add relevance scores to results:
   ```python
   results = [
       {
           'contact': {...},
           'relevance_score': 0.85,
           'matched_fields': ['full_name', 'company']
       }
   ]
   ```

**Testing:**
- Test queries: ["John", "Google", "engineer", "Gogle" (typo), "VP"]
- Verify results are ranked by relevance
- Verify typos are handled

**Success Metrics:**
- Search completes in <100ms
- Results are relevance-ranked
- Typos within 2 chars are handled
- Cost: $0 per search

---

### Phase 3B.2: Semantic Layer (Week 2)
**Goal:** Add embedding-based search for conceptual queries

**Tasks:**
1. Generate embeddings for all contacts:
   ```python
   def generate_contact_embedding(contact):
       text = f"{contact['full_name']} {contact['company']} {contact['position']}"
       embedding = openai.Embedding.create(
           model="text-embedding-3-small",
           input=text
       )
       return embedding['data'][0]['embedding']
   ```

2. Create `contact_embeddings` table:
   ```sql
   CREATE TABLE contact_embeddings (
       id UUID PRIMARY KEY,
       contact_id UUID REFERENCES contacts(id),
       embedding VECTOR(1536),  -- pgvector extension
       created_at TIMESTAMP
   );

   CREATE INDEX ON contact_embeddings USING ivfflat (embedding vector_cosine_ops);
   ```

3. Implement semantic search:
   ```python
   def semantic_search(query, top_k=20):
       # Embed query
       query_embedding = embed_text(query)

       # Find nearest neighbors (cosine similarity)
       results = supabase.rpc('match_contacts', {
           'query_embedding': query_embedding,
           'match_threshold': 0.7,
           'match_count': top_k
       })

       return results
   ```

4. Add embedding update on contact upload:
   ```python
   # When user uploads CSV
   for contact in new_contacts:
       save_contact_to_db(contact)
       embedding = generate_embedding(contact)
       save_embedding(contact_id, embedding)
   ```

**Testing:**
- Test queries: ["ML expert", "creative roles", "startup founders"]
- Verify conceptual matches work
- Verify fast lookup (<500ms)

**Success Metrics:**
- Semantic queries return relevant results
- Search completes in <500ms
- Cost: ~$0.001 per search
- Embeddings generated on upload

---

### Phase 3B.3: Hybrid Scoring (Week 3)
**Goal:** Combine BM25 + semantic + AI for best results

**Tasks:**
1. Implement hybrid search:
   ```python
   def hybrid_search(query, top_k=20):
       # Get results from multiple tiers
       bm25_results = bm25_search(query, top_k=50)
       semantic_results = semantic_search(query, top_k=50)

       # Combine scores with weights
       combined = {}
       for result in bm25_results:
           combined[result['id']] = {
               'bm25_score': result['score'] * 0.6,
               'semantic_score': 0,
               **result
           }

       for result in semantic_results:
           if result['id'] in combined:
               combined[result['id']]['semantic_score'] = result['score'] * 0.4
           else:
               combined[result['id']] = {
                   'bm25_score': 0,
                   'semantic_score': result['score'] * 0.4,
                   **result
               }

       # Final score = 0.6 * BM25 + 0.4 * semantic
       for item in combined.values():
           item['final_score'] = item['bm25_score'] + item['semantic_score']

       # Sort by final score
       ranked = sorted(combined.values(), key=lambda x: x['final_score'], reverse=True)
       return ranked[:top_k]
   ```

2. Add smart routing logic (see decision tree above)

3. Tune weights empirically:
   ```python
   # A/B test different weight combinations
   weights_to_test = [
       (0.7, 0.3),  # Favor traditional
       (0.6, 0.4),  # Balanced
       (0.5, 0.5),  # Equal
       (0.4, 0.6),  # Favor semantic
   ]
   ```

**Testing:**
- Test mixed queries: ["Google ML engineer", "senior creative at startups"]
- Compare hybrid vs single-tier results
- Measure relevance improvement

**Success Metrics:**
- Hybrid beats single-tier on test queries
- <500ms latency
- Clear relevance improvement

---

### Phase 3B.4: Caching & Performance (Week 4)
**Goal:** Make search instant with aggressive caching

**Tasks:**
1. Implement search result cache:
   ```python
   import hashlib
   from functools import lru_cache

   def get_cache_key(query, contacts_df):
       # Hash query + dataframe content
       df_hash = hashlib.md5(
           pd.util.hash_pandas_object(contacts_df).values
       ).hexdigest()
       query_hash = hashlib.md5(query.encode()).hexdigest()
       return f"{query_hash}_{df_hash}"

   @lru_cache(maxsize=1000)
   def cached_search(cache_key, query, contacts_json):
       # Convert back to df and search
       return search_results
   ```

2. Create `search_cache` table for persistence:
   ```sql
   CREATE TABLE search_cache (
       id UUID PRIMARY KEY,
       user_id UUID REFERENCES users(id),
       query_hash VARCHAR(64),
       contacts_hash VARCHAR(64),
       results JSONB,
       created_at TIMESTAMP,
       last_accessed TIMESTAMP,
       access_count INT DEFAULT 1
   );

   CREATE INDEX ON search_cache (user_id, query_hash, contacts_hash);
   ```

3. Add cache invalidation on contact changes:
   ```python
   def invalidate_search_cache(user_id):
       # Clear cache when user uploads new contacts
       supabase.table('search_cache').delete().eq('user_id', user_id).execute()
   ```

4. Add cache analytics:
   ```python
   cache_stats = {
       'hit_rate': hits / (hits + misses),
       'avg_latency_cached': 5ms,
       'avg_latency_uncached': 250ms
   }
   ```

**Testing:**
- Run same query twice, verify second is instant
- Upload new contacts, verify cache invalidates
- Measure cache hit rate

**Success Metrics:**
- Cache hit rate >60%
- Cached queries <10ms
- Cache invalidates correctly

---

### Phase 3B.5: Search Analytics (Week 5)
**Goal:** Track what users search for to improve quality

**Tasks:**
1. Create `search_analytics` table:
   ```sql
   CREATE TABLE search_analytics (
       id UUID PRIMARY KEY,
       user_id UUID REFERENCES users(id),
       query TEXT,
       query_type VARCHAR(50),  -- simple, semantic, complex
       search_tier VARCHAR(50),  -- bm25, semantic, ai
       results_count INT,
       top_result_clicked BOOLEAN,
       click_position INT,
       latency_ms INT,
       cached BOOLEAN,
       created_at TIMESTAMP
   );
   ```

2. Log every search:
   ```python
   def log_search(user_id, query, results, latency, cached):
       analytics.log_search_query(
           user_id=user_id,
           query=query,
           query_type=classify_query_complexity(query),
           results_count=len(results),
           latency_ms=latency,
           cached=cached
       )
   ```

3. Track click-through:
   ```python
   # When user clicks on a search result
   def log_result_click(search_id, position):
       # Track which result was clicked
       # Position tells us if top results are relevant
   ```

4. Build search analytics dashboard:
   ```python
   # Admin dashboard showing:
   - Most common searches
   - Searches with 0 results (improve these!)
   - Average latency by tier
   - Cache hit rate
   - Click-through rate by position
   ```

**Testing:**
- Perform 100 test searches
- Verify all logged correctly
- View analytics dashboard

**Success Metrics:**
- All searches logged
- Can identify problematic queries
- Can measure search quality over time

---

### Phase 3B.6: Advanced Features (Week 6)
**Goal:** Polish and add nice-to-have features

**Tasks:**
1. Add synonym handling:
   ```python
   synonyms = {
       'engineer': ['developer', 'swe', 'programmer', 'coder'],
       'manager': ['mgr', 'lead', 'head'],
       'vp': ['vice president', 'v.p.'],
   }
   ```

2. Add query expansion:
   ```python
   # "ML" → expand to ["machine learning", "ML", "AI"]
   ```

3. Add autocomplete:
   ```python
   # As user types, suggest:
   - Common searches
   - Company names
   - Position titles
   - Previous searches
   ```

4. Add search filters UI:
   ```python
   # Sidebar filters:
   - Company (dropdown)
   - Position (dropdown)
   - Seniority (slider)
   - Only my contacts / extended network (toggle)
   ```

5. Add "Did you mean?" suggestions:
   ```python
   # If 0 results, check for typos
   # "Gooogle engineer" → "Did you mean: Google engineer?"
   ```

6. Add search result explanations:
   ```python
   # Show why each result matched
   "John Smith @ Google - Engineer"
   ✓ Matched: name (0.9), company (0.8), position (0.7)
   ```

**Testing:**
- Test all advanced features
- User acceptance testing
- Performance regression testing

**Success Metrics:**
- Features work smoothly
- No performance degradation
- Positive user feedback

---

## 📈 Success Metrics & KPIs

### Performance Metrics
- **Latency:**
  - Tier 1 (BM25): <100ms (target: 50ms)
  - Tier 2 (Semantic): <500ms (target: 300ms)
  - Tier 3 (AI): <3s (current: 2-5s)
  - Cached: <10ms

- **Cost per search:**
  - Tier 1: $0
  - Tier 2: $0.001
  - Tier 3: $0.02
  - Target average: <$0.005 (90% reduction)

- **Cache hit rate:**
  - Target: >60%
  - Stretch: >80%

### Quality Metrics
- **Relevance:** Top 3 results contain expected answer (>90%)
- **Recall:** Can find all relevant contacts (>95%)
- **Precision:** Results are actually relevant (>85%)
- **Zero results rate:** <5% of searches

### Business Metrics
- **Search usage:** Track searches per user per session
- **Click-through rate:** % of searches where user clicks a result
- **Time to result:** How long user takes to find what they need
- **Repeat searches:** Are users re-searching (sign of poor results)?

---

## 🧪 Testing Strategy

### Test Query Categories
Create benchmark test set:

**1. Simple Name Searches (Tier 1)**
```python
test_queries = [
    "John",
    "John Smith",
    "J. Smith",
    "Smith, John",  # Different format
]
```

**2. Company Searches (Tier 1)**
```python
test_queries = [
    "Google",
    "Google engineer",
    "engineers at Google",
    "Gogle",  # Typo test
]
```

**3. Position Searches (Tier 1)**
```python
test_queries = [
    "engineer",
    "software engineer",
    "VP",
    "CEO",
]
```

**4. Semantic Searches (Tier 2)**
```python
test_queries = [
    "machine learning expert",
    "creative roles",
    "startup founders",
    "people passionate about AI",
]
```

**5. Complex Searches (Tier 3)**
```python
test_queries = [
    "who works in tech?",
    "most senior person in finance",
    "engineers at pre-IPO startups",
    "how many people work at Google?",  # Analytics
]
```

**6. Edge Cases**
```python
test_queries = [
    "",  # Empty
    "asdfjkl",  # Nonsense
    "a",  # Single char
    "John Smith Google Microsoft Engineer VP CEO",  # Too many terms
    "🚀",  # Emoji
]
```

### Evaluation Method
For each test query:
1. Run search
2. Measure latency
3. Check top 5 results
4. Manually label: relevant (1) or not (0)
5. Calculate:
   - Precision@5 = relevant results / 5
   - MRR (Mean Reciprocal Rank) = 1 / position of first relevant result
   - NDCG (Normalized Discounted Cumulative Gain)

**Example:**
```python
query = "Google engineer"
results = [
    "John Smith, Software Engineer @ Google",     # Relevant: 1
    "Jane Doe, Senior Engineer @ Google",         # Relevant: 1
    "Bob Johnson, VP Engineering @ Google",       # Relevant: 1
    "Alice Williams, Product Manager @ Google",   # Not relevant: 0 (not engineer)
    "Charlie Brown, Engineer @ Microsoft",        # Not relevant: 0 (wrong company)
]

precision_at_5 = 3/5 = 0.6
mrr = 1/1 = 1.0 (first result is relevant)
```

**Goal:** Precision@5 > 0.8 on all test queries

---

## 💰 Cost-Benefit Analysis

### Current State (all searches use AI)
- **Queries per user per day:** ~10
- **Cost per query:** $0.025
- **Daily cost (100 users):** 10 * 100 * $0.025 = **$25/day = $750/month**
- **Latency:** 2-5 seconds

### Future State (hybrid search)
**Distribution:**
- 60% Tier 1 (BM25): 600 queries/day * $0 = **$0**
- 30% Tier 2 (Semantic): 300 queries/day * $0.001 = **$0.30**
- 10% Tier 3 (AI): 100 queries/day * $0.025 = **$2.50**
- **Daily cost:** $2.80 = **$84/month**

**Savings:**
- **$666/month** (89% reduction)
- **$7,992/year**

**Performance Improvement:**
- Average latency: 0.6 * 50ms + 0.3 * 300ms + 0.1 * 3000ms = **420ms** (vs 3000ms)
- **7x faster**

---

## 🚨 Risks & Mitigations

### Risk 1: Embeddings cost too much
**Mitigation:**
- Only generate embeddings on contact upload (one-time cost)
- Use smallest embedding model (text-embedding-3-small)
- Estimated cost: 1000 contacts * $0.00002 = **$0.02** (one-time)

### Risk 2: Search quality degrades
**Mitigation:**
- A/B test new search vs old search
- Keep old AI search as fallback
- Monitor search analytics for quality drops
- User feedback button on search results

### Risk 3: pgvector not available on Supabase
**Mitigation:**
- Check if pgvector extension enabled
- Alternative: Store embeddings as JSON, compute similarity in Python
- Alternative: Use FAISS library for local similarity search

### Risk 4: Implementation takes too long
**Mitigation:**
- Prioritize Phase 3B.1 (BM25) - biggest impact
- Phase 3B.2-3B.6 are optional enhancements
- Can deploy incrementally

---

## 🎯 Phase 3B.1 Implementation Spec (START HERE)

**File:** `search_engine.py` (new file)

```python
"""
Intelligent search engine for LinkedIn contacts
Supports BM25 ranking, fuzzy matching, field boosting
"""

from rank_bm25 import BM25Okapi
import pandas as pd
from typing import List, Dict, Any
import re
from Levenshtein import distance
import numpy as np


class ContactSearchEngine:
    """
    Multi-field search engine with relevance ranking

    Features:
    - BM25 ranking algorithm
    - Fuzzy matching (typo tolerance)
    - Field boosting (name > company > position)
    - Fast (<100ms for 1000 contacts)
    """

    def __init__(self, contacts_df: pd.DataFrame):
        """
        Initialize search engine with contacts

        Args:
            contacts_df: DataFrame with columns: full_name, company, position, email
        """
        self.df = contacts_df.copy()
        self.field_weights = {
            'full_name': 3.0,
            'company': 2.0,
            'position': 1.5,
            'email': 1.0
        }
        self.fuzzy_threshold = 2  # Max Levenshtein distance for fuzzy match

        # Build search index
        self.build_index()

    def build_index(self):
        """Build BM25 search index"""

        # Create searchable documents (one per contact)
        documents = []
        for _, row in self.df.iterrows():
            # Combine fields with boosting (repeat high-weight fields)
            doc_parts = []

            # Name (repeat 3x for 3.0 weight)
            if pd.notna(row['full_name']):
                doc_parts.extend([row['full_name']] * 3)

            # Company (repeat 2x for 2.0 weight)
            if pd.notna(row['company']):
                doc_parts.extend([row['company']] * 2)

            # Position (repeat 1x for 1.5 weight, round down to 1)
            if pd.notna(row['position']):
                doc_parts.append(row['position'])

            # Email (1x)
            if pd.notna(row['email']):
                doc_parts.append(row['email'])

            # Tokenize document
            doc = ' '.join(doc_parts)
            tokens = self.tokenize(doc)
            documents.append(tokens)

        # Build BM25 index
        self.bm25 = BM25Okapi(documents)
        self.documents = documents

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into searchable terms

        Args:
            text: Input text

        Returns:
            List of tokens (lowercase, alphanumeric)
        """
        # Lowercase
        text = text.lower()

        # Split on non-alphanumeric (keep @ for emails)
        tokens = re.findall(r'[@\w]+', text)

        return tokens

    def search(
        self,
        query: str,
        top_k: int = 20,
        enable_fuzzy: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search contacts with relevance ranking

        Args:
            query: Search query (e.g., "John Google", "VP engineering")
            top_k: Number of results to return
            enable_fuzzy: Enable fuzzy matching for typos

        Returns:
            List of results with relevance scores
            [
                {
                    'contact': {...},  # Full contact row
                    'relevance_score': 0.85,
                    'matched_fields': ['full_name', 'company']
                }
            ]
        """

        # Tokenize query
        query_tokens = self.tokenize(query)

        if not query_tokens:
            return []

        # Apply fuzzy matching if enabled
        if enable_fuzzy:
            query_tokens = self.apply_fuzzy_matching(query_tokens)

        # Get BM25 scores
        scores = self.bm25.get_scores(query_tokens)

        # Get top K results
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = scores[idx]

            # Skip zero-score results
            if score <= 0:
                continue

            # Get contact
            contact = self.df.iloc[idx].to_dict()

            # Identify which fields matched
            matched_fields = self.identify_matched_fields(contact, query_tokens)

            results.append({
                'contact': contact,
                'relevance_score': float(score),
                'matched_fields': matched_fields
            })

        return results

    def apply_fuzzy_matching(self, query_tokens: List[str]) -> List[str]:
        """
        Expand query tokens with fuzzy matches

        Example: ["gogle"] → ["gogle", "google"]

        Args:
            query_tokens: Original query tokens

        Returns:
            Expanded tokens including fuzzy matches
        """

        # Get all unique terms from all documents
        all_terms = set()
        for doc in self.documents:
            all_terms.update(doc)

        expanded_tokens = []
        for token in query_tokens:
            # Always include original
            expanded_tokens.append(token)

            # Find fuzzy matches
            for term in all_terms:
                if distance(token, term) <= self.fuzzy_threshold:
                    expanded_tokens.append(term)

        return expanded_tokens

    def identify_matched_fields(
        self,
        contact: Dict[str, Any],
        query_tokens: List[str]
    ) -> List[str]:
        """
        Identify which fields matched the query

        Args:
            contact: Contact dict
            query_tokens: Query tokens

        Returns:
            List of matched field names
        """

        matched = []

        for field in ['full_name', 'company', 'position', 'email']:
            if pd.notna(contact.get(field)):
                field_value = str(contact[field]).lower()

                # Check if any query token appears in field
                for token in query_tokens:
                    if token in field_value:
                        matched.append(field)
                        break

        return matched


# ============================================
# HELPER FUNCTIONS
# ============================================

def format_search_results(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Format search results for display

    Args:
        results: Search results from ContactSearchEngine

    Returns:
        DataFrame with contacts and relevance scores
    """

    if not results:
        return pd.DataFrame()

    # Extract contacts
    contacts = [r['contact'] for r in results]
    df = pd.DataFrame(contacts)

    # Add relevance score
    df['relevance_score'] = [r['relevance_score'] for r in results]
    df['matched_fields'] = [', '.join(r['matched_fields']) for r in results]

    return df


def search_with_highlighting(
    engine: ContactSearchEngine,
    query: str,
    top_k: int = 20
) -> str:
    """
    Search and return formatted results with highlighting

    Args:
        engine: ContactSearchEngine instance
        query: Search query
        top_k: Number of results

    Returns:
        Markdown-formatted results string
    """

    results = engine.search(query, top_k=top_k)

    if not results:
        return "No results found."

    output = []
    for i, result in enumerate(results, 1):
        contact = result['contact']
        score = result['relevance_score']
        matched = result['matched_fields']

        output.append(f"**{i}. {contact['full_name']}**")
        output.append(f"   {contact['position']} @ {contact['company']}")
        output.append(f"   ✓ Matched: {', '.join(matched)} (score: {score:.2f})")
        output.append("")

    return "\n".join(output)
```

**Usage Example:**
```python
# In app.py

import search_engine as se

# Initialize search engine (do this once when contacts load)
engine = se.ContactSearchEngine(contacts_df)

# Perform search
results = engine.search("John Google", top_k=10)

# Display results
for result in results:
    st.write(f"**{result['contact']['full_name']}** - Score: {result['relevance_score']:.2f}")
    st.write(f"   {result['contact']['position']} @ {result['contact']['company']}")
    st.write(f"   Matched: {', '.join(result['matched_fields'])}")
```

---

## ✅ Next Steps

1. **Review this plan** - Does this align with your vision?
2. **Prioritize phases** - Do all 6 phases or just 3B.1?
3. **Set timeline** - When to start, when to ship?
4. **Define test queries** - What searches must work perfectly?
5. **Approve Phase 3B.1** - Start with BM25 search engine?

**Recommendation:** Start with Phase 3B.1 (BM25 search) - it delivers 80% of the value with 20% of the effort.

**Questions:**
- Do you want to proceed with Phase 3B.1 implementation now?
- Are there specific search queries that must work perfectly?
- What's your priority: speed, cost, or quality?
- Should we A/B test new search vs. current AI search?
