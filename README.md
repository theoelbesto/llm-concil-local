# llm-council-local

Local, distributed multi-LLM system with Council agents, anonymized peer review, and a Chairman synthesizer. All inference runs locally via Ollama.

## Architecture
- Stage 1: Council agents independently answer the same query.
- Stage 2: Agents review anonymized responses (Response A/B/C) and rank them.
- Stage 3: Chairman synthesizes a final answer using first opinions + rankings.

## Requirements
- Python 3.10+
- Ollama installed and running on each machine
- Models pulled locally on each machine

## Setup
1) Create a virtual environment per service (recommended).
2) Install dependencies for each service:

```bash
pip install -r agent_service/requirements.txt
pip install -r chairman_service/requirements.txt
pip install -r orchestrator/requirements.txt
```

3) Start Ollama and pull models (example):

```bash
ollama pull llama3.1:8b
```

## Run Council Agents (on multiple machines)
Set env vars per agent:

```bash
export MODEL_ID=council-a
export OLLAMA_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.1:8b
```

Run each agent:

```bash
uvicorn agent_service.app:app --host 0.0.0.0 --port 8001
```

Repeat on other machines with different MODEL_IDs and ports.

## Run Chairman Service (separate machine)

```bash
export MODEL_ID=chairman
export OLLAMA_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.1:8b

uvicorn chairman_service.app:app --host 0.0.0.0 --port 8002
```

## Run Orchestrator

```bash
export COUNCIL_ENDPOINTS=http://10.0.0.2:8001,http://10.0.0.3:8001,http://10.0.0.4:8001
export CHAIR_ENDPOINT=http://10.0.0.10:8002

uvicorn orchestrator.app:app --host 0.0.0.0 --port 8000
```

## Test the Pipeline

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain overfitting in machine learning."}'
```

The orchestrator returns JSON with:
- stage1_first_opinions
- stage2_anonymized_responses
- stage2_reviews
- stage3_final

## Demo Day Checklist
- [ ] Agent health: `curl http://AGENT_IP:8001/health`
- [ ] Chairman health: `curl http://CHAIR_IP:8002/health`
- [ ] Orchestrator health: `curl http://ORCH_IP:8000/health`
- [ ] Sample run returns all stages

## Generative AI Usage Statement
This project uses locally hosted large language models through Ollama. No cloud-based model APIs are called. All prompts and responses remain on the local network between services.
