# Pinecone Database Setup

## Overview

Your content workflow now saves approved content to Pinecone, a vector database for semantic search and retrieval.

## Setup Instructions

### 1. Get Your Pinecone API Key

1. Go to https://www.pinecone.io/
2. Sign up or log in
3. Navigate to your dashboard
4. Click "API Keys" in the left sidebar
5. Copy your API key

### 2. Add to .env File

Open `.env` and replace the placeholder:

```bash
PINECONE_API_KEY=your_actual_api_key_here
```

### 3. How It Works

When content goes through the full workflow and all steps are approved:

1. **save_to_db_node** triggers after human approval
2. Combines all completed steps into final content
3. Connects to Pinecone using your API key
4. Creates index `langgraph-content` (if it doesn't exist)
5. Stores metadata:
   - Title (from user input)
   - Content preview (first 1000 chars)
   - Full content length
   - Number of steps
   - Timestamp
   - Content plan

### 4. Database Structure

**Index Name:** `langgraph-content`
**Dimension:** 1536 (OpenAI embedding size)
**Metric:** Cosine similarity
**Cloud:** AWS (us-east-1)

### 5. Current Implementation

**Note:** The current implementation stores metadata only. For full vector embeddings:

1. Generate embeddings using OpenAI's API:

```python
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.embeddings.create(
    model="text-embedding-ada-002",
    input=full_content
)
embedding = response.data[0].embedding
```

2. Store vector with metadata:

```python
index.upsert(vectors=[{
    "id": content_id,
    "values": embedding,  # 1536-dimensional vector
    "metadata": metadata
}])
```

### 6. Fallback Behavior

If Pinecone API key is not provided:

- Content is still saved to the workflow state
- `final_content` field contains the complete output
- A message displays: "Content saved to state only"

### 7. Querying Saved Content (Future)

Once embeddings are implemented, you can search content semantically:

```python
query_embedding = generate_embedding(query_text)
results = index.query(
    vector=query_embedding,
    top_k=5,
    include_metadata=True
)
```

## Benefits

✅ **Persistent Storage**: Content survives beyond workflow execution
✅ **Semantic Search**: Find similar content by meaning, not just keywords
✅ **Scalable**: Pinecone handles millions of vectors
✅ **Fast Retrieval**: Optimized for similarity search
✅ **Version History**: Each save creates a new entry with timestamp

## Next Steps

1. Add your Pinecone API key to `.env`
2. Test the workflow end-to-end
3. Check Pinecone dashboard to see stored content
4. (Optional) Implement full vector embeddings for semantic search
