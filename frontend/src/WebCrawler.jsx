/**
 * WebCrawler Component
 * 
 * A React application that allows users to search web content through an API.
 * Features include chat management, URL customization, and response viewing.
 */
import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './WebCrawler.css';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import { BiRefresh } from "react-icons/bi"; // Import refresh icon

const WebCrawler = () => {
  // API configuration
  const apiUrl = import.meta.env.VITE_API_ENDPOINT;
  const apiPORT = import.meta.env.VITE_API_PORT;

  // State for user input and URL management
  const [prompt, setPrompt] = useState('');
  const [enableUrl, setEnableUrl] = useState(false);
  const [showUrlPopup, setShowUrlPopup] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [urls, setUrls] = useState([]);

  // References for DOM manipulation
  const chatAreaRef = useRef(null);
  const promptInputRef = useRef(null);

  // State for chat management
  const [chats, setChats] = useState([
    { id: 1, title: 'New Chat', messages: [] }
  ]);
  const [activeChat, setActiveChat] = useState(1);
  const [renamingChatId, setRenamingChatId] = useState(null);
  const [newChatTitle, setNewChatTitle] = useState('');
  const [_, setApiResponse] = useState(null); // Stores the API response

  // State for UI management
  const [messageTabStates, setMessageTabStates] = useState({});
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Updates the active tab for a specific message
   * @param {string} messageId - The ID of the message
   * @param {string} tabName - The name of the tab to activate
   */
  const handleTabChange = (messageId, tabName) => {
    setMessageTabStates(prevState => ({
      ...prevState,
      [messageId]: tabName
    }));
  };
  
  /**
   * Creates a new chat with an auto-generated title
   */
  const createNewChat = () => {
    // If no chats exist, create the first chat titled "New Chat"
    // Otherwise, generate a new chat with an incremented number
    const newChatId = chats.length > 0 ? Math.max(...chats.map(chat => chat.id)) + 1 : 1;
    
    let chatTitle = "New Chat";
    
    // Add a number to differentiate new chats
    if (chats.length > 0) {
      chatTitle = `New Chat ${newChatId - 1}`;
    }
    
    const newChat = {
      id: newChatId,
      title: chatTitle,
      messages: []
    };
    
    setChats([...chats, newChat]);
    setActiveChat(newChatId);
    setUrls([]);
  };

  /**
   * Switches to a different chat
   * @param {number} chatId - The ID of the chat to switch to
   */
  const switchChat = (chatId) => {
    setActiveChat(chatId);
    setUrls([]);
  };

  /**
   * Initiates the chat renaming process
   * @param {number} chatId - The ID of the chat to rename
   * @param {string} currentTitle - The current title of the chat
   */
  const startRenaming = (chatId, currentTitle) => {
    setRenamingChatId(chatId);
    setNewChatTitle(currentTitle);
  };

  /**
   * Completes the chat renaming process
   */
  const finishRenaming = () => {
    if (newChatTitle.trim()) {
      const updatedChats = chats.map(chat => 
        chat.id === renamingChatId ? { ...chat, title: newChatTitle } : chat
      );
      setChats(updatedChats);
    }
    setRenamingChatId(null);
    setNewChatTitle('');
  };

  /**
   * Deletes a chat and handles active chat selection
   * @param {number} chatId - The ID of the chat to delete
   */
  const deleteChat = (chatId) => {
    const updatedChats = chats.filter(chat => chat.id !== chatId);
    setChats(updatedChats);

    // Select a new active chat if the deleted chat was active
    if (activeChat === chatId && updatedChats.length > 0) {
      setActiveChat(updatedChats[0].id);
    } else if (activeChat === chatId) {
      // Set activeChat to null when all chats are deleted
      setActiveChat(null);
    }
  };

  // Auto-scroll to bottom of chat when messages change
  useEffect(() => {
    if (chatAreaRef.current) {
      chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight;
    }
  }, [chats, activeChat]);

  // Initialise textarea height and event handlers
  useEffect(() => {
    // Set initial height of textarea and handle cleanup
    if (promptInputRef.current) {
      promptInputRef.current.style.height = 'auto';
      promptInputRef.current.style.height = `${promptInputRef.current.scrollHeight}px`;
      
      // Add focus event handler to ensure we can navigate to start with arrow keys
      const handleFocus = () => {
        if (promptInputRef.current) {
          promptInputRef.current.style.overflowX = 'auto';
        }
      };
      
      const handleBlur = () => {
        if (promptInputRef.current && 
            promptInputRef.current.scrollWidth <= promptInputRef.current.clientWidth) {
          promptInputRef.current.style.overflowX = 'hidden';
        }
      };
      
      promptInputRef.current.addEventListener('focus', handleFocus);
      promptInputRef.current.addEventListener('blur', handleBlur);
      
      // Clean up event listeners on component unmount
      return () => {
        if (promptInputRef.current) {
          promptInputRef.current.removeEventListener('focus', handleFocus);
          promptInputRef.current.removeEventListener('blur', handleBlur);
        }
      };
    }
  }, []);

  /**
   * Handles text input changes and auto-resizes the textarea
   * @param {Event} e - The input change event
   */
  const handlePromptChange = (e) => {
    setPrompt(e.target.value);
    
    // Auto-resize textarea based on content
    if (promptInputRef.current) {
      promptInputRef.current.style.height = 'auto';
      promptInputRef.current.style.height = `${promptInputRef.current.scrollHeight}px`;
      
      // Enable horizontal scrolling if content is wider than the container
      if (promptInputRef.current.scrollWidth > promptInputRef.current.clientWidth) {
        promptInputRef.current.style.overflowX = 'auto';
      } else {
        promptInputRef.current.style.overflowX = 'hidden';
      }
    }
  };

  /**
   * Toggles the URL mode on/off
   * @param {Event} e - The click event
   */
  const handleEnableUrlToggle = (e) => {
    // Prevent event propagation and default behavior
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    
    const newEnableUrlState = !enableUrl;
    setEnableUrl(newEnableUrlState);

    // Close URL popup when URL mode is disabled
    if (!newEnableUrlState) {
      setShowUrlPopup(false);
    }
  };
  
  /**
   * Updates the URL input field
   * @param {Event} e - The input change event
   */
  const handleUrlInputChange = (e) => {
    setUrlInput(e.target.value);
  };

  /**
   * Adds a URL to the list with proper formatting
   */
  const addUrlWithPrefix = () => {
    if (urlInput) {
      // Ensure URL has proper protocol prefix
      let formattedUrl = urlInput;
      if (!formattedUrl.startsWith('http://') && !formattedUrl.startsWith('https://')) {
        formattedUrl = 'https://' + formattedUrl;
      }

       // Validate and add URL if not already in the list
      if (isValidUrl(formattedUrl)) {
        if (!urls.includes(formattedUrl)) {
          setUrls([...urls, formattedUrl]);
          setUrlInput('');
        } else {
          alert('This URL has already been added.');
        }
      } else {
        alert('Please enter a valid URL with a proper domain (e.g., example.com)');
      }
    }
  };

  /**
   * Removes a URL from the list
   * @param {number} index - The index of the URL to remove
   */
  const removeUrl = (index) => {
    const newUrls = [...urls];
    newUrls.splice(index, 1);
    setUrls(newUrls);
  };

  /**
   * Validates if a string is a properly formatted URL
   * @param {string} string - The URL string to validate
   * @returns {boolean} - Whether the URL is valid
   */
  const isValidUrl = (string) => {
    try {
      const url = new URL(string);

      // Check for valid protocol
      if (url.protocol !== 'http:' && url.protocol !== 'https:') {
        return false;
      }

      // Check for valid domain
      if (!url.hostname.includes('.')) {
        return false;
      }

      // Reject IP addresses without paths
      if (/^(\d{1,3}\.){3}\d{1,3}$/.test(url.hostname) && !url.pathname.length > 1) {
        return false;
      }
      return true;
    } catch (_) {
      return false;
    }
  };

  /**
   * Checks if the prompt has actual content
   * @param {string} text - The text to check
   * @returns {boolean} - Whether the text has content
   */
  const isValidPrompt = (text) => {
    // Check if the text is empty after trimming whitespace and newlines
    return text.trim().length > 0;
  };

  /**
   * Handles query submission
   */
  const handleSubmit = async () => {
    if (prompt && isValidPrompt(prompt)) {
      try {
        // Always proceed with regular submission (using cache when available)
        await submitQuery(prompt, false);
      } catch (error) {
        console.error('Error processing request:', error);
      }
    }
  };

  /**
   * Converts a decimal string to percentage format
   * @param {string} decimalStr - Decimal value as string
   * @param {number} decimalPlaces - Number of decimal places
   * @returns {string} - Percentage value
   */
  function safeStringToPercentage(decimalStr, decimalPlaces = 0) {
    const num = parseFloat(decimalStr);
    
    if (isNaN(num)) {
      return "0%"; // Default value for invalid input
    }
    
    return `${(num * 100).toFixed(decimalPlaces)}%`;
  }

  /**
   * Formats duration values with appropriate units
   * @param {string} durationStr - Duration value as string
   * @returns {string} - Formatted duration
   */
  function formatDuration(durationStr) {
    // Handle null, undefined, or empty string
    if (!durationStr) return "N/A";
    
    // Parse the string to a number
    const duration = parseFloat(durationStr);
    
    // Check if it's a valid number
    if (isNaN(duration)) return "N/A";
    
    // If duration is below 0 seconds, convert to milliseconds
    if (duration < 0) {
      const milliseconds = duration * 1000;
      return `${milliseconds.toFixed(0)} milliseconds`;
    }
    
    // Otherwise, format to exactly 2 decimal places and add "seconds"
    return `${duration.toFixed(2)} seconds`;
  }

  /**
   * Submits a query to the API and handles the response
   * @param {string} userPrompt - The user's input query
   * @param {boolean} forceCrawl - Whether to force a new crawl
   */
  const submitQuery = async (userPrompt, forceCrawl) => {
    // Set loading state to true before API call
    setIsLoading(true);

    // Prepare request data
    try {
      let data = {
        user_prompt: userPrompt,
        urls: [],
        num_seed_urls: 5,
        force_crawl: forceCrawl,
        use_llm_response: true
      };

       // Add custom URLs if enabled
      if (enableUrl && urls.length > 0) {
        data.urls = urls;
      }
      
      // Add prompt to chat
      const updatedChats = [...chats];
      const chatIndex = updatedChats.findIndex(chat => chat.id === activeChat);
      
      if (chatIndex !== -1) {
        updatedChats[chatIndex].messages.push({ 
          text: userPrompt, 
          type: 'prompt' 
        });
        setChats(updatedChats);
      }
      
      // Show loading indicator
      const loadingMessage = {
        text: 'Fetching response...',
        type: 'response',
        isLoading: true
      };
      
      const updatedChatsWithLoading = [...chats];
      const chatIndexForLoading = updatedChatsWithLoading.findIndex(chat => chat.id === activeChat);
      
      if (chatIndexForLoading !== -1) {
        updatedChatsWithLoading[chatIndexForLoading].messages.push(loadingMessage);
        setChats(updatedChatsWithLoading);
      }
      
      // Send API request
      const response = await axios.post(apiUrl+apiPORT+'/api/crawl', data);
      setApiResponse(response.data);
      console.log(response.data)

       // Handle error response
      if (response.data.status === "error") {
        // Format metadata and evaluation metrics
        const errorPart = response.data.error || "Unknown error";
        let metadataPart = "\nMetadata:\n";
        if (response.data.metadata) {
          for (let [key, value] of Object.entries(response.data.metadata)) {
            metadataPart += `  ${key}: ${value}\n`;
          }
        }
        
        // Format evaluation metrics (handling nested structure)
        let metricsPart = "Evaluation Metrics:\n";
        if (response.data.evaluation_metrics) {
          for (let [key, value] of Object.entries(response.data.evaluation_metrics)) {
            if (typeof value === 'object' && value !== null) {
              metricsPart += `  ${key}:\n`;
              for (let [subKey, subValue] of Object.entries(value)) {
                metricsPart += `    ${subKey}: ${subValue}\n`;
              }
            } else {
              metricsPart += `  ${key}: ${value}\n`;
            }
          }
        }
        
        // Combine with appropriate formatting and separation
        const errorMessage = `${errorPart}\n${metadataPart}\n${metricsPart}`;
        
        // Create an error response object
        const errorResponse = {
          id: Date.now().toString(),
          text: errorMessage,
          type: 'error',
          isError: true,
          fullResponse: response.data // Store full response for reference
        };
        
        // Update the chat with the error message
        const finalChats = [...chats];
        const chatIndex = finalChats.findIndex(chat => chat.id === activeChat);
        
        if (chatIndex !== -1) {
          // Replace the loading message with the error message
          finalChats[chatIndex].messages = [
            ...finalChats[chatIndex].messages.filter(msg => !msg.isLoading),
            errorResponse
          ];
          setChats(finalChats);
        }
      }// Handle partial success response
      else if (response.data.status === "partial_success") {
        // Extract error messages if present (could be a string or array)
        let errorContent = "";
        if (response.data.error) {
          const errorText = Array.isArray(response.data.error) 
            ? response.data.error.join("\n") 
            : response.data.error;
          errorContent = `Error(s) occurred during processing:\n${errorText}`;
        }
        
        // Check for LLM error in metadata
        const hasLlmError = response.data.metadata && response.data.metadata.llm_error;
        
        // Format metadata section
        let metadataPart = "\nMetadata:\n";
        if (response.data.metadata) {
          for (let [key, value] of Object.entries(response.data.metadata)) {
            if (typeof value === 'object' && value !== null) {
              metadataPart += ` ${key}:\n`;
              for (let [subKey, subValue] of Object.entries(value)) {
                metadataPart += `   ${subKey}: ${subValue}\n`;
              }
            } else {
              metadataPart += ` ${key}: ${value}\n`;
            }
          }
        }
        
        // Format evaluation metrics section
        let metricsPart = "\nEvaluation Metrics:\n";
        if (response.data.evaluation_metrics) {
          for (let [key, value] of Object.entries(response.data.evaluation_metrics)) {
            if (typeof value === 'object' && value !== null) {
              metricsPart += ` ${key}:\n`;
              for (let [subKey, subValue] of Object.entries(value)) {
                metricsPart += `   ${subKey}: ${subValue}\n`;
              }
            } else {
              metricsPart += ` ${key}: ${value}\n`;
            }
          }
        }
        
        // Combine all error information for display
        const fullErrorInfo = `${errorContent}${metadataPart}${metricsPart}`;
        
        // Format LLM content - use error message if appropriate
        let llmResponseContent = response.data.llm_response;
        if (hasLlmError && response.data.llm_response === "N/A") {
          llmResponseContent = `Error in LLM Response Generation: ${response.data.metadata.llm_error}`;
        }
        
        // Create a response message with appropriate flags
        const responseMessage = {
          id: Date.now().toString(),
          text: llmResponseContent, // Show LLM response or error in main content
          type: 'response',
          isPartialSuccess: true,
          hasErrors: !!errorContent,
          hasLlmError: hasLlmError,
          errorContent: fullErrorInfo, // Store full error info for display in UI
          fullResponse: response.data
        };
        
        // Update the chat
        const finalChats = [...chats];
        const chatIndex = finalChats.findIndex(chat => chat.id === activeChat);
        
        if (chatIndex !== -1) {
          // Replace loading message with partial success response
          finalChats[chatIndex].messages = [
            ...finalChats[chatIndex].messages.filter(msg => !msg.isLoading),
            responseMessage
          ];
          setChats(finalChats);
        }// Handle successful response
      } else {
        // Process normal response (existing code)
        const responseMessage = {
          id: Date.now().toString(),
          text: response.data.llm_response,
          type: 'response',
          fullResponse: response.data
        };

        // Update the chat
        const finalChats = [...chats];
        const chatIndex = finalChats.findIndex(chat => chat.id === activeChat);
        
        if (chatIndex !== -1) {
          // Replace the loading message with the actual response
          finalChats[chatIndex].messages = [
            ...finalChats[chatIndex].messages.filter(msg => !msg.isLoading),
            responseMessage
          ];
          setChats(finalChats);
        }
      }
      
      // Removed setSavedPrompt(null) call
      setPrompt('');
    } catch (error) {
      console.error('Error fetching response:', error);
      // Determine type of error
      let errorMessage = "An unexpected error occurred";
      
      if (error.response) {
        // The server responded with an error status code (4xx, 5xx)
        errorMessage = `Server error: ${error.response.status} - ${error.response.statusText || 'Unknown error'}`;
      } else if (error.request) {
        // The request was made but no response was received
        errorMessage = "Network error: Unable to connect to server. This could be due to your internet connection or the server is currently unavailable. Please check your connection or try again later.";
      } else {
        // Something happened in setting up the request
        errorMessage = `Request error: ${error.message}`;
      }
      
      // Add error message to chat
      const errorResponse = {
        id: Date.now().toString(),
        text: errorMessage,
        type: 'error',
        isError: true
      };
      
      const finalChats = [...chats];
      const chatIndex = finalChats.findIndex(chat => chat.id === activeChat);
      
      if (chatIndex !== -1) {
        // Replace loading message with error message
        finalChats[chatIndex].messages = [
          ...finalChats[chatIndex].messages.filter(msg => !msg.isLoading),
          errorResponse
        ];
        setChats(finalChats);
      }
    } finally {
      // Set loading state back to false after API call completes (success or error)
      setIsLoading(false);
    }
  };  
  
  // Get current active chat
  const currentChat = chats.find(chat => chat.id === activeChat) || { messages: [] };

  /**
   * Handles Enter key press for form elements
   * @param {Event} e - The keypress event
   * @param {Function} action - The function to execute on Enter
   */
  const handleKeyPress = (e, action) => {
    if (e.key === 'Enter') {
      action();
    }
  };

  /**
   * Renders a metric with its justification
   * @param {string} label - The metric label
   * @param {Object} metric - The metric data
   */
  const MetricWithJustification = ({ label, metric }) => {
    if (!metric) return <>{label}: N/A</>;
    
    return (
      <>
        {label}: {metric.score ? safeStringToPercentage(metric.score, 0) : "N/A"}
        {metric.justification && (
          <div className="justification"><br></br>Justification: {metric.justification}</div>
        )}
      </>
    );
  };  

  /**
   * Renders a comprehensive message in the chat interface
   * @param {Object} message - The message data object
   * @param {string} activeTab - Currently selected tab for this message
   * @param {Function} onTabChange - Callback function to handle tab changes
   */
  const Message = ({ message, activeTab, onTabChange }) => {
    // Determine if we should show tabs based on message type and availability of full response
    const showTabs = message.type === 'response' && message.fullResponse;

    // Special handling for loading state messages
    if (message.isLoading) {
      return (
        <div className={`message ${message.type}`}>
          <div className="loading-message-container">
            <div className="loading-spinner"></div>
            <span>{message.text}</span>
          </div>
        </div>
      );
    }

    return (
      <div className={`message ${message.type}`}>
        {/* Display the sender label */}
        <div className="message-type">{message.type === 'prompt' ? 'You' : 'DAWC'}</div>
        
        {showTabs ? (
          <>
            {/* Tab navigation for response messages with full data */}
            <div className="tab-navigation">
              <button 
                className={`tab-button ${activeTab === 'llm_response' ? 'active' : ''}`}
                onClick={() => onTabChange(message.id, 'llm_response')}
              >
                LLM Response
              </button>
              <button 
                className={`tab-button ${activeTab === 'contents' ? 'active' : ''}`}
                onClick={() => onTabChange(message.id, 'contents')}
              >
                Raw Response
              </button>
              <button 
                className={`tab-button ${activeTab === 'metrics' ? 'active' : ''}`}
                onClick={() => onTabChange(message.id, 'metrics')}
              >
                Metrics
              </button>
            </div>
            
            {/* LLM Response tab content */}
            {activeTab === 'llm_response' && (
              <div className="llm-response">
                {/* Handle error state */}
                {message.fullResponse.status === "error" ? (
                  // Display error message when status is "error"
                  <div className="error-message">
                    <h3>Error Occurred</h3>
                    {/* Display metadata for debugging if available */}
                    <pre>{message.fullResponse.error}</pre>
                    {message.fullResponse.metadata && (
                      <>
                        <h4>Metadata:</h4>
                        <pre>{JSON.stringify(message.fullResponse.metadata, null, 2)}</pre>
                      </>
                    )}
                    {/* Display evaluation metrics if available */}
                    {message.fullResponse.evaluation_metrics && (
                      <>
                        <h4>Evaluation Metrics:</h4>
                        <pre>{JSON.stringify(message.fullResponse.evaluation_metrics, null, 2)}</pre>
                      </>
                    )}
                  </div>
                ) : message.fullResponse.status === "partial_success" && message.fullResponse.metadata?.llm_error ? (
                  /* Handle partial success with LLM error */
                  <div className="error-message">
                    <h3>LLM Generation Error</h3>
                    <pre>{message.fullResponse.metadata.llm_error}</pre>
                    {message.fullResponse.error && (
                      <>
                        <h4>Additional Errors:</h4>
                        {/* Show additional errors if present */}
                        <pre>{Array.isArray(message.fullResponse.error) 
                          ? message.fullResponse.error.join('\n') 
                          : message.fullResponse.error}</pre>
                      </>
                    )}
                  </div>
                ) : message.fullResponse.llm_response === "N/A" ? (
                  /* Handle when LLM response is N/A but status isn't error */
                  <div className="warning-message">
                    <p>No LLM response was generated. This could be due to insufficient data or an error in the generation process.</p>
                    {/* Display available error information */}
                    {message.fullResponse.error && (
                      <>
                        <h4>Errors:</h4>
                        <pre>{Array.isArray(message.fullResponse.error) 
                          ? message.fullResponse.error.join('\n') 
                          : message.fullResponse.error}</pre>
                      </>
                    )}
                  </div>
                ) : (
                  /* Render successful LLM response with markdown formatting */
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    components={{
                      /* Custom code block renderer for syntax highlighting */
                      code({node, inline, className, children, ...props}) {
                        // Extract language from className if it exists
                        const match = /language-(\w+)/.exec(className || '');
                        return !inline && match ? (
                           // Use SyntaxHighlighter for code blocks
                          <SyntaxHighlighter
                            style={oneDark}
                            language={match[1]}
                            PreTag="div"
                            showLineNumbers={true}
                            {...props}
                          >
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        ) : (
                          // Use regular code tag for inline code
                          <code className={className} {...props}>
                            {children}
                          </code>
                        );
                      }
                    }}
                  >
                    {message.fullResponse.llm_response}
                  </ReactMarkdown>
                )}
              </div>
            )}

            {/* Raw Response (Contents) tab */}
            {activeTab === 'contents' && (
              <div className="contents-tab">
                {/* Display JSON results if available, or fallback message */}
                {message.fullResponse.results && message.fullResponse.results.length > 0 ? (
                  <pre className="json-content" style={{ 
                    backgroundColor: "#282828", 
                    padding: "1rem", 
                    borderRadius: "0.25rem", 
                    overflowX: "auto",
                    color: "#e0e0e0",
                    fontFamily: "monospace",
                    fontSize: "0.875rem",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word"
                  }}>
                    {JSON.stringify(message.fullResponse.results, null, 2)}
                  </pre>
                ) : (
                  <div className="no-content">No search results available</div>
                )}
              </div>
            )}

            {/* Metrics tab for displaying performance data */}
            {activeTab === 'metrics' && (
              <div className="metrics-tab">
                {/* Time metrics section */}
                <div className="metrics-section">
                  <h3>Time Metrics</h3>
                  <p>Response Latency: {
                    message.fullResponse.evaluation_metrics?.time_metrics?.duration_seconds 
                      ? formatDuration(message.fullResponse.evaluation_metrics.time_metrics.duration_seconds) 
                      : "N/A"
                  }</p>
                </div>

                {/* Harvest metrics section - displays data about page relevance and quantity */}
                <div className="metrics-section">
                  <h3>Harvest Metrics</h3>
                  <p>Relevant Pages: {message.fullResponse.evaluation_metrics?.harvest_metrics?.overall?.relevant_pages || "N/A"}</p>
                  <p>Total Pages: {message.fullResponse.evaluation_metrics?.harvest_metrics?.overall?.total_pages || "N/A"}</p>
                  <p>Harvest Ratio: {
                    message.fullResponse.evaluation_metrics?.harvest_metrics?.overall?.harvest_ratio 
                      ? safeStringToPercentage(
                          message.fullResponse.evaluation_metrics.harvest_metrics.overall.harvest_ratio,
                          0
                        ) 
                      : "N/A"
                  }</p>
                </div>
                
                {/* AI scoring metrics - only displayed when available */}
                {message.fullResponse.evaluation_metrics?.generative_ai_scoring_metrics && (
                  <div className="metrics-section">
                    <h3>AI Scoring Metrics</h3>
                    
                    {/* Raw results evaluation subsection */}
                    <h4>Raw Results Evaluation</h4>
                    <MetricWithJustification 
                      label="Relevance" 
                      metric={message.fullResponse.evaluation_metrics.generative_ai_scoring_metrics.raw_results_evaluation?.relevance} 
                    />
                    <MetricWithJustification 
                      label="Completeness" 
                      metric={message.fullResponse.evaluation_metrics.generative_ai_scoring_metrics.raw_results_evaluation?.information_completeness} 
                    />
                    <MetricWithJustification 
                      label="Quality" 
                      metric={message.fullResponse.evaluation_metrics.generative_ai_scoring_metrics.raw_results_evaluation?.information_quality} 
                    />
                    <MetricWithJustification 
                      label="Diversity" 
                      metric={message.fullResponse.evaluation_metrics.generative_ai_scoring_metrics.raw_results_evaluation?.diversity} 
                    />
                    <MetricWithJustification 
                      label="Overall" 
                      metric={message.fullResponse.evaluation_metrics.generative_ai_scoring_metrics.raw_results_evaluation?.overall} 
                    />
                    
                    {/* LLM response evaluation subsection */}
                    <h4>LLM Response Evaluation</h4>
                    <MetricWithJustification 
                      label="Correctness" 
                      metric={message.fullResponse.evaluation_metrics.generative_ai_scoring_metrics.llm_response_evaluation?.correctness} 
                    />
                    <MetricWithJustification 
                      label="Relevance" 
                      metric={message.fullResponse.evaluation_metrics.generative_ai_scoring_metrics.llm_response_evaluation?.relevance} 
                    />
                    <MetricWithJustification 
                      label="Comprehensiveness" 
                      metric={message.fullResponse.evaluation_metrics.generative_ai_scoring_metrics.llm_response_evaluation?.comprehensiveness} 
                    />
                    <MetricWithJustification 
                      label="Hallucination" 
                      metric={message.fullResponse.evaluation_metrics.generative_ai_scoring_metrics.llm_response_evaluation?.hallucination} 
                    />
                    <MetricWithJustification 
                      label="Clarity" 
                      metric={message.fullResponse.evaluation_metrics.generative_ai_scoring_metrics.llm_response_evaluation?.clarity} 
                    />
                    <MetricWithJustification 
                      label="Overall" 
                      metric={message.fullResponse.evaluation_metrics.generative_ai_scoring_metrics.llm_response_evaluation?.overall} 
                    />
                  </div>
                )}
              </div>
            )}
             {/* Regenerate button - only shown for cached responses */}
            {message.fullResponse.metadata?.from_cache && (
              <>                
                <div className="regenerate-button" onClick={() => submitQuery(message.fullResponse.prompt, false)}>
                  <BiRefresh className="regenerate-icon" />
                  <span className="regenerate-text">Regenerate Response</span>
                </div>
              </>
            )}
          </>
        ) : (
          /* Simple message display for prompt messages or responses without full data */
          <div className="message-text">{message.text}</div>
        )}
      </div>
    );
  };

  /**
   * Main application render function
   * @returns {JSX.Element} - The WebCrawler application UI
   */
  return (
    <div className="app-container">
      {/* Sidebar for chat management */}
      <div className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-title">Chats</div>
          <button className="new-chat-button" onClick={createNewChat}>New Chat</button>
        </div>
        {/* Display chat list or empty state */}
        <div className="chat-list">
          {chats.length > 0 ? (
            chats.map(chat => (
              <div 
                key={chat.id} 
                className={`chat-item ${chat.id === activeChat ? 'active' : ''}`}
                onClick={() => switchChat(chat.id)}
              >
                {/* Render rename input or regular title */}
                {renamingChatId === chat.id ? (
                  <input
                    type="text"
                    className="rename-input"
                    value={newChatTitle}
                    onChange={(e) => setNewChatTitle(e.target.value)}
                    onBlur={finishRenaming}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        finishRenaming();
                      }
                    }}
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <>
                    <div className="chat-title">{chat.title}</div>
                    {/* Chat action buttons */}
                    <div className="chat-actions">
                      <button 
                        className="rename-button" 
                        onClick={(e) => {
                          e.stopPropagation();
                          startRenaming(chat.id, chat.title);
                        }}
                      >
                        ✎
                      </button>
                      <button 
                        className="delete-button" 
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteChat(chat.id);
                        }}
                      >
                        ×
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))
          ) : (
            <div className="empty-chat-list">
              <p>No chats yet</p>
              <p className="empty-chat-hint">Start typing below to create a new chat</p>
            </div>
          )}
        </div>
      </div>
       {/* Main content area */}
      <div className={`main-content ${showUrlPopup ? 'with-popup' : ''}`}>
        <div className="chat-container">
          {/* Chat messages display area */}
          <div className="chat-area" ref={chatAreaRef}>
            {activeChat !== null && currentChat && currentChat.messages.length > 0 ? (
              currentChat.messages.map((message, index) => (
                <Message 
                  key={index} 
                  message={message} 
                  activeTab={messageTabStates[message.id] || 'llm_response'} 
                  onTabChange={handleTabChange}
                />
              ))
            ) : (
              <div className="empty-chat-area">
                <div className="empty-chat-icon">🤖</div>
                <h3>Welcome to DAWC</h3>
                <p>Send a message to start a new conversation</p>
              </div>
            )}
          </div>       
          <div className="footer">
            <div className="toggle-container">
              <label className="toggle-label">
                <span>Enable URL</span>
                <div
                  className={`toggle ${enableUrl ? 'active' : ''}`}
                  onClick={handleEnableUrlToggle}
                  style={{ backgroundColor: enableUrl ? '#2563eb' : '#3f3f3f' }}
                ></div>
              </label>
            </div>

            {/* Prompt input, url toggle button and submit button */}
            <div className="input-container">
              <textarea
                ref={promptInputRef}
                className="prompt-input"
                value={prompt}
                onChange={handlePromptChange}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    // Only submit if the prompt is valid
                    if (isValidPrompt(prompt)) {
                      handleSubmit();
                    }
                  }
                }}
                placeholder="Enter your prompt... (Shift+Enter for new line)"
                rows={1}
                spellCheck={true}
                onScroll={(e) => {
                  // Propagate scroll when at edges
                  if (e.target.scrollLeft === 0) {
                    e.target.style.overflowX = 'hidden';
                  } else {
                    e.target.style.overflowX = 'auto';
                  }
                }}
                disabled={isLoading}
              />
              
              {enableUrl && (
                <button
                  className="icon-button url-button"
                  onClick={() => setShowUrlPopup(!showUrlPopup)}
                >
                  🔗
                </button>
              )}
              
              <button
                className="icon-button submit-button"
                onClick={handleSubmit}
                disabled={!prompt || !isValidPrompt(prompt) || isLoading}
                
              >
                ➤
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* URL popup area */}
      {showUrlPopup && (
        <div className="url-popup">
          <div className="popup-header">
            <h3>Manage URLs</h3>
            <button
              className="popup-close-button"
              onClick={() => setShowUrlPopup(false)}
            >
              ×
            </button>
          </div>

          {/* URL input form when URL mode is enabled */}
          <div className="url-input-container">
            <input
              type="text"
              className="url-input"
              value={urlInput}
              onChange={handleUrlInputChange}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  addUrlWithPrefix();
                }
              }}
              placeholder="https://example.com"
            />
            <button className="add-url-button" onClick={addUrlWithPrefix}>Add URL</button>
          </div>

          {/* Display list of added URLs */}
          <div className="url-list">
            {urls.length > 0 ? (
              <>
                <h4 className="url-list-header">Added URLs:</h4>
                {urls.map((url, index) => (
                  <div key={index} className="url-item">
                    <span className="url-text">{url}</span>
                    <button className="remove-url-button" onClick={() => removeUrl(index)}>×</button>
                  </div>
                ))}
              </>
            ) : (
              <div className="no-urls">No URLs added yet</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default WebCrawler;