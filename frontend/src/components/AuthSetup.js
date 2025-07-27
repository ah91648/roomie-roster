import React, { useState, useEffect } from 'react';
import { authAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const AuthSetup = () => {
  const [status, setStatus] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [setupStep, setSetupStep] = useState('check-status');

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await authAPI.getStatus();
      const authStatus = response.data;
      
      setStatus(authStatus);
      
      // Determine setup step based on status
      if (!authStatus.google_api_available) {
        setSetupStep('dependencies-missing');
      } else if (!authStatus.credentials_configured) {
        setSetupStep('upload-credentials');
      } else {
        setSetupStep('ready');
      }
      
    } catch (err) {
      setError('Failed to load auth status: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleCredentialUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
      setError(null);
      const fileContent = await file.text();
      const credentials = JSON.parse(fileContent);
      
      await authAPI.setupCredentials(credentials);
      setSetupStep('ready');
      loadStatus();
    } catch (err) {
      setError('Failed to upload credentials: ' + (err.response?.data?.error || err.message));
    }
  };

  if (loading) {
    return <div className="loading">Loading authentication setup...</div>;
  }

  return (
    <div className="auth-setup">
      <div className="header">
        <h2>🔐 Google Authentication Setup</h2>
        <div className="header-actions">
          <button onClick={loadStatus} className="button secondary">
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {/* Setup Progress */}
      <div className="setup-progress">
        <h3>Setup Progress</h3>
        <div className="progress-steps">
          <div className={`step ${status.google_api_available ? 'completed' : 'pending'}`}>
            <span className="step-indicator">
              {status.google_api_available ? '✅' : '❌'}
            </span>
            <span>Google API Dependencies</span>
          </div>
          <div className={`step ${status.credentials_configured ? 'completed' : 'pending'}`}>
            <span className="step-indicator">
              {status.credentials_configured ? '✅' : '⏳'}
            </span>
            <span>OAuth Credentials Configured</span>
          </div>
          <div className={`step ${status.credentials_configured ? 'completed' : 'pending'}`}>
            <span className="step-indicator">
              {status.credentials_configured ? '✅' : '⏳'}
            </span>
            <span>Ready for User Login</span>
          </div>
        </div>
      </div>

      {/* Setup Content */}
      <div className="setup-content">
        {setupStep === 'dependencies-missing' && (
          <div className="setup-step">
            <h3>⚠️ Missing Dependencies</h3>
            <p>Google Authentication API dependencies are not installed. Please install them by running:</p>
            <code>pip install -r requirements.txt</code>
            <p>Then restart the backend server.</p>
          </div>
        )}

        {setupStep === 'upload-credentials' && (
          <div className="setup-step">
            <h3>1. Setup Google OAuth Credentials</h3>
            <p>To enable Google Authentication, you need to configure OAuth 2.0 credentials:</p>
            
            <div className="instructions">
              <h4>Step-by-step instructions:</h4>
              <ol>
                <li>Go to the <a href="https://console.cloud.google.com/" target="_blank" rel="noopener noreferrer">Google Cloud Console</a></li>
                <li>Create a new project or select an existing one</li>
                <li>Enable the following APIs:
                  <ul>
                    <li>Google+ API (for user info)</li>
                    <li>Google Calendar API (if not already enabled)</li>
                  </ul>
                </li>
                <li>Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"</li>
                <li>Choose "Web application" as the application type</li>
                <li>Add authorized redirect URIs:
                  <ul>
                    <li><code>http://localhost:5000/api/auth/callback</code></li>
                    <li>Add your production domain when deploying</li>
                  </ul>
                </li>
                <li>Download the credentials JSON file</li>
                <li>Upload it below</li>
              </ol>
            </div>
            
            <div className="credential-upload">
              <h4>Upload OAuth Credentials</h4>
              <div className="file-upload">
                <label htmlFor="auth-credentials-upload" className="button primary">
                  Upload OAuth Credentials JSON
                </label>
                <input
                  id="auth-credentials-upload"
                  type="file"
                  accept=".json"
                  onChange={handleCredentialUpload}
                  style={{ display: 'none' }}
                />
              </div>
              
              <div className="upload-notes">
                <p className="text-small">
                  <strong>Note:</strong> The uploaded credentials will be stored securely on the server and used to authenticate users via Google OAuth.
                </p>
              </div>
            </div>
          </div>
        )}

        {setupStep === 'ready' && (
          <div className="setup-step">
            <h3>✅ Authentication Ready</h3>
            <p>Google Authentication is properly configured and ready to use!</p>
            
            <div className="feature-list">
              <h4>Available Features:</h4>
              <ul>
                <li>✅ Google OAuth login for users</li>
                <li>✅ Link Google accounts to existing roommates</li>
                <li>✅ Secure session management</li>
                <li>✅ User profile and account management</li>
                <li>✅ Integration with calendar features</li>
              </ul>
            </div>
            
            <div className="next-steps">
              <h4>Next Steps:</h4>
              <ul>
                <li>Users can now sign in with their Google accounts</li>
                <li>First-time users will be prompted to link to a roommate</li>
                <li>Existing calendar integration will work with personal accounts</li>
                <li>All features will be personalized per user</li>
              </ul>
            </div>
          </div>
        )}
      </div>

      {/* Current Status */}
      <div className="current-status">
        <h3>Current Status</h3>
        <div className="status-grid">
          <div className="status-item">
            <span className="status-label">Google API Available:</span>
            <span className={`status-value ${status.google_api_available ? 'success' : 'error'}`}>
              {status.google_api_available ? 'Yes' : 'No'}
            </span>
          </div>
          <div className="status-item">
            <span className="status-label">Credentials Configured:</span>
            <span className={`status-value ${status.credentials_configured ? 'success' : 'inactive'}`}>
              {status.credentials_configured ? 'Yes' : 'No'}
            </span>
          </div>
          <div className="status-item">
            <span className="status-label">Total Users:</span>
            <span className="status-value">
              {status.total_users || 0}
            </span>
          </div>
        </div>
      </div>

      {status.credentials_configured && (
        <div className="warning-section">
          <h4>⚠️ Important Security Notes</h4>
          <ul className="text-small">
            <li>OAuth credentials are stored securely on the server</li>
            <li>User tokens are encrypted and managed automatically</li>
            <li>For production deployment, ensure HTTPS is enabled</li>
            <li>Update redirect URIs in Google Cloud Console for production domains</li>
          </ul>
        </div>
      )}
    </div>
  );
};

export default AuthSetup;