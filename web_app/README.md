# 🚀 Investment Analysis Pipeline Web App

A clean, flat web application that runs your complete investment analysis pipeline using Streamlit.

## 🏗️ Architecture

The web app follows this pipeline:

1. **🔍 Noise Filter AI** - Analyzes investment noise using News Verification
2. **🎯 Impaction AI** - Routes to sub-agents using Manager Agent
3. **🔗 Chain of Thought AI** - Generates impact chains with Mermaid.js visualization

## 📁 File Structure

```
web_app/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── static/            # Static assets (CSS, JS, images)
├── templates/         # HTML templates (if needed)
└── assets/            # Additional assets
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd web_app
pip install -r requirements.txt
```

### 2. Run the Web App
```bash
streamlit run app.py
```

### 3. Open Browser
Navigate to `http://localhost:8501`

## 🎯 Features

- **Clean, Flat Design** - Minimal, essential interface
- **User Input** - User ID, Stock Ticker, Investment Question
- **Pipeline Restart** - Reset with existing input parameters
- **Real-time Progress** - Loading bars and status updates
- **Expandable Results** - Click buttons to view detailed outputs
- **Mermaid.js Charts** - Beautiful chain of thought visualizations
- **Error Handling** - Graceful error handling with user feedback

## 🔧 Configuration

### Environment Variables
Make sure your API keys are set in your environment:
- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEY`
- `TAVILY_API_KEY`

### Redis Configuration
The app uses Redis for progress tracking and data storage. Ensure your Redis connection is properly configured in your agent files.

## 📊 Usage

1. **Enter Details**: Fill in User ID, Stock Ticker, and Investment Question
2. **Start Pipeline**: Click "Start Analysis Pipeline"
3. **Monitor Progress**: Watch each AI agent complete their analysis
4. **View Results**: Expand sections to see detailed results
5. **Visualize Chain**: See the impact chain as a beautiful Mermaid.js graph
6. **Restart**: Use "Restart Pipeline" to run with new parameters

## 🎨 Customization

### Styling
Modify the CSS in `app.py` to change colors, fonts, and layout.

### Pipeline Steps
Add or modify pipeline steps in the `run_pipeline()` function.

### Agent Integration
Ensure your agent classes have the expected methods:
- `NewsVerificationAgent.verify_statement()`
- `ManagerAgent.analyze_with_multiprocessing()`
- `ChainOfThoughtAgent.generate_impact_chain()`

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all agent files are in the parent directory
2. **API Key Errors**: Check environment variables are set correctly
3. **Redis Connection**: Verify Redis server is running and accessible
4. **Mermaid.js Rendering**: Check browser console for JavaScript errors

### Debug Mode
Add `st.write()` statements to debug specific sections of the pipeline.

## 🔄 Updates

- **Pipeline Status**: Real-time updates on current step
- **Error Recovery**: Graceful handling of agent failures
- **Session Management**: Persistent state across page refreshes

## 📱 Responsive Design

The app is designed to work on:
- Desktop browsers
- Tablet devices
- Mobile phones (with some layout adjustments)

## 🚀 Performance Tips

1. **Agent Caching**: Results are cached in session state
2. **Lazy Loading**: Results are only generated when needed
3. **Progress Tracking**: Real-time updates without blocking UI

## 🤝 Contributing

To add new features:
1. Modify `app.py` for UI changes
2. Update `requirements.txt` for new dependencies
3. Test with different input scenarios
4. Update this README with new features

## 📄 License

This project is part of your Fintegrate AI system.
