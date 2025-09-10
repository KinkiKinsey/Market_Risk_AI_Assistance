# Macro Analyst Agent - Developer Journey

## 🎯 **PURPOSE & OVERVIEW**

The **Macro Analyst Agent** is a sophisticated AI agent designed to process macro economic queries and provide intelligent analysis through LLM-powered insights. It serves as the bridge between user queries and comprehensive macro economic analysis, integrating with the Macro Read Agent for data processing and storing results in a user-specific database.

### **Core Functionality:**
- **Macro Query Processing**: Handles natural language questions about economic indicators, market trends, and macro factors
- **LLM Integration**: Uses DeepSeek via LLM_Call_Agent for intelligent analysis generation
- **Structured Output**: Generates FACT → EVIDENCE → RESULT format responses
- **User Database Management**: Stores analysis results and progress tracking in Redis
- **Progress Monitoring**: Real-time workflow progress tracking with step-by-step updates

### **Key Use Cases:**
1. **Economic Indicators**: "What economic indicators are available?"
2. **Stock-Macro Analysis**: "Why did PLTR go down recently, based on macro factors?"
3. **Sector Impact**: "How do inflation trends affect tech stocks?"
4. **Risk Assessment**: "What macro risks should I watch for?"
5. **Policy Impact**: "How do Fed policy changes affect the market?"

---

## 🏗️ **ARCHITECTURE & DESIGN**

### **System Architecture:**
```
┌─────────────────────────┐    ┌─────────────────────────┐    ┌─────────────────────────┐
│   Macro Analyst Agent   │    │   Macro Read Agent      │    │   Macro DB Agent        │
│         ✅              │    │         ✅              │    │         ✅              │
│                         │    │                         │    │                         │
│ • Query processing      │───►│ • Data freshness check  │───►│ • Macro data storage    │
│ • Progress tracking     │    │ • LLM analysis          │    │ • Weekly update logic   │
│ • User database mgmt    │    │ • FACT→EVIDENCE→RESULT  │    │ • Redis operations      │
│ • Command line interface│    │ • Macro data retrieval  │    │ • Data management       │
└─────────────────────────┘    └─────────────────────────┘    └─────────────────────────┘
         │                                │                                │
         │                                ▼                                ▼
         │                    ┌─────────────────────────┐    ┌─────────────────────────┐
         │                    │   LLM Call Agent        │    │        Redis DB         │
         │                    │         ✅              │    │                         │
         │                    │                         │    │ • Macro economic data   │
         │                    │ • DeepSeek integration  │    │ • LLM analysis results  │
         │                    │ • API management        │    │ • Update timing         │
         │                    │ • LLM response handling │    │ • Clean structure       │
         └────────────────────┘                         │    └─────────────────────────┘
```

### **Data Flow:**
1. **User Input**: Command-line query via `--queries` parameter
2. **Query Processing**: Pass query to Macro Read Agent
3. **Data Freshness Check**: Verify if macro data needs updating (weekly threshold)
4. **LLM Analysis**: Generate FACT → EVIDENCE → RESULT analysis
5. **Progress Tracking**: Update Redis with workflow progress
6. **Result Storage**: Store analysis in user-specific database
7. **Output**: Return structured analysis to user

---

## 📁 **FILE STRUCTURE & LOCATION**

### **Main Agent File:**
```
New_Fintegrate_AI/
├── Macro_Analyst_Agent.py                    # ✅ MAIN AGENT FILE
├── Macro_Read_Agent.py                       # ✅ CALLED BY THIS AGENT
├── Macro_DB_Agent.py                         # ✅ USED BY READ AGENT
├── Macro_Storage.py                           # ✅ USED BY DB AGENT
├── LLM_Call_Agent.py                          # ✅ LLM INTERACTIONS
├── Market_Expectation_Agent.py                # ✅ REFERENCE PATTERN
└── Fundamental_Segmentation_Agent.py          # ✅ REFERENCE PATTERN
```

