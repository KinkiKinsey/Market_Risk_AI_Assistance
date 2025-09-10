import streamlit as st
import streamlit.components.v1 as components
import time
import sys
import os

# Add parent directory to path to import our agents
# Try multiple possible paths for different deployment scenarios
possible_paths = [
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # Local development
    os.path.dirname(os.path.abspath(__file__)),  # Streamlit Cloud root
    '/mount/src/new_fintegrate_ai',  # Streamlit Cloud specific
    '/mount/src/New_Fintegrate_AI',  # Alternative Streamlit Cloud path
]

# Debug: Print current paths for troubleshooting
print(f"🔍 Current working directory: {os.getcwd()}")
print(f"🔍 Current file location: {os.path.abspath(__file__)}")
print(f"🔍 Python path before: {sys.path}")

for path in possible_paths:
    print(f"🔍 Checking path: {path}")
    if os.path.exists(path):
        print(f"✅ Path exists: {path}")
        if os.path.exists(os.path.join(path, 'News_Verification.py')):
            print(f"✅ Found News_Verification.py in: {path}")
            sys.path.append(path)
            break
        else:
            print(f"❌ News_Verification.py not found in: {path}")
    else:
        print(f"❌ Path does not exist: {path}")
else:
    # Fallback: add current directory and parent
    print("⚠️ Using fallback paths")
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print(f"🔍 Python path after: {sys.path}")

from News_Verification import verify_statement_with_user
from Manager_Agent import ManagerAgent
from Chain_of_Thought_Agent import ChainOfThoughtAgent

# Page config
st.set_page_config(
    page_title="Fintegrate AI - Financial Analysis Pipeline",
    page_icon="🚀",
    layout="wide"
)

