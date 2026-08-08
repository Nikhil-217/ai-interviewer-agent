---
name: interview-evaluator
description: Evaluate technical interview answers with structured scoring, identify strengths and weaknesses, and choose adaptive follow-up questions.
---

# Interview Evaluator Skill

## Goal
Evaluate candidate answers consistently and drive the next interview action.

## Evaluation dimensions
Score each answer using a consistent scale, for example 0-10:
- technical_accuracy
- conceptual_depth
- reasoning
- practical_understanding
- clarity
- completeness

Optionally calculate an overall score.

## Evaluation process
For every answer:
1. Identify what the candidate correctly explained.
2. Identify missing concepts.
3. Identify misconceptions.
4. Determine confidence level from evidence in the answer.
5. Decide whether to probe, increase difficulty, maintain difficulty, or change topic.

Do not reveal hidden chain-of-thought.

## Adaptive rules
- 8-10: ask a deeper or practical question.
- 5-7: ask a targeted clarification/follow-up.
- 0-4: diagnose the gap with a simpler question or move to another topic after one useful probe.

## Follow-up quality
Good follow-ups should depend on the candidate's actual answer.

Example:
Candidate: "RAG uses embeddings to search documents."
Follow-up: "Why can semantically similar retrieval still produce irrelevant chunks, and how would you reduce that problem?"

Avoid generic follow-ups such as "Can you explain more?"

## Final feedback
Return structured feedback containing:
- overall_score
- strengths
- weaknesses
- topics_mastered
- topics_needing_review
- recommended_next_steps
- per-topic performance
- concise interviewer summary
