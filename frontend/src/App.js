import React, { useState, useEffect } from 'react';
import RoommateManager from './components/RoommateManager';
import ChoreManager from './components/ChoreManager';
import AssignmentDisplay from './components/AssignmentDisplay';
import ShoppingListManager from './components/ShoppingListManager';
import RequestManager from './components/RequestManager';
import LaundryScheduler from './components/LaundryScheduler';
import PomodoroTimer from './components/PomodoroTimer';
import TodoManager from './components/TodoManager';
import MoodJournal from './components/MoodJournal';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import GoogleLoginButton from './components/GoogleLoginButton';
import UserProfile from './components/UserProfile';
import RoommateSelector from './components/RoommateSelector';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { stateAPI } from './services/api';
import './App.css';

// Main App component that uses auth context
function MainApp() {
  const [activeTab, setActiveTab] = useState('assignments');
  const [appStatus, setAppStatus] = useState('loading');
  const [error, setError] = useState(null);
  const {
    isAuthenticated,
    user,
    needsRoommateLink,
    isLoading: authLoading,
    isInitialized,
    isConfigured,
    loginWithGoogle
  } = useAuth();

  // Handle keyboard navigation for tabs
  const handleTabKeyPress = (event, tabId) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      setActiveTab(tabId);
    }
  };

  useEffect(() => {
    checkAppHealth();
  }, []);

  const checkAppHealth = async () => {
    try {
      await stateAPI.health();
      setAppStatus('ready');
      setError(null);
    } catch (err) {
      setAppStatus('error');
      setError('Unable to connect to the backend server. Make sure the Flask server is running on port 5002.');
    }
  };

  const tabs = [
    { id: 'assignments', label: 'Assignments', icon: '📋' },
    { id: 'roommates', label: 'Roommates', icon: '👥' },
    { id: 'chores', label: 'Chores', icon: '🧹' },
    { id: 'laundry', label: 'Laundry', icon: '🧺' },
    { id: 'shopping', label: 'Shopping List', icon: '🛒' },
    { id: 'requests', label: 'Requests', icon: '🙋' },
    { id: 'separator', label: 'PRODUCTIVITY', isSeparator: true },
    { id: 'pomodoro', label: 'Pomodoro', icon: '⏱️' },
    { id: 'todos', label: 'Todos', icon: '✅' },
    { id: 'mood', label: 'Mood', icon: '😊' },
    { id: 'analytics', label: 'Analytics', icon: '📊' },
  ];

  const renderActiveComponent = () => {
    switch (activeTab) {
      case 'roommates':
        return <RoommateManager />;
      case 'chores':
        return <ChoreManager />;
      case 'laundry':
        return <LaundryScheduler />;
      case 'shopping':
        return <ShoppingListManager />;
      case 'requests':
        return <RequestManager />;
      case 'pomodoro':
        return <PomodoroTimer />;
      case 'todos':
        return <TodoManager />;
      case 'mood':
        return <MoodJournal />;
      case 'analytics':
        return <AnalyticsDashboard />;
      case 'assignments':
      default:
        return <AssignmentDisplay />;
    }
  };

  // Show loading state while checking app health or auth status
  if (appStatus === 'loading' || authLoading || !isInitialized) {
    return (
      <div className="app-loading">
        <div className="loading-content">
          <h2>🏠 RoomieRoster</h2>
          <p>Loading application...</p>
        </div>
      </div>
    );
  }

  if (appStatus === 'error') {
    return (
      <div className="app-error">
        <div className="error-content">
          <h2>🏠 RoomieRoster</h2>
          <div className="error-message">
            <h3>Connection Error</h3>
            <p>{error}</p>
            <button onClick={checkAppHealth} className="button primary">
              Retry Connection
            </button>
            <div className="help-text">
              <p>To start the backend server:</p>
              <code>cd backend && PORT=5002 python app.py</code>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // AUTHENTICATION GATE: If not authenticated, show login page ONLY
  if (!isAuthenticated && isInitialized) {
    return (
      <div className="app-login-required">
        <div className="login-content">
          <div className="login-header">
            <h1 className="app-title">
              🏠 <span>RoomieRoster</span>
            </h1>
            <p className="app-subtitle">Household Chore Management Made Easy</p>
          </div>

          <div className="login-message">
            <div className="lock-icon">🔒</div>
            <h2>Authentication Required</h2>
            <p>
              RoomieRoster is a private household management app.
              You must be logged in with a registered Google account to access this application.
            </p>
          </div>

          {isConfigured ? (
            <div className="login-actions">
              <GoogleLoginButton />
              <p className="login-help">
                Only registered household members can access this app.
              </p>
            </div>
          ) : (
            <div className="login-actions">
              <div className="auth-setup-notice">
                <h3>Setup Required</h3>
                <p>Google Authentication needs to be configured by an administrator.</p>
                <p className="help-text">
                  Please contact your household administrator to complete the authentication setup.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <h1 className="app-title">
              🏠 <span>RoomieRoster</span>
            </h1>
            <p className="app-subtitle">Household Chore Management Made Easy</p>
          </div>
          
          <div className="header-right">
            {isAuthenticated ? (
              <UserProfile compact={true} showRoommateInfo={true} showActions={true} />
            ) : isConfigured ? (
              <GoogleLoginButton />
            ) : null}
          </div>
        </div>
      </header>

      <nav className="app-nav">
        <div className="nav-container">
          <button 
            className="nav-scroll-btn nav-scroll-left"
            onClick={() => {
              const navTabs = document.querySelector('.nav-tabs');
              navTabs.scrollBy({ left: -200, behavior: 'smooth' });
            }}
            aria-label="Scroll left"
          >
            ‹
          </button>
          
          <div className="nav-tabs">
            {tabs.map(tab => {
              // Hide auth-required tabs for non-authenticated users
              if (tab.authRequired && !isAuthenticated) {
                return null;
              }

              // Render separator as visual element
              if (tab.isSeparator) {
                return (
                  <div key={tab.id} className="nav-separator">
                    <span className="separator-label">{tab.label}</span>
                  </div>
                );
              }

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  onKeyPress={(e) => handleTabKeyPress(e, tab.id)}
                  className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
                  role="tab"
                  aria-selected={activeTab === tab.id}
                  aria-controls={`${tab.id}-panel`}
                  tabIndex={activeTab === tab.id ? 0 : -1}
                  title={tab.label}
                >
                  <span className="tab-icon" aria-hidden="true">{tab.icon}</span>
                  <span className="tab-label">{tab.label}</span>
                </button>
              );
            })}
          </div>
          
          <button 
            className="nav-scroll-btn nav-scroll-right"
            onClick={() => {
              const navTabs = document.querySelector('.nav-tabs');
              navTabs.scrollBy({ left: 200, behavior: 'smooth' });
            }}
            aria-label="Scroll right"
          >
            ›
          </button>
        </div>
      </nav>

      <main className="app-main">
        <div className="main-content">
          {renderActiveComponent()}
        </div>
      </main>

      <footer className="app-footer">
        <p>Zeith - Productivity & household management platform (v3.0 - Productivity Features)</p>
      </footer>

      {/* Roommate Linking Modal */}
      {needsRoommateLink && (
        <div className="modal-overlay">
          <div className="modal-content">
            <RoommateSelector />
          </div>
        </div>
      )}
    </div>
  );
}

// Root App component with AuthProvider
function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}

export default App;