### **Dependencies:**
- **Direct Import**: `Macro_Read_Agent.py`
- **LLM Integration**: `LLM_Call_Agent.py`
- **Database**: Redis (shared with Macro system)
- **Progress Tracking**: Redis hash structure for workflow steps

---

## 🔧 **KEY FUNCTIONS & METHODS**

### **1. Core Processing Methods:**

#### **`run_macro_analysis(query: str) -> Dict`**
- **Purpose**: Complete macro analysis workflow orchestrator
- **Flow**: Query processing → Progress tracking → Storage → Result return
- **Returns**: Complete analysis result with storage status

#### **`process_macro_query(query: str) -> Dict`**
- **Purpose**: Process macro query through Macro Read Agent
- **Integration**: Calls `MacroReadAgent.process_user_query()`
- **Progress Tracking**: Updates Redis with workflow steps
- **Returns**: Structured analysis result

#### **`store_macro_analysis(analysis_result: Dict) -> bool`**
- **Purpose**: Store analysis results in user database
- **Storage**: Redis with user-specific keys
- **Progress**: Updates completion status
- **Returns**: Storage success/failure status

### **2. Progress Tracking Methods:**

#### **`_update_progress(step: str, status: str, progress: int, details: str)`**
- **Purpose**: Update workflow progress in Redis
- **Structure**: Hash-based progress tracking (same as other agents)
- **Keys**: `macro_analyst:step_name` format
- **Expiry**: 24-hour TTL for progress data

### **3. Database Management Methods:**

#### **`get_user_macro_analysis() -> Dict`**
- **Purpose**: Retrieve current analysis for user
- **Keys**: `macro_result:user_id` and `macro_frontend_progress:user_id`
- **Returns**: Current analysis and progress data

---

## 📊 **DATA STRUCTURE & DATABASE SCHEMA**

### **Redis Database Structure:**

#### **1. Macro Result Storage:**
```bash
# Key Format: macro_result:{user_id}
# Example: macro_result:investor_001

{
    "success": true,
    "user_id": "investor_001",
    "query": "Why did PLTR go down recently, based on macro factors?",
    "analysis": "**OPPORTUNITY**\n• **FACT:** GDP growth remains positive...",
    "timestamp": "2024-01-15T10:30:00",
    "agent_type": "Macro_Analyst_Agent",
    "data_source": "Macro_Read_Agent",
    "output_format": "FACT → EVIDENCE → RESULT",
    "metadata": {
        "query_length": 58,
        "response_length": 245,
        "processing_time": "2024-01-15T10:30:00"
    }
}
```

#### **2. Frontend Progress Tracking:**
```bash
# Key Format: macro_frontend_progress:{user_id}
# Example: macro_frontend_progress:investor_001

# Redis Hash Structure (same as other agents):
{
    "macro_analyst:starting analysis": {
        "user_id": "investor_001",
        "step": "starting analysis",
        "status": "started",
        "progress": 10,
        "details": "Initializing macro analysis for query: Why did PLTR go down...",
        "timestamp": "2024-01-15T10:30:00",
        "agent": "macro_analyst"
    },
    "macro_analyst:preprocessing query": {
        "user_id": "investor_001",
        "step": "preprocessing query",
        "status": "started",
        "progress": 20,
        "details": "Preparing query for Macro Read Agent",
        "timestamp": "2024-01-15T10:30:05",
        "agent": "macro_analyst"
    },
    "macro_analyst:calling macro read agent": {
        "user_id": "investor_001",
        "step": "calling macro read agent",
        "status": "started",
        "progress": 30,
        "details": "Connecting to Macro Read Agent",
        "timestamp": "2024-01-15T10:30:10",
        "agent": "macro_analyst"
    },
    "macro_analyst:processing response": {
        "user_id": "investor_001",
        "step": "processing response",
        "status": "started",
        "progress": 60,
        "details": "Processing LLM analysis response",
        "timestamp": "2024-01-15T10:30:15",
        "agent": "macro_analyst"
    },
    "macro_analyst:generating final result": {
        "user_id": "investor_001",
        "step": "generating final result",
        "status": "started",
        "progress": 80,
        "details": "Creating structured analysis result",
        "timestamp": "2024-01-15T10:30:20",
        "agent": "macro_analyst"
    },
    "macro_analyst:storing analysis": {
        "user_id": "investor_001",
        "step": "storing analysis",
        "status": "started",
        "progress": 90,
        "details": "Storing macro analysis results",
        "timestamp": "2024-01-15T10:30:25",
        "agent": "macro_analyst"
    },
    "macro_analyst:analysis complete": {
        "user_id": "investor_001",
        "step": "analysis complete",
        "status": "completed",
        "progress": 100,
        "details": "Macro analysis completed successfully",
        "timestamp": "2024-01-15T10:30:30",
        "agent": "macro_analyst"
    }
}
```

