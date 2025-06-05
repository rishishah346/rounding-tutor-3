/**
 * AI Companion for Rounding Tutor
 * Provides a conversational interface to support student learning
 */
class AICompanionUI {
    constructor() {
        // Initialize properties
        this.isExpanded = false;
        this.isLoading = false;
        this.messageQueue = [];
        this.processingQueue = false;
        this.hasShownWelcome = false;
        this.typewriterInterval = null;
        
        // Create companion container if it doesn't exist
        this.initializeDOM();
        
        // Add event listeners
        this.initializeEventListeners();
    }
    
    /**
     * Creates or finds the AI companion DOM elements
     */
    initializeDOM() {
        // Check if container already exists
        let container = document.getElementById('ai-companion-container');
        
        if (!container) {
            // Create container
            container = document.createElement('div');
            container.id = 'ai-companion-container';
            container.className = 'ai-companion collapsed';
            
            // Create header (only shown when expanded)
            const header = document.createElement('div');
            header.id = 'ai-header';
            header.innerHTML = `
                <h3>Math Helper</h3>
                <button id="ai-toggle" aria-label="Close AI companion" title="Close">
                    <span class="toggle-icon">⊖</span>
                </button>
            `;
            
            // Create content (only shown when expanded)
            const content = document.createElement('div');
            content.id = 'ai-content';
            content.innerHTML = `
                <div id="ai-avatar" class="avatar"></div>
                <div id="ai-message">Hi! I'm Math Helper. Click to expand and get help with rounding!</div>
            `;
            
            // Assemble components
            container.appendChild(header);
            container.appendChild(content);
            
            // Add to document
            document.body.appendChild(container);
        }
        
        // Store references to DOM elements
        this.companionContainer = document.getElementById('ai-companion-container');
        this.messageElement = document.getElementById('ai-message');
        this.avatarElement = document.getElementById('ai-avatar');
        this.toggleButton = document.getElementById('ai-toggle');
    }
    
    /**
     * Set up event listeners for the AI companion
     */
    initializeEventListeners() {
        // Make entire companion clickable when collapsed
        this.companionContainer.addEventListener('click', (e) => {
            if (!this.isExpanded) {
                e.preventDefault();
                e.stopPropagation();
                this.toggleCompanion();
            }
        });
        
        // Toggle companion when close button is clicked (expanded state)
        if (this.toggleButton) {
            this.toggleButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleCompanion();
            });
        }
        
        // Request welcome message on page load (with delay)
        if (document.readyState === 'complete') {
            setTimeout(() => this.requestWelcomeMessage(), 1500);
        } else {
            window.addEventListener('load', () => {
                setTimeout(() => this.requestWelcomeMessage(), 1500);  
            });
        }
    }
    
    /**
     * Request welcome message (only once per page load)
     */
    requestWelcomeMessage() {
        if (!this.hasShownWelcome) {
            this.hasShownWelcome = true;
            this.requestMessage('welcome');
        }
    }
    
    /**
     * Toggle the expanded/collapsed state of the companion
     */
    toggleCompanion() {
        this.isExpanded = !this.isExpanded;
        
        if (this.isExpanded) {
            this.companionContainer.classList.remove('collapsed');
            this.companionContainer.classList.add('expanded');
            // Update message if it's the default
            if (this.messageElement.textContent.includes('Click to expand')) {
                this.messageElement.textContent = 'Hi! I\'m Math Helper, ready to support your decimal rounding practice.';
            }
        } else {
            this.companionContainer.classList.remove('expanded');
            this.companionContainer.classList.add('collapsed');
        }
    }
    
    /**
     * Force expand the companion (for important messages)
     */
    forceExpand() {
        if (!this.isExpanded) {
            this.toggleCompanion();
        }
    }
    
    /**
     * Request a message from the AI companion
     * @param {string} messageType - Type of message to request
     * @param {Object} context - Additional context for the message
     * @param {boolean} autoExpand - Whether to automatically expand for this message
     */
    requestMessage(messageType, context = {}, autoExpand = false) {
        // Add to queue
        this.messageQueue.push({ messageType, context, autoExpand });
        
        // Process queue if not already processing
        if (!this.processingQueue) {
            this.processMessageQueue();
        }
    }
    
    /**
     * Process messages in the queue one at a time
     */
    async processMessageQueue() {
        if (this.messageQueue.length === 0) {
            this.processingQueue = false;
            return;
        }
        
        this.processingQueue = true;
        const { messageType, context, autoExpand } = this.messageQueue.shift();
        
        // Clear any previous typewriter effect before starting new one
        if (this.typewriterInterval) {
            clearInterval(this.typewriterInterval);
            this.typewriterInterval = null;
        }
        
        // Auto-expand for important messages
        if (autoExpand || messageType === 'stage_transition' || messageType === 'struggle_support') {
            this.forceExpand();
            this.addHighlight();
        }
        
        // Show loading state
        this.setLoading(true);
        
        try {
            // Request message from server
            const response = await fetch('/api/ai/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message_type: messageType,
                    context: context
                }),
            });
            
            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}`);
            }
            
            const data = await response.json();
            this.displayMessage(data.message);
        } catch (error) {
            console.error('Error getting AI message:', error);
            this.displayMessage("I'm here to help with your rounding practice!");
        } finally {
            this.setLoading(false);
            
            // Process next message in queue after current one is fully displayed
            setTimeout(() => this.processMessageQueue(), 2000); // Increased delay
        }
    }
    
    /**
     * Add highlight effect to draw attention
     */
    addHighlight() {
        this.companionContainer.classList.add('highlight-pulse');
        setTimeout(() => {
            this.companionContainer.classList.remove('highlight-pulse');
        }, 2000);
    }
    
    /**
     * Display a message with typewriter effect
     * @param {string} message - Message to display
     */
    displayMessage(message) {
        // Clear current message
        this.messageElement.innerHTML = '';
        
        // Use typewriter effect for message
        this.typeWriterEffect(message);
        
        // Show companion briefly if it's collapsed and this is an important message
        if (!this.isExpanded) {
            this.addHighlight();
        }
    }
    
    /**
     * Create a typewriter effect for displaying messages
     * @param {string} message - Message to display with effect
     */
    typeWriterEffect(message) {
        // Clear any existing typewriter interval
        if (this.typewriterInterval) {
            clearInterval(this.typewriterInterval);
        }
        
        const words = message.split(' ');
        let wordIndex = 0;
        
        // Clear existing content
        this.messageElement.textContent = '';
        
        // Add words with a delay
        this.typewriterInterval = setInterval(() => {
            if (wordIndex >= words.length) {
                clearInterval(this.typewriterInterval);
                this.typewriterInterval = null;
                return;
            }
            
            this.messageElement.textContent += (wordIndex > 0 ? ' ' : '') + words[wordIndex];
            wordIndex++;
            
            // Auto-scroll if needed
            this.messageElement.scrollTop = this.messageElement.scrollHeight;
        }, 80);  // Adjust speed as needed
    }
    
    /**
     * Set the loading state of the companion
     * @param {boolean} isLoading - Whether the companion is loading
     */
    setLoading(isLoading) {
        this.isLoading = isLoading;
        
        if (isLoading) {
            this.avatarElement.classList.add('thinking');
            this.messageElement.innerHTML = '<span class="thinking-dots">...</span>';
        } else {
            this.avatarElement.classList.remove('thinking');
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Create a global instance
    window.aiCompanion = new AICompanionUI();
});