import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './WebCrawler.css';

const WebCrawler = () => {
  const [prompt, setPrompt] = useState('');
  const [enableUrl, setEnableUrl] = useState(false);
  const [strictUrl, setStrictUrl] = useState(false);
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

  const handleEnableUrlToggle = () => {
    const newEnableUrlState = !enableUrl;
    setEnableUrl(newEnableUrlState);
    if (!newEnableUrlState) {
      setStrictUrl(false);
      setShowUrlPopup(false);
    }
  };

  const handleStrictUrlToggle = () => {
    if (enableUrl) {
      setStrictUrl(!strictUrl);
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

  const processPrompt = (data) => {
    const updatedChats = [...chats];
    const chatIndex = updatedChats.findIndex(chat => chat.id === activeChat);
    
    if (chatIndex !== -1) {
      const newMessages = [
        ...updatedChats[chatIndex].messages,
        { text: prompt, type: 'prompt' }
      ];
      
      updatedChats[chatIndex].messages = newMessages;
      setChats(updatedChats);
      
      // Simulate API call
      setTimeout(() => {
        const responseMessage = {
          text: `Response to: ${prompt}`,
          type: 'response',
        };
        
        const updatedChatsWithResponse = [...chats];
        const chatIndex = updatedChatsWithResponse.findIndex(chat => chat.id === activeChat);
        
        if (chatIndex !== -1) {
          updatedChatsWithResponse[chatIndex].messages = [
            ...updatedChatsWithResponse[chatIndex].messages,
            responseMessage
          ];
          
          setChats(updatedChatsWithResponse);
        }
      }, 1000);
    }
    
    setPrompt('');
  };

  // Add this function to check if the prompt has actual content
  const isValidPrompt = (text) => {
    // Check if the text is empty after trimming whitespace and newlines
    return text.trim().length > 0;
  };

  // Update the handleSubmit function to check for validity
  const handleSubmit = async () => {
    // Only proceed if the prompt is valid (not just whitespace/newlines)
    if (prompt && isValidPrompt(prompt)) {
      try {
        let data = { prompt };
        if (enableUrl && urls.length > 0) {
          data.urls = urls;
          data.strict = strictUrl;
        }

        // If no active chat, create a new one first
        if (activeChat === null) {
          createNewChat();
          // Need to wait for state update to complete
          setTimeout(() => processPrompt(data), 0);
          return;
        }

        processPrompt(data);
      } catch (error) {
        console.error('Error processing request:', error);
      }
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
                <div key={index} className={`message ${message.type}`}>
                  <div className="message-type">{message.type === 'prompt' ? 'You' : 'Assistant'}</div>
                  <div className="message-text">{message.text}</div>
                </div>
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
              
              <label className="toggle-label">
                <span>Strict URL</span>
                <div
                  className={`toggle ${strictUrl ? 'active' : ''}`}
                  onClick={handleStrictUrlToggle}
                  style={{ 
                    backgroundColor: strictUrl ? '#2563eb' : '#3f3f3f', 
                    opacity: enableUrl ? 1 : 0.5,
                    cursor: enableUrl ? 'pointer' : 'not-allowed'
                  }}
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
                disabled={!prompt || !isValidPrompt(prompt)}
              >
                ➤
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