### **Database Key Naming Convention:**

#### **Results Storage:**
```bash
# Format: macro_result:{user_id}
macro_result:investor_001
macro_result:analyst_002
macro_result:default_user
```

#### **Progress Tracking:**
```bash
# Format: macro_frontend_progress:{user_id}
macro_frontend_progress:investor_001
macro_frontend_progress:analyst_002
macro_frontend_progress:default_user
```

### **Data Persistence & Expiry:**

#### **Results Data:**
- **TTL**: 30 days (2,592,000 seconds)
- **Purpose**: Long-term storage of analysis results
- **Cleanup**: Automatic Redis expiry

#### **Progress Data:**
- **TTL**: 24 hours (86,400 seconds)
- **Purpose**: Short-term workflow tracking
- **Cleanup**: Automatic Redis expiry

---

## 🚀 **USAGE & INTEGRATION**

### **1. Command Line Usage:**

#### **Basic Query:**
```bash
python3 Macro_Analyst_Agent.py --queries "What economic indicators are available?"
```

#### **With Custom User ID:**
```bash
python3 Macro_Analyst_Agent.py --queries "Why did PLTR go down recently?" --user-id "investor_001"
```

#### **Short Form:**
```bash
python3 Macro_Analyst_Agent.py -q "How do inflation trends affect tech stocks?" -u "analyst_002"
```

### **2. Programmatic Integration:**

#### **Direct Import:**
```python
from Macro_Analyst_Agent import MacroAnalystAgent

# Initialize agent
agent = MacroAnalystAgent(user_id="investor_001")

# Process query
result = agent.run_macro_analysis("What macro risks should I watch for?")

# Check result
if result.get('success'):
    print(f"Analysis: {result['analysis']}")
    print(f"Stored: {result.get('stored')}")
```

#### **Progress Monitoring:**
```python
# Get current analysis
current_analysis = agent.get_user_macro_analysis()

# Check progress
progress = current_analysis.get('progress', {})
for step, data in progress.items():
    if step.startswith('macro_analyst:'):
        step_data = json.loads(data)
        print(f"Step: {step_data['step']}, Status: {step_data['status']}, Progress: {step_data['progress']}%")
```

### **3. Workflow Integration:**

#### **Complete Analysis Pipeline:**
```python
# 1. Initialize agent
agent = MacroAnalystAgent(user_id="system_user")

# 2. Process macro query
result = agent.run_macro_analysis("How do interest rate changes affect the tech sector?")

# 3. Verify storage
if result.get('stored'):
    print("✅ Analysis stored successfully")
    print(f"Result key: {agent.macro_result_key}")
    print(f"Progress key: {agent.macro_frontend_progress_key}")
```

---

## 🔄 **WORKFLOW & PROGRESS TRACKING**

### **Progress Steps & Percentages:**

#### **1. Starting Analysis (10%)**
- **Status**: "started"
- **Details**: "Initializing macro analysis for query: [query]..."
- **Action**: Agent initialization and query preparation

#### **2. Preprocessing Query (20%)**
- **Status**: "started"
- **Details**: "Preparing query for Macro Read Agent"
- **Action**: Query validation and formatting

#### **3. Calling Macro Read Agent (30%)**
- **Status**: "started" → "completed"
- **Details**: "Connecting to Macro Read Agent"
- **Action**: Integration with Macro Read Agent