# Custom CSS for high-tech, flat design with purple theme and white text
st.markdown("""
<style>
    .main {
        padding: 0;
    }
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
        color: white !important;
    }
    
    /* Global white text */
    .stMarkdown, .stText, .stWrite, .stJson, .stCode, .stExpander, .stSpinner, .stSuccess, .stError, .stWarning, .stInfo {
        color: white !important;
    }
    
    /* All text elements white */
    p, h1, h2, h3, h4, h5, h6, div, span, label, strong, em, b, i, li, ul, ol, blockquote, pre, code {
        color: white !important;
    }
    
    /* Streamlit specific elements */
    .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
        color: white !important;
    }
    
    .stTextInput > div > div > input {
        color: white !important;
        background: rgba(255, 255, 255, 0.1) !important;
        border: 2px solid rgba(255, 255, 255, 0.3) !important;
    }
    
    .stTextArea > div > div > textarea {
        color: white !important;
        background: rgba(255, 255, 255, 0.1) !important;
        border: 2px solid rgba(255, 255, 255, 0.3) !important;
    }
    
    .stTextInput > div > div > input::placeholder {
        color: rgba(255, 255, 255, 0.7) !important;
    }
    
    .stTextArea > div > div > textarea::placeholder {
        color: rgba(255, 255, 255, 0.7) !important;
    }
    
    /* Header styling */
    .main-header {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 20px;
        padding: 30px;
        margin: 20px 0;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    }
    
    .main-header h1 {
        color: white !important;
        font-size: 3.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        letter-spacing: 2px;
    }
    
    .main-header .subtitle {
        color: white !important;
        font-size: 1.2rem;
        margin-top: 10px;
        font-weight: 300;
    }
    
    /* Input section styling */
    .input-section {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 20px;
        padding: 30px;
        margin: 20px 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        color: white !important;
    }
    
    .input-section .stTextInput, .input-section .stTextArea {
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 12px;
        transition: all 0.3s ease;
        background: rgba(255, 255, 255, 0.1) !important;
    }
    
    .input-section .stTextInput:focus, .input-section .stTextArea:focus {
        border-color: white;
        box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.2);
    }
    
    /* User input text color - BLACK for better readability */
    .input-section .stTextInput > div > div > input {
        color: #000000 !important;
        font-weight: 500;
        background: rgba(255, 255, 255, 0.9) !important;
    }
    
    .input-section .stTextArea > div > div > textarea {
        color: #000000 !important;
        font-weight: 500;
        background: rgba(255, 255, 255, 0.9) !important;
    }
    
    .input-section .stTextInput::placeholder, .input-section .stTextArea::placeholder {
        color: rgba(0, 0, 0, 0.6) !important;
    }
    
    /* Force black text in all input elements */
    .stTextInput input, .stTextArea textarea {
        color: #000000 !important;
        background: rgba(255, 255, 255, 0.9) !important;
    }
    
    /* Override Streamlit's default white text */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        color: #000000 !important;
        background: rgba(255, 255, 255, 0.9) !important;
    }
    
    /* Nuclear option - force black text everywhere */
    .stTextInput *,
    .stTextArea * {
        color: #000000 !important;
    }
    
    /* Specific input field overrides */
    input[type="text"], textarea {
        color: #000000 !important;
        background: rgba(255, 255, 255, 0.9) !important;
    }
    
    /* Character count styling */
    .stCaption {
        color: rgba(255, 255, 255, 0.8) !important;
        font-size: 0.9em !important;
        font-style: italic !important;
    }
    
    /* Error message styling */
    .stAlert {
        background: rgba(255, 0, 0, 0.1) !important;
        border: 1px solid rgba(255, 0, 0, 0.3) !important;
        border-radius: 8px !important;
    }
    
    /* Pipeline cards */
    .pipeline-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 20px;
        padding: 25px;
        margin: 20px 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        color: white !important;
    }
    
    .pipeline-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
    }
    
    .agent-title {
        font-size: 28px;
        font-weight: 700;
        color: white !important;
        margin-bottom: 20px;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Decision panels */
    .decision-panel {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border: none;
        border-radius: 15px;
        padding: 20px;
        margin: 20px 0;
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 16px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-align: center;
        min-width: 100px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: white !important;
    }
    
    .status-success {
        background: linear-gradient(135deg, #4caf50, #45a049);
        color: white !important;
        box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
    }
    
    .status-warning {
        background: linear-gradient(135deg, #ff9800, #f57c00);
        color: white !important;
        box-shadow: 0 4px 15px rgba(255, 152, 0, 0.3);
    }
    
    .status-error {
        background: linear-gradient(135deg, #f44336, #d32f2f);
        color: white !important;
        box-shadow: 0 4px 15px rgba(244, 67, 54, 0.3);
    }
    
    /* Loading bars */
    .loading-bar {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 15px;
        height: 8px;
        overflow: hidden;
        margin: 15px 0;
    }
    
    .loading-fill {
        background: linear-gradient(90deg, #667eea, #764ba2);
        height: 100%;
        transition: width 0.3s ease;
        border-radius: 15px;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 12px;
        color: white !important;
        font-weight: 600;
    }
    
    /* Success, Error, Warning, Info messages */
    .stSuccess, .stError, .stWarning, .stInfo {
        color: white !important;
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 12px !important;
        padding: 15px !important;
    }
    
    /* JSON and code blocks */
    .stJson, .stCode {
        background: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 12px !important;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea, #764ba2);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #5a6fd8, #6a4190);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'pipeline_complete' not in st.session_state:
    st.session_state.pipeline_complete = False
if 'noise_decision' not in st.session_state:
    st.session_state.noise_decision = None
if 'agent_results' not in st.session_state:
    st.session_state.agent_results = None
if 'chain_result' not in st.session_state:
    st.session_state.chain_result = None
if 'current_step' not in st.session_state:
    st.session_state.current_step = "ready"

# Main app
def main():
    # Custom header with Fintegrate AI branding
    st.markdown("""
    <div class="main-header">
        <h1>🚀 Fintegrate AI</h1>
        <div class="subtitle">Advanced Financial Analysis Pipeline</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Input Section
    with st.container():
        st.markdown('<div class="input-section">', unsafe_allow_html=True)
        
        # Note about empty inputs
        st.info("💡 **Enter your analysis parameters below** - All fields start empty for fresh analysis")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            user_id = st.text_input("👤 User ID", value="", key="user_id")
        
        with col2:
            ticker = st.text_input("📈 Stock Ticker", value="", key="ticker")
        
        with col3:
            if st.button("🔄 Restart Pipeline", type="primary"):
                st.session_state.pipeline_complete = False
                st.session_state.noise_decision = None
                st.session_state.agent_results = None
                st.session_state.chain_result = None
                st.session_state.current_step = "ready"
                st.rerun()
        
        # Big Chat Box
        user_question = st.text_area(
            "💬 Investment Question (400 Characters Max)",
            value="",
            height=120,
            max_chars=400,
            key="user_question",
            help="Enter your investment question. Maximum 400 characters allowed."
        )
        
        # Character count display
        if user_question:
            char_count = len(user_question)
            remaining = 400 - char_count
            if remaining >= 0:
                st.caption(f"📝 Characters: {char_count}/400 ({remaining} remaining)")
            else:
                st.error(f"⚠️ Character limit exceeded! You have {char_count}/400 characters. Please shorten your question.")
        
        # Analysis Button
        if st.button("🚀 Start Analysis Pipeline", type="primary", use_container_width=True):
            # Check character limit before running pipeline
            if len(user_question) > 400:
                st.error("❌ Cannot start analysis: Question exceeds 400 character limit. Please shorten your question.")
                return
            
            if not user_question.strip():
                st.error("❌ Cannot start analysis: Please enter an investment question.")
                return
                
            import asyncio
            asyncio.run(run_pipeline(user_id, ticker, user_question))
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Display Results
    if st.session_state.pipeline_complete:
        display_results()

async def run_pipeline(user_id, ticker, user_question):
    """Run the complete analysis pipeline"""
    
    # Step 1: Noise Filter AI
    st.markdown('<div class="pipeline-card">', unsafe_allow_html=True)
    st.markdown('<div class="agent-title">🔍 Noise Filter AI</div>', unsafe_allow_html=True)
    st.session_state.current_step = "noise_filter"
    
    with st.spinner("Analyzing investment noise..."):
        try:
            # Use the function-based approach for News_Verification
            noise_result = await verify_statement_with_user(
                statement=user_question,
                user_id=user_id,
                use_video=False
            )
            st.session_state.noise_decision = noise_result
            st.success("✅ Noise Filter AI completed successfully!")
        except Exception as e:
            st.error(f"❌ Error in Noise Filter AI: {str(e)}")
            return
    
            # Display Noise Filter Results
        display_noise_filter_results(noise_result)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Check if investment noise
        if noise_result.final_decision == 'Not Noise for Investment':
            st.success("✅ Investment Signal Detected - Proceeding to Impaction AI")
            
            # Step 2: Impaction AI (Manager Agent)
            st.markdown('<div class="pipeline-card">', unsafe_allow_html=True)
            st.markdown('<div class="agent-title">🎯 Impaction AI</div>', unsafe_allow_html=True)
            st.session_state.current_step = "impaction_ai"
            
            with st.spinner("Analyzing market impact..."):
                try:
                    # Call the static function directly
                    from Manager_Agent import analyze_with_multiprocessing
                    manager_result = await analyze_with_multiprocessing(
                        user_query=user_question,
                        ticker=ticker,
                        user_id=user_id
                    )
                    st.session_state.agent_results = manager_result
                    st.success("✅ Impaction AI completed successfully!")
                except Exception as e:
                    st.error(f"❌ Error in Impaction AI: {str(e)}")
                    return
            
            # Display Impaction AI Results
            display_impaction_results(manager_result)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Step 3: Chain of Thought AI
            st.markdown('<div class="pipeline-card">', unsafe_allow_html=True)
            st.markdown('<div class="agent-title">🔗 Chain of Thought AI</div>', unsafe_allow_html=True)
            st.session_state.current_step = "chain_of_thought"
            
            with st.spinner("Generating impact chain..."):
                try:
                    chain_agent = ChainOfThoughtAgent()
                    chain_result = chain_agent.generate_impact_chain(
                        ticker=ticker,
                        user_question=user_question,
                        verification_links=noise_result.reference_links or [],
                        verification_reasoning=noise_result.final_reasoning or '',
                        agent_analysis_results=manager_result
                    )
                    st.session_state.chain_result = chain_result
                    st.success("✅ Chain of Thought AI completed successfully!")
                except Exception as e:
                    st.error(f"❌ Error in Chain of Thought AI: {str(e)}")
                    return
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.session_state.pipeline_complete = True
            st.session_state.current_step = "complete"
            st.success("🎉 Pipeline Complete!")
        else:
            st.warning("⚠️ Investment Noise Detected - Analysis Stopped")
            st.session_state.current_step = "noise_detected"

def display_noise_filter_results(noise_result):
    """Display Noise Filter AI results"""
    with st.container():
        # Decision Panel
        decision = noise_result.final_decision or 'Unknown'
        if decision == 'Not Noise for Investment':
            st.markdown('<div class="decision-panel">', unsafe_allow_html=True)
            st.success(f"✅ Decision: {decision}")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.error(f"❌ Decision: {decision}")
        
        # Expandable Results
        with st.expander("📊 View Verification Analysis Results", expanded=False):
            # Convert VerificationResult to dict for display
            result_dict = {
                "statement": noise_result.statement,
                "final_decision": noise_result.final_decision,
                "final_reasoning": noise_result.final_reasoning,
                "reference_links": noise_result.reference_links,
                "filters": [
                    {
                        "name": f.name,
                        "status": f.status.value,
                        "details": f.details
                    } for f in noise_result.filters
                ]
            }
            st.json(result_dict)

def display_impaction_results(manager_result):
    """Display Impaction AI results"""
    with st.container():
        # Agent Results
        if 'agent_results' in manager_result:
            for agent_name, result in manager_result['agent_results'].items():
                st.markdown(f"**{agent_name}:**")
                with st.expander(f"📊 View {agent_name} Results", expanded=False):
                    st.write(result)
                st.markdown("---")
        else:
            st.info("No agent results found in the response")

def display_chain_results(chain_result):
    """Display Chain of Thought AI results with Mermaid.js"""
    with st.container():
        # Display chain info
        st.write(f"**Ticker:** {chain_result.ticker}")
        st.write(f"**Impact Chain:** {chain_result.impact_chain}")
        st.write(f"**Final Direction:** {chain_result.final_direction}")
        st.write(f"**Explanation:** {chain_result.chain_explanation}")
        
        # Generate Mermaid.js code
        try:
            from Chain_of_Thought_Agent import generate_mermaid_code
            mermaid_code = generate_mermaid_code(
                node_count=chain_result.node_count,
                edge_count=chain_result.edge_count,
                events=chain_result.events
            )
            
            # Clean the Mermaid.js code (remove \n and quotes)
            clean_mermaid = mermaid_code.replace('\\n', '\n').strip("'")
            
            # Display Mermaid.js chart
            st.markdown("### 📊 Impact Chain Visualization")
            components.html(f"""
            <div class="mermaid">
            {clean_mermaid}
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
            <script>
            mermaid.initialize({{startOnLoad: true}});
            </script>
            """, height=500)
            
            # Show raw Mermaid.js code
            with st.expander("📝 View Raw Mermaid.js Code", expanded=False):
                st.code(clean_mermaid, language="mermaid")
                
        except Exception as e:
            st.error(f"❌ Error generating Mermaid.js chart: {str(e)}")
            st.info("Displaying raw chain data instead")
            st.json({
                "node_count": chain_result.node_count,
                "edge_count": chain_result.edge_count,
                "events": chain_result.events
            })

def display_results():
    """Display all pipeline results"""
    if st.session_state.chain_result:
        display_chain_results(st.session_state.chain_result)

if __name__ == "__main__":
    main()
