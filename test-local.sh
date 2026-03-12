#!/bin/bash
# Local testing script - runs FastAPI app locally and tests against remote vLLM

set -e

# Configuration
SERVICE_URL="${SERVICE_URL:-http://localhost:8080}"
INFERENCE_URL="${INFERENCE_URL:-http://inference.inference.svc.cluster.local/v1/chat/completions}"

printf "Starting local test...\n\n"

# Test 1: Health check
printf "1. Testing health endpoint...\n"
curl -s "$SERVICE_URL/health" | jq
printf "\n"

# Test 2: List agents
printf "2. Listing available agents...\n"
curl -s "$SERVICE_URL/agents" | jq
printf "\n"

# Test 3: Architect agent
printf "3. Testing Architect Agent...\n"
curl -s -X POST "$SERVICE_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Design a real-time data pipeline for IoT sensors using open source technologies",
    "agent": "architect"
  }' | jq
printf "\n"

# Test 4: Lawyer agent
printf "4. Testing Lawyer Agent...\n"
curl -s -X POST "$SERVICE_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the licensing requirements for using Apache Kafka in a commercial product?",
    "agent": "lawyer"
  }' | jq
printf "\n"

# Test 5: Auto-routing (should go to architect)
printf "5. Testing Auto-routing (Architecture question)...\n"
curl -s -X POST "$SERVICE_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What technology stack would you recommend for building a microservices platform?",
    "agent": "auto"
  }' | jq
printf "\n"

# Test 6: Auto-routing (should go to lawyer)
printf "6. Testing Auto-routing (Legal question)...\n"
curl -s -X POST "$SERVICE_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Is GPL-licensed software compatible with proprietary software?",
    "agent": "auto"
  }' | jq
printf "\n"

printf "All tests completed!\n"