#### **4. Processing Response (60%)**
- **Status**: "started"
- **Details**: "Processing LLM analysis response"
- **Action**: LLM response processing and validation

#### **5. Generating Final Result (80%)**
- **Status**: "started"
- **Details**: "Creating structured analysis result"
- **Action**: Result formatting and metadata creation

#### **6. Storing Analysis (90%)**
- **Status**: "started"
- **Details**: "Storing macro analysis results"
- **Action**: Database storage operations

#### **7. Analysis Complete (100%)**
- **Status**: "completed"
- **Details**: "Macro analysis completed successfully"
- **Action**: Final status update and cleanup

### **Progress Update Logic:**

#### **Hash Structure Management:**
```python
def _update_progress(self, step: str, status: str, progress: int, details: str):
    # Get existing progress data
    existing_data = self.redis_client.hgetall(progress_key)
    
    # Keep existing data from other agents
    for key, value in existing_data.items():
        if not key.startswith('macro_analyst:'):
            updated_data[key] = value
    
    # Add/update Macro Analyst Agent data
    macro_key = f"macro_analyst:{step}"
    updated_data[macro_key] = json.dumps(progress_data)
    
    # Store all data back to Redis
    self.redis_client.hset(progress_key, mapping=updated_data)
```

---

## 🗄️ **DATABASE OPERATIONS**

### **Redis Connection Configuration:**

#### **Connection Parameters:**
```python
self.redis_config = {
    "host": "redis-16204.fcrce180.us-east-1-1.ec2.redns.redis-cloud.com",
    "port": 16204,
    "username": "default",
    "password": "9rHiMKl63iYK9ja4qja6ZjnamuixS4UG"
}
```

#### **Connection Method:**
```python
def _connect_redis(self):
    """Connect to Redis user database"""
    try:
        self.redis_client = redis.Redis(
            host=self.redis_config["host"],
            port=self.redis_config["port"],
            username=self.redis_config["username"],
            password=self.redis_config["password"],
            decode_responses=True
        )
        self.redis_client.ping()
        print(f"✅ Redis connected: {self.redis_config['host']}:{self.redis_config['port']}")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        self.redis_client = None
```

### **Data Storage Operations:**

#### **Result Storage:**
```python
# Store macro result
result_key = self.macro_result_key
result_data = json.dumps(analysis_result, default=str)
self.redis_client.set(result_key, result_data)
self.redis_client.expire(result_key, 30 * 24 * 60 * 60)  # 30 days
```

#### **Progress Storage:**
```python
# Store progress updates
progress_key = self.macro_frontend_progress_key
self.redis_client.hset(progress_key, mapping=updated_data)
self.redis_client.expire(progress_key, 86400)  # 24 hours
```

### **Data Retrieval Operations:**

#### **Get Current Analysis:**
```python
def get_user_macro_analysis(self) -> Dict[str, Any]:
    # Get current analysis
    result_data = self.redis_client.get(self.macro_result_key)
    if not result_data:
        return {'error': 'No current analysis found'}
    
    current_analysis = json.loads(result_data)
    
    # Get progress data
    progress_data = self.redis_client.get(self.macro_frontend_progress_key)
    progress = json.loads(progress_data) if progress_data else {}
    
    return {
        'current_analysis': current_analysis,
        'progress': progress,
        'retrieved_at': datetime.now().isoformat()
    }
```

---

## 🔍 **ERROR HANDLING & LOGGING**

### **Error Handling Strategy:**

#### **1. Redis Connection Errors:**
```python
try:
    self.redis_client.ping()
    print(f"✅ Redis connected: {self.redis_config['host']}:{self.redis_config['port']}")
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
    self.redis_client = None
```

#### **2. Query Processing Errors:**
```python
try:
    analysis_response = self.macro_read_agent.process_user_query(query)
    if not analysis_response:
        return {
            'success': False,
            'error': 'No response from Macro Read Agent',
            'timestamp': timestamp,
            'query': query
        }
except Exception as e:
    error_msg = f"Error processing macro query: {str(e)}"
    logging.error(error_msg)
    return {
        'success': False,
        'error': error_msg,
        'timestamp': datetime.now().isoformat(),
        'query': query
    }
```

