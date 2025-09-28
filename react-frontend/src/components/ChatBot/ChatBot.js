import React, { useState, useRef, useEffect } from 'react';
import './ChatBot.css';
import { useDocument } from '../../context/DocumentContext';
import { useNotification } from '../../context/NotificationContext';
import { 
  askQuestion as apiAskQuestion,
  analyzePaper,
  generateResearchQuestions,
  askWithQuotes
} from '../../services/api';

const ChatBot = () => {
  const { document, qa, updateQa } = useDocument();
  const { showNotification } = useNotification();
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const messageCounterRef = useRef(0); // Counter to ensure unique IDs

  // Fixed scrollToBottom function (removed useEffect from inside)
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize with welcome message when document is ready
  useEffect(() => {
    if (document.status === 'ready' && messages.length === 0) {
      messageCounterRef.current += 1;
      setMessages([
        {
          id: Date.now() + messageCounterRef.current,
          type: 'bot',
          content: `Hi! I'm your AI assistant. I've analyzed your document "${document.fileName}" and I'm ready to help you understand it better. 

Try one of the suggestions below or ask me anything!`,
          timestamp: new Date(),
          showSuggestions: true
        }
      ]);
    }
  }, [document.status, document.fileName, messages.length]); // Added messages.length to dependencies

  // Fixed addMessage function (removed duplicate return)
  const addMessage = (type, content, isStreaming = false) => {
    messageCounterRef.current += 1;
    const newMessage = {
      id: Date.now() + messageCounterRef.current,
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

  // Detect if user is asking for exact location/mention
  const detectExactMentionQuery = (question) => {
    const mentionPatterns = [
      /where\s+(?:does|do|is|are).*mention/i,
      /which\s+(?:line|paragraph|section|page).*mention/i,
      /what\s+(?:line|paragraph|section|page).*mention/i,
      /find.*mention.*of/i,
      /locate.*mention/i,
      /where.*(?:discuss|talk|reference)/i,
      /which\s+(?:paragraph|section).*(?:about|discuss)/i,
      /find.*reference.*to/i,
      /show\s+me\s+where/i,
      /highlight.*where/i
    ];
    
    return mentionPatterns.some(pattern => pattern.test(question));
  };

  // Extract search term from question
  const extractSearchTerm = (question) => {
    // Try different patterns to extract the search term
    const patterns = [
      /mention[s]?\s+["']([^"']+)["']/i,
      /mention[s]?\s+([a-zA-Z\s]{2,20})(?:\s|$|\?)/i,
      /about\s+["']([^"']+)["']/i,
      /about\s+([a-zA-Z\s]{2,20})(?:\s|$|\?)/i,
      /reference[s]?\s+to\s+["']([^"']+)["']/i,
      /reference[s]?\s+to\s+([a-zA-Z\s]{2,20})(?:\s|$|\?)/i,
      /discuss[es]?\s+["']([^"']+)["']/i,
      /discuss[es]?\s+([a-zA-Z\s]{2,20})(?:\s|$|\?)/i,
      /where\s+is\s+["']([^"']+)["']/i,
      /where\s+is\s+([a-zA-Z\s]{2,20})(?:\s|$|\?)/i
    ];
    
    for (const pattern of patterns) {
      const match = question.match(pattern);
      if (match) {
        return match[1].trim();
      }
    }
    
    // Fallback: extract quoted terms
    const quotedMatch = question.match(/["']([^"']{2,30})["']/);
    if (quotedMatch) {
      return quotedMatch[1].trim();
    }
    
    return null;
  };

  // Navigate to exact location with highlighting
  const navigateToExactLocation = (location) => {
    console.log('Navigating to exact location:', location);
    
    // Extract highlighting information from the new structure
    const searchTerms = location.found_terms || [];
    const mainSearchTerm = searchTerms.length > 0 ? searchTerms[0] : '';
    
    window.dispatchEvent(new CustomEvent('highlightInPDF', {
      detail: {
        page: location.page,
        section: location.section,
        paragraphId: location.paragraph_id,
        contentType: location.content_type,
        searchTerms: searchTerms,
        searchTerm: mainSearchTerm,
        fullText: location.full_text,
        highlightInfo: location.highlight_info,
        bbox: location.bbox,
        startChar: location.start_char,
        endChar: location.end_char
      }
    }));
    
    // Add confirmation message with more details
    const confirmMessageId = addMessage('bot', `📍 Highlighting "${mainSearchTerm}" on page ${location.page} in section "${location.section}"\n🔍 Looking for terms: ${searchTerms.join(', ')}`);
    
    // Mark as navigation message
    setMessages(prev => prev.map(msg => 
      msg.id === confirmMessageId ? { ...msg, isNavigation: true } : msg
    ));
  };

  // Utility function to escape regex special characters
  const escapeRegex = (string) => {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  };

  // Format answer with supporting quotes - much simpler than exact mention formatting
  const formatAnswerWithQuotes = (result) => {
    const { answer, supporting_quotes, confidence } = result;
    
    if (!supporting_quotes || supporting_quotes.length === 0) {
      return answer + "\n\n💡 *I couldn't find specific supporting quotes for this answer.*";
    }

    return answer;
  };

  // Navigate to quote location with highlighting
  const navigateToQuote = (quote) => {
    console.log('Navigating to quote:', quote);

    // Extract a good search term from the quote text
    const quoteText = quote.text || '';
    const searchTerm = quoteText.length > 50 ? 
                      quoteText.substring(0, 50).trim() : 
                      quoteText.trim();

    window.dispatchEvent(new CustomEvent('highlightInPDF', {
      detail: {
        page: quote.page,
        section: quote.section,
        searchTerm: searchTerm, // Primary search term
        searchTerms: [searchTerm], // Backup array format
        highlightText: quoteText, // Full quote text
        bbox: quote.bbox,
        exactMatch: true
      }
    }));
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

    // Use Smart Quote Finder for ALL questions
    setIsTyping(true);
    const typingId = addMessage('bot', 'Analyzing document and finding supporting quotes...', true);

    try {
      const result = await askWithQuotes(document.id, userMessage);
      console.log('Smart Quote Finder result:', result);
      
      setIsTyping(false);
      
      // Create the answer with quotes
      const answerWithQuotes = formatAnswerWithQuotes(result);
      const messageId = updateMessage(typingId, answerWithQuotes);
      
      // Add quote data to message for highlighting
      setMessages(prev => prev.map(msg => 
        msg.id === typingId ? {
          ...msg,
          hasQuotes: true,
          quotesData: result.supporting_quotes || [],
          confidence: result.confidence || 0,
          question: userMessage
        } : msg
      ));
      
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
              {message.hasQuotes && message.quotesData?.length > 0 ? (
                <div className="smart-quote-response">
                  <div className="answer-text">
                    {message.content.split('\n').map((line, idx) => (
                      <div key={idx} className="answer-line">
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
                  
                  <div className="quote-section">
                    <h4>📍 Supporting Quotes (Confidence: {message.confidence}%)</h4>
                    {message.quotesData.slice(0, 3).map((quote, idx) => (
                      <div 
                        key={`quote-${message.id}-${idx}`}
                        className="quote-card"
                        data-confidence={
                          quote.confidence >= 75 ? 'high' : 
                          quote.confidence >= 50 ? 'medium' : 'low'
                        }
                        onClick={() => navigateToQuote(quote)}
                      >
                        <div className="quote-text">"{quote.text}"</div>
                        <div className="quote-source">
                          📄 Page {quote.page} • {quote.section} • {quote.confidence}% match
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="message-text">
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
              )}
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
                  className="suggestion-chip exact-search"
                  onClick={() => setInputValue("Where does the author mention")}
                  disabled={isTyping}
                >
                  🔍 Find Exact Mention
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
            placeholder={document.status === 'ready' ? "Ask me anything or try: 'Where does the author mention machine learning?'" : "Upload a document to start chatting..."}
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