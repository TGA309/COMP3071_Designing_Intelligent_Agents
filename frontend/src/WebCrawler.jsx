import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './WebCrawler.css';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import { BiRefresh } from "react-icons/bi"; // Import refresh icon

const WebCrawler = () => {

  const apiUrl = import.meta.env.VITE_API_ENDPOINT;
  const apiPORT = import.meta.env.VITE_API_PORT;
  const [prompt, setPrompt] = useState('');
  const [enableUrl, setEnableUrl] = useState(false);
  const [showUrlPopup, setShowUrlPopup] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [urls, setUrls] = useState([]);
  const chatAreaRef = useRef(null);
  const promptInputRef = useRef(null);
  // State for managing multiple chats
  const [chats, setChats] = useState([
    { id: 1, title: 'New Chat', messages: [] }
  ]);
  const [activeChat, setActiveChat] = useState(1);
  const [renamingChatId, setRenamingChatId] = useState(null);
  const [newChatTitle, setNewChatTitle] = useState('');
  const [_, setApiResponse] = useState(null);
  // State to track active tabs for each message
  const [messageTabStates, setMessageTabStates] = useState({});
  const [isLoading, setIsLoading] = useState(false);

  // Function to update tab state for a specific message
  const handleTabChange = (messageId, tabName) => {
    setMessageTabStates(prevState => ({
      ...prevState,
      [messageId]: tabName
    }));
  };
  
  // Functions for managing chats
  const createNewChat = () => {
    // If no chats exist, create the first chat titled "New Chat"
    // Otherwise, generate a new chat with an incremented number
    const newChatId = chats.length > 0 ? Math.max(...chats.map(chat => chat.id)) + 1 : 1;
    
    let chatTitle = "New Chat";
    
    // Only add a number to the title if there are existing chats
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

  const switchChat = (chatId) => {
    setActiveChat(chatId);
    setUrls([]);
  };

  const startRenaming = (chatId, currentTitle) => {
    setRenamingChatId(chatId);
    setNewChatTitle(currentTitle);
  };

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

  const deleteChat = (chatId) => {
    const updatedChats = chats.filter(chat => chat.id !== chatId);
    setChats(updatedChats);
    
    if (activeChat === chatId && updatedChats.length > 0) {
      setActiveChat(updatedChats[0].id);
    } else if (activeChat === chatId) {
      // Set activeChat to null when all chats are deleted
      setActiveChat(null);
    }
  };

  // Scroll to bottom of chat when messages change
  useEffect(() => {
    if (chatAreaRef.current) {
      chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight;
    }
  }, [chats, activeChat]);

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
      
      return () => {
        if (promptInputRef.current) {
          promptInputRef.current.removeEventListener('focus', handleFocus);
          promptInputRef.current.removeEventListener('blur', handleBlur);
        }
      };
    }
  }, []);

  const handlePromptChange = (e) => {
    setPrompt(e.target.value);
    
    // Auto-resize textarea
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

  const handleEnableUrlToggle = (e) => {
    // Prevent event propagation and default behavior
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    
    const newEnableUrlState = !enableUrl;
    setEnableUrl(newEnableUrlState);
    if (!newEnableUrlState) {
      setShowUrlPopup(false);
    }
  };
  

  const handleUrlInputChange = (e) => {
    setUrlInput(e.target.value);
  };

  const addUrlWithPrefix = () => {
    if (urlInput) {
      let formattedUrl = urlInput;
      if (!formattedUrl.startsWith('http://') && !formattedUrl.startsWith('https://')) {
        formattedUrl = 'https://' + formattedUrl;
      }
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

  const removeUrl = (index) => {
    const newUrls = [...urls];
    newUrls.splice(index, 1);
    setUrls(newUrls);
  };

  const isValidUrl = (string) => {
    try {
      const url = new URL(string);
      if (url.protocol !== 'http:' && url.protocol !== 'https:') {
        return false;
      }
      if (!url.hostname.includes('.')) {
        return false;
      }
      if (/^(\d{1,3}\.){3}\d{1,3}$/.test(url.hostname) && !url.pathname.length > 1) {
        return false;
      }
      return true;
    } catch (_) {
      return false;
    }
  };

  // Add this function to check if the prompt has actual content
  const isValidPrompt = (text) => {
    // Check if the text is empty after trimming whitespace and newlines
    return text.trim().length > 0;
  };

  const handleSubmit = async () => {
    if (prompt && isValidPrompt(prompt)) {
      try {
        // Always proceed with regular submission (using cache when available)
        await submitQuery(prompt, false);
      } catch (error) {
        console.error('Error processing request:', error);
        // Error handling code unchanged
      }
    }
  };

  function safeStringToPercentage(decimalStr, decimalPlaces = 0) {
    const num = parseFloat(decimalStr);
    
    if (isNaN(num)) {
      return "0%"; // or handle error differently
    }
    
    return `${(num * 100).toFixed(decimalPlaces)}%`;
  }

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
  
  const submitQuery = async (userPrompt, forceCrawl) => {
    // Set loading state to true before API call
    setIsLoading(true);
  
    try {
      let data = {
        user_prompt: userPrompt,
        urls: [],
        num_seed_urls: 5,
        force_crawl: forceCrawl,
        use_llm_response: true
      };
      
      if (enableUrl && urls.length > 0) {
        data.urls = urls;
      }
      
      // Always add prompt to chat (removed confirmingForceCrawl check)
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
      
      const response = await axios.post(apiUrl+apiPORT+'/api/crawl', data);
      setApiResponse(response.data);
      
      // Update the chat with the actual response
      const responseMessage = {
        id: Date.now().toString(),
        text: response.data.llm_response,
        type: 'response',
        fullResponse: response.data
      };
      
      const finalChats = [...chats];
      if (chatIndex !== -1) {
        // Replace the loading message with the actual response
        finalChats[chatIndex].messages = [
          ...finalChats[chatIndex].messages.filter(msg => !msg.isLoading),
          responseMessage
        ];
        setChats(finalChats);
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
      
      // Add error message to chat as a response
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

  // Handle Enter key for inputs
  const handleKeyPress = (e, action) => {
    if (e.key === 'Enter') {
      action();
    }
  };

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

  const Message = ({ message, activeTab, onTabChange }) => {
    const showTabs = message.type === 'response' && message.fullResponse;
    return (
      <div className={`message ${message.type}`}>
        <div className="message-type">{message.type === 'prompt' ? 'You' : 'DAWC'}</div>
        
        {showTabs ? (
          <>
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
            
              {activeTab === 'llm_response' && (
              <div className="llm-response">
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({node, inline, className, children, ...props}) {
                      const match = /language-(\w+)/.exec(className || '');
                      return !inline && match ? (
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
                        <code className={className} {...props}>
                          {children}
                        </code>
                      );
                    }
                  }}
                >
                  {message.fullResponse.llm_response}
                </ReactMarkdown>
              </div>
            )}

            {activeTab === 'contents' && (
              <div className="contents-tab">
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

            {activeTab === 'metrics' && (
              <div className="metrics-tab">
                <div className="metrics-section">
                  <h3>Time Metrics</h3>
                  <p>Response Latency: {
                    message.fullResponse.evaluation_metrics?.time_metrics?.duration_seconds 
                      ? formatDuration(message.fullResponse.evaluation_metrics.time_metrics.duration_seconds) 
                      : "N/A"
                  }</p>
                </div>
                
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
                
                {message.fullResponse.evaluation_metrics?.generative_ai_scoring_metrics && (
                  <div className="metrics-section">
                    <h3>AI Scoring Metrics</h3>
                    
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
          <div className="message-text">{message.text}</div>
        )}
      </div>
    );
  };
  
  return (
    <div className="app-container">
      <div className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-title">Chats</div>
          <button className="new-chat-button" onClick={createNewChat}>New Chat</button>
        </div>
        <div className="chat-list">
          {chats.length > 0 ? (
            chats.map(chat => (
              <div 
                key={chat.id} 
                className={`chat-item ${chat.id === activeChat ? 'active' : ''}`}
                onClick={() => switchChat(chat.id)}
              >
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
      
      <div className={`main-content ${showUrlPopup ? 'with-popup' : ''}`}>
        <div className="chat-container">
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
                {isLoading ? 
                  <i className="fas fa-spinner fa-spin"></i> : 
                  <i className="fas fa-paper-plane"></i>
                }
              </button>
            </div>
          </div>
        </div>
      </div>
      
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