#### **3. Storage Errors:**
```python
try:
    # Storage operations
    result1 = self.redis_client.set(result_key, result_data)
    result2 = self.redis_client.hset(progress_key, mapping=updated_data)
    
    if result1 and result2:
        print(f"✅ Macro analysis stored successfully")
        return True
    else:
        print(f"⚠️ Storage operation failed")
        return False
        
except Exception as e:
    print(f"❌ Failed to store macro analysis: {e}")
    logging.error(f"Store macro analysis error: {e}")
    return False
```

### **Logging Configuration:**

#### **Log Setup:**
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('macro_analyst_agent.log')
    ]
)
```

#### **Log File:**
- **Filename**: `macro_analyst_agent.log`
- **Location**: Same directory as agent file
- **Format**: Timestamp - Level - Message
- **Rotation**: Manual (new file created on each run)

---

## 🧪 **TESTING & DEBUGGING**

### **1. Unit Testing:**

#### **Test Import:**
```bash
python3 -c "from Macro_Analyst_Agent import MacroAnalystAgent; print('✅ Import successful!')"
```

#### **Test Compilation:**
```bash
python3 -m py_compile Macro_Analyst_Agent.py
```

### **2. Integration Testing:**

#### **Test Basic Query:**
```bash
python3 Macro_Analyst_Agent.py --queries "What economic indicators are available?"
```

#### **Test Custom User:**
```bash
python3 Macro_Analyst_Agent.py --queries "Why did PLTR go down?" --user-id "test_user_001"
```

### **3. Database Verification:**

#### **Check Redis Keys:**
```bash
# Connect to Redis
redis-cli -h redis-16204.fcrce180.us-east-1-1.ec2.redns.redis-cloud.com -p 16204 -u default -a 9rHiMKl63iYK9ja4qja6ZjnamuixS4UG

# Check keys
KEYS macro_result:*
KEYS macro_frontend_progress:*

# Check specific user data
GET macro_result:test_user_001
HGETALL macro_frontend_progress:test_user_001
```

#### **Verify Data Structure:**
```bash
# Check result structure
redis-cli GET macro_result:test_user_001 | python3 -m json.tool

# Check progress structure
redis-cli HGETALL macro_frontend_progress:test_user_001
```

### **4. Debug Commands:**

#### **Check Agent Status:**
```python
from Macro_Analyst_Agent import MacroAnalystAgent

agent = MacroAnalystAgent(user_id="debug_user")
print(f"User ID: {agent.user_id}")
print(f"Result Key: {agent.macro_result_key}")
print(f"Progress Key: {agent.macro_frontend_progress_key}")
print(f"Redis Connected: {agent.redis_client is not None}")
```

---

## 🔧 **CONFIGURATION & CUSTOMIZATION**

### **Environment Variables:**

#### **Redis Configuration:**
```python
# Can be customized via environment variables
import os

redis_host = os.getenv('REDIS_HOST', 'redis-16204.fcrce180.us-east-1-1.ec2.redns.redis-cloud.com')
redis_port = int(os.getenv('REDIS_PORT', 16204))
redis_username = os.getenv('REDIS_USERNAME', 'default')
redis_password = os.getenv('REDIS_PASSWORD', '9rHiMKl63iYK9ja4qja6ZjnamuixS4UG')
```

#### **Agent Configuration:**
```python
# Default user ID
default_user_id = os.getenv('DEFAULT_USER_ID', 'default_user')

# Progress TTL
progress_ttl = int(os.getenv('PROGRESS_TTL', 86400))  # 24 hours

