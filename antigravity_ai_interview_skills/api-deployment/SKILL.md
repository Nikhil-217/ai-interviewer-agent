---
name: api-deployment
description: Build, validate, containerize, and deploy the AI Interview Agent as a production-style HTTP service.
---

# API and Deployment Skill

## Goal
Expose a reliable HTTP endpoint for the interview agent.

## Recommended stack
- Python
- FastAPI
- Pydantic
- Uvicorn
- Docker
- Cloud Run or another container platform

## API principles
- Validate every request with Pydantic.
- Return predictable JSON responses.
- Separate API, agent, retrieval, evaluation, and state-management layers.
- Never expose API keys.
- Load secrets from environment variables.
- Return useful HTTP status codes.
- Add structured logging.

## Suggested endpoints
Adapt these to the supplied technical specification:
- POST /interview/start
- POST /interview/turn
- POST /interview/finish
- GET /health

If the technical specification requires a different contract, follow it exactly.

## Suggested project structure
app/
  main.py
  api/
  agents/
  retrieval/
  evaluation/
  models/
  services/
  tests/

## Deployment checklist
- requirements.txt or pyproject.toml
- Dockerfile
- environment-variable configuration
- health endpoint
- startup command
- API contract tests
- no secrets committed to Git
- production logging
- graceful error handling

## Important
The supplied Technical Specification is authoritative. Do not invent or alter its required request/response contract.
