---
name: agent-testing
description: Test AI interview agents for functional requirements, adaptive behavior, context retention, structured outputs, and edge cases.
---

# Agent Testing Skill

## Goal
Test the interview system as an engineered product, not just as an LLM prompt.

## Minimum acceptance tests
Verify:
- at least 8 questions
- at least 4 curriculum days
- follow-up questions depend on previous answers
- conversation context is preserved
- structured final feedback is produced
- required HTTP endpoint exists
- candidate profile affects interview selection

## Behavioral tests
Test:
- excellent answer
- partial answer
- vague answer
- incorrect answer
- "I don't know"
- repeated answer
- topic change
- skipped topic
- incomplete candidate profile
- candidate with few completed days
- duplicate question prevention
- context retention across turns

## Retrieval tests
Verify:
- relevant curriculum days are retrieved
- metadata is preserved
- skipped topics are filtered appropriately
- fabricated topics are not returned
- fallback retrieval works

## API tests
Test:
- valid request
- invalid JSON
- missing candidate
- malformed curriculum
- empty answer
- session continuation
- interview completion
- structured response schema

## Quality principle
LLM behavior is probabilistic. Use deterministic validation around it:
- Pydantic schemas
- minimum counts
- allowed topic IDs
- state transition validation
- duplicate detection
- explicit completion conditions
