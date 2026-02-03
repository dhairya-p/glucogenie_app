# Backend Quick Start

## 1) Install Dependencies
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2) Environment Variables
Create `backend/.env` (copy from `.env.example`):

```bash
cp .env.example .env
```

Required:
```
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_INDEX=diabetes-medical-knowledge
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...
NEO4J_DATABASE=neo4j
```

## 3) Run the Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 4) Verify
- Health: `http://localhost:8000/health`
- Docs: `http://localhost:8000/docs`

Expected health response:
```json
{"api":"ok","supabase":true}
```

## 5) Notes
- Pinecone namespaces: `clinical_safety`, `dietician_docs`
- Neo4j KG is built from `notebooks/drug_interaction_docs`

