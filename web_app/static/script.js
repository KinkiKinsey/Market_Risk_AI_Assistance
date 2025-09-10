// Additional JavaScript functionality for the Investment Analysis Pipeline

// Utility functions
const Utils = {
    // Format timestamp
    formatTimestamp: (timestamp) => {
        const date = new Date(timestamp);
        return date.toLocaleString();
    },
    
    // Truncate text
    truncateText: (text, maxLength = 100) => {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },
    
    // Generate random ID
    generateId: () => {
        return Math.random().toString(36).substr(2, 9);
    }
};

// Progress tracking
class ProgressTracker {
    constructor() {
        this.steps = [];
        this.currentStep = 0;
    }
    
    addStep(name, description) {
        this.steps.push({
            name,
            description,
            status: 'waiting',
            startTime: null,
            endTime: null,
            duration: null
        });
    }
    
    startStep(stepIndex) {
        if (this.steps[stepIndex]) {
            this.steps[stepIndex].status = 'running';
            this.steps[stepIndex].startTime = Date.now();
            this.currentStep = stepIndex;
        }
    }
    
    completeStep(stepIndex, success = true) {
        if (this.steps[stepIndex]) {
            this.steps[stepIndex].status = success ? 'success' : 'error';
            this.steps[stepIndex].endTime = Date.now();
            this.steps[stepIndex].duration = 
                this.steps[stepIndex].endTime - this.steps[stepIndex].startTime;
        }
    }
    
    getProgress() {
        const completed = this.steps.filter(step => 
            step.status === 'success' || step.status === 'error'
        ).length;
        return (completed / this.steps.length) * 100;
    }
    
    getCurrentStep() {
        return this.steps[this.currentStep];
    }
}

// Mermaid.js enhancement
class MermaidEnhancer {
    constructor() {
        this.charts = new Map();
        this.currentTheme = 'default';
    }
    
    initialize() {
        mermaid.initialize({
            startOnLoad: true,
            theme: this.currentTheme,
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis',
                nodeSpacing: 50,
                rankSpacing: 50
            },
            themeVariables: {
                primaryColor: '#1f77b4',
                primaryTextColor: '#333',
                primaryBorderColor: '#1f77b4',
                lineColor: '#666',
                secondaryColor: '#f8f9fa',
                tertiaryColor: '#e9ecef'
            }
        });
    }
    
    renderChart(containerId, mermaidCode, options = {}) {
        try {
            const container = document.getElementById(containerId);
            if (!container) {
                console.error(`Container ${containerId} not found`);
                return false;
            }
            
            // Clean the mermaid code
            const cleanCode = this.cleanMermaidCode(mermaidCode);
            
            // Store chart reference
            this.charts.set(containerId, {
                code: cleanCode,
                options,
                timestamp: Date.now()
            });
            
            // Render the chart
            container.innerHTML = cleanCode;
            mermaid.init(undefined, container);
            
            return true;
        } catch (error) {
            console.error('Error rendering Mermaid chart:', error);
            return false;
        }
    }
    
    cleanMermaidCode(code) {
        // Remove escaped newlines and quotes
        return code
            .replace(/\\n/g, '\n')
            .replace(/\\"/g, '"')
            .replace(/^['"]|['"]$/g, '') // Remove leading/trailing quotes
            .trim();
    }
    
    toggleTheme() {
        this.currentTheme = this.currentTheme === 'default' ? 'dark' : 'default';
        mermaid.initialize({
            startOnLoad: true,
            theme: this.currentTheme
        });
        
        // Re-render all charts with new theme
        this.charts.forEach((chart, containerId) => {
            this.renderChart(containerId, chart.code, chart.options);
        });
    }
    
    downloadChart(containerId, format = 'svg') {
        const chart = this.charts.get(containerId);
        if (!chart) return false;
        
        const svg = document.querySelector(`#${containerId} svg`);
        if (!svg) return false;
        
        if (format === 'svg') {
            this.downloadSVG(svg, 'impact-chain.svg');
        } else if (format === 'png') {
            this.downloadPNG(svg, 'impact-chain.png');
        }
        
        return true;
    }
    
    downloadSVG(svg, filename) {
        const svgData = new XMLSerializer().serializeToString(svg);
        const blob = new Blob([svgData], {type: 'image/svg+xml'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }
    
    downloadPNG(svg, filename) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        const svgData = new XMLSerializer().serializeToString(svg);
        const svgBlob = new Blob([svgData], {type: 'image/svg+xml'});
        const url = URL.createObjectURL(svgBlob);
        
        img.onload = function() {
            canvas.width = img.width * 2; // Higher resolution
            canvas.height = img.height * 2;
            ctx.scale(2, 2);
            ctx.drawImage(img, 0, 0);
            
            const pngUrl = canvas.toDataURL('image/png');
            const a = document.createElement('a');
            a.href = pngUrl;
            a.download = filename;
            a.click();
        };
        img.src = url;
    }
}

// Animation controller
class AnimationController {
    constructor() {
        this.animations = new Map();
    }
    
    addAnimation(elementId, animationType, duration = 1000) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        const animation = {
            type: animationType,
            duration,
            startTime: Date.now(),
            element
        };
        
        this.animations.set(elementId, animation);
        this.startAnimation(animation);
    }
    
    startAnimation(animation) {
        const { element, type, duration } = animation;
        
        switch (type) {
            case 'fadeIn':
                element.style.opacity = '0';
                element.style.transform = 'translateY(20px)';
                element.style.transition = `opacity ${duration}ms ease, transform ${duration}ms ease`;
                
                setTimeout(() => {
                    element.style.opacity = '1';
                    element.style.transform = 'translateY(0)';
                }, 50);
                break;
                
            case 'slideIn':
                element.style.transform = 'translateX(-100%)';
                element.style.transition = `transform ${duration}ms ease`;
                
                setTimeout(() => {
                    element.style.transform = 'translateX(0)';
                }, 50);
                break;
                
            case 'scaleIn':
                element.style.transform = 'scale(0.8)';
                element.style.opacity = '0';
                element.style.transition = `transform ${duration}ms ease, opacity ${duration}ms ease`;
                
                setTimeout(() => {
                    element.style.transform = 'scale(1)';
                    element.style.opacity = '1';
                }, 50);
                break;
        }
    }
    
    removeAnimation(elementId) {
        this.animations.delete(elementId);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Mermaid enhancer
    window.mermaidEnhancer = new MermaidEnhancer();
    window.mermaidEnhancer.initialize();
    
    // Initialize animation controller
    window.animationController = new AnimationController();
    
    // Initialize progress tracker
    window.progressTracker = new ProgressTracker();
    
    console.log('Investment Analysis Pipeline Web App initialized');
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        Utils,
        ProgressTracker,
        MermaidEnhancer,
        AnimationController
    };
}
