# 🚀 Diabetes FYP - Next Steps & Roadmap

## ✅ Current State (What's Working)

### Backend (FastAPI)
- ✅ **Authentication**: Supabase JWT validation with fallback
- ✅ **Streaming Chat**: SSE-based real-time chat responses
- ✅ **Agent Architecture**: 
  - Router Agent (intent classification)
  - Lifestyle Analyst (comprehensive data analysis)
  - Clinical Safety Agent (medication/condition checks)
  - Cultural Dietitian Agent (food image analysis - stub)
- ✅ **Data Access**: Full access to all Supabase tables:
  - `profiles` (name, age, sex, ethnicity, activity_level)
  - `conditions` (medical conditions)
  - `medications` (prescribed medications)
  - `glucose_readings` (with timing, notes)
  - `activity_logs` (duration, intensity)
  - `weight_logs` (weight tracking)
  - `medication_logs` (medication adherence)
  - `meal_logs` (if exists, otherwise inferred from glucose timing)
- ✅ **Comprehensive Analysis**: 
  - Glucose trends, variability, time-in-range
  - Activity-glucose correlations
  - Weight tracking and trends
  - Medication adherence monitoring
  - Personalized insights based on conditions/medications

### Frontend (Flutter)
- ✅ **Authentication**: Supabase auth integration
- ✅ **Chat Interface**: Real-time streaming chat with Riverpod
- ✅ **Data Logging**: Glucose, activity, weight, medications
- ✅ **Profile Management**: User profile with all fields

---

## 🎯 Immediate Next Steps (Priority Order)

### 1. **Neo4j GraphRAG Integration** (High Priority)

**Why**: Enable medical knowledge graph for:
- Evidence-based recommendations
- Drug-drug interaction checks
- Condition-medication relationships
- Singapore-specific dietary knowledge
- Cultural food recommendations

**Implementation Steps**:

#### Step 1.1: Set up Neo4j Connection
```python
# backend/app/core/neo4j_client.py
from neo4j import GraphDatabase
import os

class Neo4jClient:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        username = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        
        if not password:
            raise ValueError("NEO4J_PASSWORD not set")
        
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
    
    def close(self):
        self.driver.close()
    
    def query(self, cypher: str, parameters: dict = None):
        with self.driver.session() as session:
            return session.run(cypher, parameters or {})
```

#### Step 1.2: Create Medical Knowledge Graph Schema
```cypher
// Nodes
CREATE (d:Diabetes {type: "Type 2"})
CREATE (m:Medication {name: "Metformin", class: "Biguanide"})
CREATE (f:Food {name: "Rice", culture: "Singaporean", carbs_per_100g: 28})
CREATE (c:Condition {name: "Hypertension"})

// Relationships
CREATE (m)-[:TREATS]->(d)
CREATE (m)-[:INTERACTS_WITH {severity: "moderate"}]->(other_med)
CREATE (f)-[:AFFECTS {impact: "high_glucose"}]->(d)
CREATE (d)-[:COEXISTS_WITH]->(c)
```

#### Step 1.3: Create GraphRAG Agent
```python
# backend/app/agents/graphrag_agent.py
from app.core.neo4j_client import Neo4jClient

@tool("query_medical_knowledge", return_direct=False)
def query_medical_knowledge(
    user_conditions: List[str],
    user_medications: List[str],
    query_type: str  # "interactions", "recommendations", "food_advice"
) -> dict:
    """Query Neo4j for medical knowledge based on user context."""
    client = Neo4jClient()
    
    if query_type == "interactions":
        # Check for drug-drug interactions
        cypher = """
        MATCH (m1:Medication)-[r:INTERACTS_WITH]->(m2:Medication)
        WHERE m1.name IN $meds AND m2.name IN $meds
        RETURN m1.name, m2.name, r.severity, r.description
        """
        results = client.query(cypher, {"meds": user_medications})
        # Process and return interactions
    
    # Similar for other query types
```

#### Step 1.4: Integrate with Router Agent
- Add "medical_knowledge" intent to router
- Route medication/condition queries to GraphRAG agent
- Combine GraphRAG results with lifestyle analysis

