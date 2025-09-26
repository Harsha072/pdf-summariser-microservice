import React, { useState, useRef, useEffect } from 'react';
import './ChatBot.css';
import { useDocument } from '../../context/DocumentContext';
import { useNotification } from '../../context/NotificationContext';
import { 
  askQuestion as apiAskQuestion,
  analyzePaper,
  generateResearchQuestions 
} from '../../services/api';

const ChatBot = () => {
  const { document, qa, updateQa } = useDocument();
  const { showNotification } = useNotification();
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize with welcome message when document is ready
  useEffect(() => {
    if (document.status === 'ready' && messages.length === 0) {
      setMessages([
        {
          id: 1,
          type: 'bot',
          content: `Hi! I'm your AI assistant. I've analyzed your document "${document.fileName}" and I'm ready to help you understand it better. 

Try one of the suggestions below or ask me anything!`,
          timestamp: new Date(),
          showSuggestions: true
        }
      ]);
    }
  }, [document.status, document.fileName]);

  const addMessage = (type, content, isStreaming = false) => {
    const newMessage = {
      id: Date.now(),
      type,
      content,
      timestamp: new Date(),
      isStreaming
    };
    setMessages(prev => [...prev, newMessage]);
    return newMessage.id;
  };

  const updateMessage = (id, content) => {
    setMessages(prev => 
      prev.map(msg => 
        msg.id === id ? { ...msg, content, isStreaming: false } : msg
      )
    );
  };

  const handleSuggestionClick = (suggestion) => {
    if (suggestion === 'Generate Summary') {
      handleGenerateSummary();
    } else if (suggestion === 'Research Questions') {
      handleGenerateQuestions();
    } else if (suggestion === 'Explain Key Concepts') {
      handleExplainConcepts();
    } else if (suggestion === 'What is this about?') {
      setInputValue("What is this document about?");
    }
  };

  const handleExplainConcepts = async () => {
    if (!document.id || document.status !== 'ready') {
      showNotification('Please wait for document processing to complete', 'warning');
      return;
    }

    addMessage('user', '💡 Explain key concepts');
    
    setIsTyping(true);
    const typingId = addMessage('bot', 'Identifying and explaining key concepts...', true);

    try {
      const result = await apiAskQuestion(document.id, "What are the key concepts and terms in this document? Please explain them in simple terms.");
      
      setIsTyping(false);
      updateMessage(typingId, `💡 **Key Concepts Explained**\n\n${result.answer}`);

    } catch (error) {
      setIsTyping(false);
      updateMessage(typingId, `Sorry, I couldn't explain key concepts: ${error.message}`);
      showNotification('Concept explanation failed', 'error');
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;
    if (!document.id || document.status !== 'ready') {
      showNotification('Please wait for document processing to complete', 'warning');
      return;
    }

    const userMessage = inputValue.trim();
    setInputValue('');

    // Add user message
    addMessage('user', userMessage);

    // Add typing indicator
    setIsTyping(true);
    const typingId = addMessage('bot', 'Thinking...', true);

    try {
      const result = await apiAskQuestion(document.id, userMessage);
      
      setIsTyping(false);
      updateMessage(typingId, result.answer);
      
      // Update QA context for compatibility
      updateQa({ 
        question: userMessage,
        answer: result.answer,
        loading: false 
      });

    } catch (error) {
      setIsTyping(false);
      updateMessage(typingId, `Sorry, I encountered an error: ${error.message}`);
      showNotification('Failed to get answer', 'error');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleGenerateSummary = async () => {
    if (!document.id || document.status !== 'ready') {
      showNotification('Please wait for document processing to complete', 'warning');
      return;
    }

    // Add user action message
    addMessage('user', '📋 Generate document summary');
    
    // Add typing indicator
    setIsTyping(true);
    const typingId = addMessage('bot', 'Analyzing document and creating summary...', true);

    try {
      // For now, we'll use the analyze paper API to generate a summary-like response
      const analysis = await analyzePaper(document.id);
      
      let summaryContent = "📋 **Document Summary**\n\n";
      
      if (analysis.research_focus) {
        summaryContent += `**Research Focus:** ${analysis.research_focus}\n\n`;
      }
      
      if (analysis.paper_type) {
        summaryContent += `**Document Type:** ${analysis.paper_type}\n\n`;
      }
      
      if (analysis.research_question) {
        summaryContent += `**Main Research Question:** ${analysis.research_question}\n\n`;
      }
      
      if (analysis.key_findings) {
        summaryContent += `**Key Findings:**\n`;
        if (Array.isArray(analysis.key_findings)) {
          analysis.key_findings.forEach(finding => {
            summaryContent += `• ${finding}\n`;
          });
        } else {
          summaryContent += `${analysis.key_findings}\n`;
        }
        summaryContent += `\n`;
      }
      
      if (analysis.methodology) {
        summaryContent += `**Methodology:** ${analysis.methodology}\n\n`;
      }
      
      if (analysis.contributions) {
        summaryContent += `**Main Contributions:** ${analysis.contributions}`;
      }

      setIsTyping(false);
      updateMessage(typingId, summaryContent);

    } catch (error) {
      setIsTyping(false);
      updateMessage(typingId, `Sorry, I couldn't generate a summary: ${error.message}`);
      showNotification('Summary generation failed', 'error');
    }
  };

  const handleGenerateQuestions = async () => {
    if (!document.id || document.status !== 'ready') {
      showNotification('Please wait for document processing to complete', 'warning');
      return;
    }

    addMessage('user', '🤔 Generate research questions');
    
    setIsTyping(true);
    const typingId = addMessage('bot', 'Generating research questions...', true);

    try {
      const questionsData = await generateResearchQuestions(document.id);
      
      const content = `🤔 **Research Questions**\n\n${questionsData.questions}`;
      
      setIsTyping(false);
      updateMessage(typingId, content);

    } catch (error) {
      setIsTyping(false);
      updateMessage(typingId, `Sorry, I couldn't generate research questions: ${error.message}`);
      showNotification('Question generation failed', 'error');
    }
  };

  return (
    <div className="chatbot-container">
      {/* Chat Header */}
      <div className="chat-header">
        <div className="chat-title">
          <i className="fas fa-robot"></i>
          <span>AI Assistant</span>
        </div>
        <div className="chat-status">
          {document.status === 'ready' ? (
            <span className="status-ready">
              <i className="fas fa-circle"></i>
              Ready
            </span>
          ) : (
            <span className="status-processing">
              <i className="fas fa-circle"></i>
              Processing...
            </span>
          )}
        </div>
      </div>

      {/* Chat Messages */}
      <div className="chat-messages">
        {messages.length === 0 && document.status !== 'ready' && (
          <div className="welcome-placeholder">
            <i className="fas fa-robot chat-placeholder-icon"></i>
            <h3>AI Assistant</h3>
            <p>Upload a document to start chatting with your AI assistant!</p>
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id} className={`message ${message.type}`}>
            <div className="message-content">
              {message.content.split('\n').map((line, index) => (
                <div key={index}>
                  {line.startsWith('**') && line.endsWith('**') ? (
                    <strong>{line.slice(2, -2)}</strong>
                  ) : line.startsWith('• ') ? (
                    <div className="bullet-point">{line}</div>
                  ) : (
                    line
                  )}
                </div>
              ))}
            </div>
            
            {/* Suggestion Chips */}
            {message.showSuggestions && document.status === 'ready' && (
              <div className="suggestion-chips">
                <button 
                  className="suggestion-chip"
                  onClick={() => handleSuggestionClick('Generate Summary')}
                  disabled={isTyping}
                >
                  📋 Generate Summary
                </button>
                <button 
                  className="suggestion-chip"
                  onClick={() => handleSuggestionClick('Research Questions')}
                  disabled={isTyping}
                >
                  🤔 Research Questions
                </button>
                <button 
                  className="suggestion-chip"
                  onClick={() => handleSuggestionClick('Explain Key Concepts')}
                  disabled={isTyping}
                >
                  💡 Explain Key Concepts
                </button>
                <button 
                  className="suggestion-chip"
                  onClick={() => handleSuggestionClick('What is this about?')}
                  disabled={isTyping}
                >
                  ❓ What is this about?
                </button>
              </div>
            )}
            
            <div className="message-time">
              {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="typing-indicator">
            <div className="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input */}
      <div className="chat-input-container">
        <div className="chat-input-wrapper">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={document.status === 'ready' ? "Ask me anything about your document..." : "Upload a document to start chatting..."}
            disabled={document.status !== 'ready' || isTyping}
            rows="1"
            className="chat-input"
          />
          <button 
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || document.status !== 'ready' || isTyping}
            className="send-button"
          >
            <i className="fas fa-paper-plane"></i>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatBot;