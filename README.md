# Agentic AI Demo

Minimalist agentic AI demonstration using prompt engineering. This app is generated using Claude for educational purpose only.

## Architecture

```
Client Request
      ↓
Coordinator API (FastAPI)
      ↓
  ┌───┴───┐
  ↓       ↓
Architect Lawyer
Agent     Agent
  ↓       ↓
  └───┬───┘
      ↓
vLLM Backend (GPU)
microsoft/Phi-3-mini-4k-instruct
      ↓
  Response
```

## Agents

### 1. Architect Agent
**Role**: Software architecture and technology recommendations

**Capabilities**:
- Architecture design patterns
- Technology stack recommendations
- Complexity assessment
- Timeline estimation

**Example Query**:
```bash
curl -X POST http://<SERVICE_IP>/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Design a real-time analytics platform for IoT sensors",
    "agent": "architect"
  }'
```

### 2. Lawyer Agent
**Role**: Open source licensing and legal compliance

**Capabilities**:
- License analysis
- Commercial permissibility
- Risk assessment
- Compliance guidance

**Example Query**:
```bash
curl -X POST http://<SERVICE_IP>/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Can I use Apache Kafka and Kubernetes in a commercial product?",
    "agent": "lawyer"
  }'
```

### 3. Coordinator (Auto-routing)
**Role**: Automatic agent selection

**Example Query**:
```bash
curl -X POST http://<SERVICE_IP>/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the licensing implications of using TensorFlow?",
    "agent": "auto"
  }'
```

## Deployment

See `./stack help`

## Testing

### 1. Check Service Health
```bash
export SERVICE_IP=$(kubectl get svc -n $K8S_NAMESPACE agentic-demo -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

curl http://$SERVICE_IP/health
```

### 2. List Available Agents
```bash
curl http://$SERVICE_IP/agents | jq
```

### 3. Test Architect Agent
```bash
curl -X POST http://$SERVICE_IP/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Design a microservices architecture for an e-commerce platform with high availability requirements",
    "agent": "architect"
  }' | jq
```

### 4. Test Lawyer Agent
```bash
curl -X POST http://$SERVICE_IP/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze the licensing requirements for using PostgreSQL, Redis, and Elasticsearch in a SaaS product",
    "agent": "lawyer"
  }' | jq
```

### 5. Test Auto-Routing
```bash
# Should route to Architect
curl -X POST http://$SERVICE_IP/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What technology stack would you recommend for building a real-time chat application?",
    "agent": "auto"
  }' | jq

# Should route to Lawyer
curl -X POST http://$SERVICE_IP/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Is GPL-licensed software allowed in commercial products?",
    "agent": "auto"
  }' | jq
```

## Demo Scenarios

### Scenario 1: Full Software Project Analysis

**Step 1 - Architecture**: Ask architect about technology choices
```bash
curl -X POST http://$SERVICE_IP/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Design a video streaming platform using open source technologies. Include CDN, transcoding, and storage recommendations.",
    "agent": "architect"
  }' | jq
```

**Step 2 - Legal**: Ask lawyer about licensing
```bash
curl -X POST http://$SERVICE_IP/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Review the licensing implications of using FFmpeg, Nginx, and MinIO for a commercial video streaming service",
    "agent": "lawyer"
  }' | jq
```

### Scenario 2: Machine Learning Pipeline

**Architecture Query**:
```bash
curl -X POST http://$SERVICE_IP/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Design an ML training pipeline with experiment tracking, model versioning, and deployment automation",
    "agent": "auto"
  }' | jq
```

**Legal Query**:
```bash
curl -X POST http://$SERVICE_IP/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Can I use PyTorch, MLflow, and Kubeflow in a commercial ML product?",
    "agent": "auto"
  }' | jq
```

## Architecture Highlights

### Why This Design?

1. **Single App, Multiple Personalities**: Uses prompt engineering instead of multiple microservices
   - Simpler deployment
   - No service mesh complexity
   - Easier to maintain

2. **GPU Sharing**: All agents share the same vLLM inference backend
   - Efficient GPU utilization
   - Cost-effective
   - Simple architecture

3. **Auto-Routing**: Coordinator agent determines appropriate specialist
   - User-friendly
   - Demonstrates AI-driven workflow
   - Easy to extend

4. **Production-Ready**:
   - Health checks
   - Auto-scaling (HPA)
   - Load balancing
   - Resource limits

## Performance

- **Cold Start**: ~100-200ms (FastAPI app)
- **Inference Time**: ~1-3s per query (depends on GPU availability and query complexity)
- **Throughput**: Limited by GPU inference backend capacity

## Extending the Demo

### Add New Agent

1. Add system prompt to `app.py`:
```python
AGENT_PROMPTS["devops"] = """You are a DevOps engineer..."""
```

2. Update the agent type in models:
```python
agent: Literal["architect", "lawyer", "devops", "auto"] = "auto"
```

3. Update coordinator prompt to recognize new agent

4. Rebuild and redeploy

### Use Different LLM

Update ConfigMap in `agentic-demo.yaml`:
```yaml
data:
  MODEL_NAME: "mistralai/Mistral-7B-Instruct-v0.2"
```

## Troubleshooting

### Agent Returns Empty Response
- Check vLLM inference backend is running
- Verify INFERENCE_URL is correct
- Check network connectivity between namespaces

### High Latency
- Check GPU node availability
- Scale up inference backend replicas
- Increase timeout values

### Out of Memory
- Reduce max_tokens in app.py
- Use quantized model (4-bit)
- Scale down concurrent requests

## Cost Optimization

- **Development**: Use CPU inference for testing (slower but cheaper)
- **Production**: Use GPU autoscaling with KEDA
- **Idle Times**: Scale inference backend to 0 when not in use

## References

- [Microsoft Phi-3 Documentation](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct)
- [vLLM Documentation](https://docs.vllm.ai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