**Data Sources for Neo4j**:
- DrugBank API (drug interactions)
- Singapore Health Promotion Board (food database)
- Medical literature (PubMed abstracts via LangChain document loaders)

---

### 2. **Enhanced Cultural Dietitian Agent** (High Priority)

**Current**: Stub implementation
**Goal**: Full food image analysis with Singaporean context

**Implementation**:
```python
# backend/app/agents/cultural_dietitian_agent.py

@tool("analyze_food_image", return_direct=False)
def analyze_food_image(
    image_url: str,
    patient: PatientContext
) -> dict:
    """Analyze food image using OpenAI Vision API + Singapore food database."""
    
    # 1. Use OpenAI Vision to identify food items
    vision_response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Identify all food items and estimate portions."},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }]
    )
    
    # 2. Match to Singapore food database (Neo4j or Supabase)
    # 3. Calculate carbs, calories, cultural context
    # 4. Provide diabetes-friendly alternatives
    # 5. Consider patient's ethnicity for cultural sensitivity
```

**Singapore Food Database**:
- Create `singapore_foods` table in Supabase or Neo4j
- Include: name, carbs_per_100g, calories, cultural_category, diabetes_friendly_alternatives

---

### 3. **Advanced Analytics & Insights** (Medium Priority)

#### 3.1: Predictive Analytics
- **Glucose Prediction**: Use historical patterns to predict future glucose levels
- **Hypoglycemia Risk**: ML model to predict low glucose events
- **Medication Effectiveness**: Track glucose response to medication changes

```python
# backend/app/analytics/predictive_models.py
from sklearn.ensemble import RandomForestRegressor
import pandas as pd

def predict_glucose_next_hour(
    recent_readings: List[float],
    recent_meals: List[dict],
    recent_activity: List[dict]
) -> float:
    """Predict glucose level 1 hour ahead."""
    # Feature engineering
    # Model training/prediction
    pass
```

#### 3.2: Pattern Detection
- **Circadian Patterns**: Identify time-of-day glucose patterns
- **Meal Impact**: Correlate specific foods with glucose spikes
- **Activity Optimization**: Identify best times for exercise

#### 3.3: Visualization Endpoints
```python
# backend/app/routers/analytics.py
@app.get("/analytics/glucose_trend")
async def get_glucose_trend_chart(
    user: Any = Depends(get_current_user),
    days: int = 7
):
    """Return glucose trend chart data (JSON for frontend to render)."""
    # Fetch data, process, return structured JSON
    return {
        "labels": [...],
        "datasets": [{
            "label": "Glucose (mg/dL)",
            "data": [...],
            "target_range": {"min": 80, "max": 180}
        }]
    }
```

---

### 4. **Real-time Alerts & Notifications** (Medium Priority)

**Use Cases**:
- Hypoglycemia alert (glucose < 70)
- Hyperglycemia alert (glucose > 250)
- Missed medication reminder
- Weekly summary report

**Implementation**:
```python
# backend/app/services/alert_service.py
async def check_glucose_alerts(user_id: str, reading: float):
    """Check if glucose reading triggers alerts."""
    if reading < 70:
        # Send push notification via Supabase Realtime or FCM
        await send_alert(user_id, "Low Glucose Alert", 
                        f"Your glucose is {reading} mg/dL. Consider taking action.")
```

**Frontend Integration**:
- Use Flutter local notifications
- Integrate with Supabase Realtime subscriptions
- Background task to check for alerts

---

### 5. **Multi-language Support** (Low Priority)

**Singapore Context**: Support English, Mandarin, Malay, Tamil

**Implementation**:
- Use OpenAI's multilingual capabilities
- Store translations in Supabase
- Detect user language preference from profile

---

### 6. **Healthcare Provider Dashboard** (Future)

**Features**:
- View patient summaries
- Medication adjustment recommendations
- Trend analysis across patient population
- Export reports for clinical use

**Architecture**:
- Separate admin routes in FastAPI
- Role-based access control (RBAC) in Supabase
- Flutter web dashboard (or separate React dashboard)

---

## 🏗️ Architecture Improvements