# Result TTL
result_ttl = int(os.getenv('RESULT_TTL', 30 * 24 * 60 * 60))  # 30 days
```

### **Customization Options:**

#### **1. Progress Steps:**
```python
# Customize progress steps
PROGRESS_STEPS = [
    ("starting analysis", 10),
    ("preprocessing query", 20),
    ("calling macro read agent", 30),
    ("processing response", 60),
    ("generating final result", 80),
    ("storing analysis", 90),
    ("analysis complete", 100)
]
```

#### **2. Output Format:**
```python
# Customize analysis output format
OUTPUT_FORMATS = {
    "default": "FACT → EVIDENCE → RESULT",
    "simple": "Opportunity & Risk",
    "detailed": "FACT → EVIDENCE → RESULT → IMPACT"
}
```

---

## 🚀 **DEPLOYMENT & SCALABILITY**

### **Deployment Requirements:**

#### **1. System Requirements:**
- **Python**: 3.8+
- **Redis**: 6.0+
- **Memory**: 512MB+ RAM
- **Storage**: 100MB+ disk space

#### **2. Dependencies:**
```bash
pip install redis
pip install openai  # For LLM integration
```

#### **3. Network Access:**
- **Redis**: Port 16204 (or custom)
- **LLM API**: HTTPS access to DeepSeek API
- **Internet**: For external API calls

### **Scalability Considerations:**

#### **1. User Management:**
- **Single Instance**: Handles multiple users via Redis key separation
- **User Isolation**: Each user gets separate database keys
- **Concurrent Access**: Redis handles concurrent user requests

#### **2. Performance Optimization:**
- **Connection Pooling**: Redis connection reuse
- **TTL Management**: Automatic cleanup of old data
- **Progress Caching**: Hash-based progress storage

#### **3. Monitoring:**
- **Log Files**: `macro_analyst_agent.log`
- **Redis Metrics**: Key count, memory usage, TTL status
- **Progress Tracking**: Real-time workflow monitoring

---

## 🔮 **FUTURE ENHANCEMENTS**

### **Planned Features:**

#### **1. Advanced Progress Tracking:**
- **WebSocket Integration**: Real-time frontend updates
- **Progress History**: Historical workflow tracking
- **Performance Metrics**: Response time analysis

#### **2. Enhanced Analysis:**
- **Multi-Query Support**: Batch processing capabilities
- **Analysis Templates**: Predefined analysis patterns
- **Custom Output Formats**: Configurable response structures

#### **3. Integration Features:**
- **Manager Agent**: Multi-agent orchestration
- **API Endpoints**: REST API for web integration
- **Event Streaming**: Real-time analysis updates

### **Architecture Evolution:**

#### **Current State:**
```
User Query → Macro_Analyst_Agent → Macro_Read_Agent → LLM → Storage
```

#### **Future State:**
```
User Query → Manager_Agent → Macro_Analyst_Agent → Macro_Read_Agent → LLM → Storage
         ↓
    Progress Updates → WebSocket → Frontend
         ↓
    Event Stream → Analytics → Monitoring
```

---

## 📚 **REFERENCE & RESOURCES**

### **Related Documentation:**
- **Market_Expectation_DEVELOPER_JOURNEY.md**: Reference architecture pattern
- **Fundamental_Segmentation_DEVELOPER_JOURNEY.md**: Integration examples
- **Macro_Read_Agent.py**: Core analysis integration
- **LLM_Call_Agent.py**: LLM interaction patterns

### **Code Examples:**
- **Basic Usage**: See "Usage & Integration" section
- **Progress Tracking**: See "Workflow & Progress Tracking" section
- **Database Operations**: See "Database Operations" section

### **Troubleshooting:**
- **Common Issues**: See "Error Handling & Logging" section
- **Testing**: See "Testing & Debugging" section
- **Configuration**: See "Configuration & Customization" section

---

## 🎯 **SUMMARY**

The **Macro Analyst Agent** provides a robust, scalable solution for macro economic analysis with:

- **🎯 Command-line Interface**: Simple `--queries` parameter usage
- **🧠 LLM Integration**: DeepSeek-powered intelligent analysis
- **📊 Structured Output**: FACT → EVIDENCE → RESULT format
- **🗄️ User Database**: Redis-based storage with progress tracking
- **🔄 Progress Monitoring**: Real-time workflow step tracking
- **🔧 Extensible Architecture**: Easy integration and customization

**Perfect for developers building macro analysis systems, financial applications, or economic research tools!** 🚀
