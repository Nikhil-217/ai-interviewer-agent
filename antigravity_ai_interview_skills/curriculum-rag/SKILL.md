---
name: curriculum-rag
description: Build curriculum-aware retrieval for an AI interview agent using curriculum JSON, candidate progress, semantic search, and metadata filtering.
---

# Curriculum RAG Skill

## Goal
Retrieve the most relevant curriculum material before generating interview questions.

## Input data
Support:
- modules
- days
- topics
- learning objectives
- tools
- missions
- completed topics
- attempted topics
- skipped topics
- learning signals

## Recommended pipeline
1. Load and validate curriculum JSON.
2. Normalize each curriculum day/topic into retrieval documents.
3. Preserve metadata such as day, module, topic, objectives, and tools.
4. Create embeddings.
5. Store vectors in a vector database such as ChromaDB or FAISS.
6. Retrieve candidate-relevant topics.
7. Filter out skipped/unavailable topics when appropriate.
8. Re-rank retrieved topics before question generation.

## Retrieval metadata
Each chunk should retain:
- day
- module
- topic
- learning_objectives
- tools
- source_id

## Candidate-aware retrieval
Prioritize:
1. Completed topics
2. Topics with meaningful attempts
3. Topics relevant to recent interview answers
4. Weak areas discovered during the interview

Avoid repeatedly retrieving the same topic unless a follow-up is intentional.

## Quality rules
- Prefer semantic retrieval over keyword-only matching.
- Use metadata filtering for day/topic constraints.
- Keep retrieved context concise.
- Never fabricate curriculum content.
- Make retrieval deterministic enough to test.

## Fallback
If vector retrieval is unavailable, use metadata/keyword retrieval so the API can still function.