### 1. **Caching Layer**
```python
# backend/app/core/cache.py
from functools import lru_cache
import redis

# Cache patient context (TTL: 5 minutes)
@lru_cache(maxsize=100)
def get_cached_patient_context(user_id: str) -> PatientContext:
    # Fetch from Supabase, cache in Redis
    pass
```

### 2. **Rate Limiting**
```python
# backend/app/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/chat_stream")
@limiter.limit("10/minute")
async def chat_stream_endpoint(...):
    pass
```

### 3. **Error Handling & Monitoring**
- Add Sentry for error tracking
- Structured logging with correlation IDs
- Health check endpoints for all services

### 4. **Testing**
```python
# backend/tests/test_agents.py
def test_lifestyle_analyst():
    # Mock Supabase responses
    # Test glucose analysis logic
    # Assert insights are generated correctly
    pass
```

---

## 📊 Data Model Enhancements

### 2. **Create Views for Common Queries**
```sql
-- Supabase SQL
CREATE VIEW glucose_summary_7d AS
SELECT 
    user_id,
    AVG(reading) as avg_glucose,
    COUNT(*) as reading_count,
    MIN(reading) as min_glucose,
    MAX(reading) as max_glucose
FROM glucose_readings
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY user_id;
```

---

## 🔐 Security Enhancements

1. **Input Validation**: Strengthen Pydantic models with stricter validation
2. **SQL Injection Prevention**: Already handled by Supabase client, but add explicit checks
3. **Rate Limiting**: Prevent abuse (see Architecture Improvements)
4. **Audit Logging**: Log all data access for compliance

---

## 📱 Frontend Enhancements

### 1. **Offline Support**
- Cache chat history locally
- Queue data logs when offline
- Sync when connection restored


### 3. **Data Visualization**
- Charts for glucose trends (use `fl_chart` package)
- Activity heatmap
- Weight progress graph

---

## 🧪 Testing Strategy

### Backend
- Unit tests for each agent
- Integration tests for API endpoints
- Mock Supabase/Neo4j for testing

### Frontend
- Widget tests for UI components
- Integration tests for chat flow
- E2E tests with Flutter Driver

---

## 📈 Performance Optimization

1. **Database Indexing**: Ensure indexes on `user_id`, `created_at` for all tables
2. **Query Optimization**: Use Supabase query builders efficiently
3. **Streaming Optimization**: Batch SSE events if needed
4. **Frontend**: Lazy loading, image optimization

---

## 🚀 Deployment Checklist

### Backend
- [ ] Set up production environment variables
- [ ] Configure CORS for production domain
- [ ] Set up monitoring (Sentry, logs)
- [ ] Deploy to cloud (Railway, Render, or AWS)

### Frontend
- [ ] Configure production Supabase URL
- [ ] Set up app signing for iOS/Android
- [ ] Test on physical devices
- [ ] Submit to App Store/Play Store

---

## 📚 Documentation

1. **API Documentation**: Enhance FastAPI auto-generated docs
2. **Agent Documentation**: Document each agent's purpose and inputs/outputs
3. **Deployment Guide**: Step-by-step production deployment
4. **User Guide**: How to use the app features

---

## 🎓 Research Opportunities

1. **Personalized Medicine**: Use ML to personalize recommendations
2. **Behavioral Change**: Implement behavior change techniques (BCTs)
3. **Social Features**: Peer support groups (with privacy)
4. **Gamification**: Points, badges for logging consistency

---

## 🔄 Continuous Improvement

- **A/B Testing**: Test different recommendation strategies
- **User Feedback**: In-app feedback mechanism
- **Analytics**: Track feature usage (privacy-preserving)
- **Iterative Development**: Regular updates based on user needs

---

## 📞 Next Actions

1. **This Week**: 
   - Set up Neo4j instance (local or cloud)
   - Create initial knowledge graph schema
   - Implement GraphRAG agent

2. **Next Week**:
   - Enhance Cultural Dietitian agent
   - Add visualization endpoints
   - Implement basic alerts

3. **Month 1**:
   - Complete Neo4j integration
   - Add predictive analytics
   - Deploy to staging environment

4. **Month 2**:
   - User testing and feedback
   - Performance optimization
   - Production deployment

---

**Last Updated**: December 2025
**Status**: Active Development

