---
name: interview-agent
description: Build and improve a realistic multi-turn AI technical interviewer that adapts questions to candidate profiles, curriculum progress, answers, difficulty, and interview state.
---

# Interview Agent Skill

## Goal
Build an interviewer, not a static questionnaire.

## Core requirements
- Conduct a realistic multi-turn technical interview.
- Ask at least 8 questions.
- Cover at least 4 distinct curriculum days.
- Generate follow-up questions from previous answers.
- Maintain interview state and conversation context.
- Avoid repeating questions.
- Respect completed, skipped, and attempted topics.
- Adapt difficulty based on answer quality.
- End with actionable structured feedback.

## Interview state
Prefer an explicit state object containing:
- candidate_id
- current_day
- covered_days
- asked_questions
- answers
- scores
- strengths
- weaknesses
- difficulty
- questions_remaining
- interview_stage

## Question strategy
Use a mix of:
1. Conceptual questions
2. Why/how reasoning questions
3. Practical implementation questions
4. Architecture/design questions
5. Debugging/troubleshooting questions
6. Follow-up probing questions

Do not blindly follow a fixed questionnaire.

## Adaptation
Strong answer -> increase depth/difficulty.
Partial answer -> probe the missing concept.
Vague answer -> ask for an example or implementation detail.
Incorrect answer -> diagnose the misconception and ask a targeted follow-up.
"I don't know" -> briefly acknowledge it and move to another useful question.

## Scope
Questions must be grounded in the supplied curriculum and candidate profile. Do not invent completed learning experiences.

## Output
Use structured outputs where possible. Separate:
- question to candidate
- internal evaluation
- state update
- final feedback

Never expose hidden reasoning or internal scoring rationale to the candidate.
