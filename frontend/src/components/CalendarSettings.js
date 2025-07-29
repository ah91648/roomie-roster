import React, { useState, useEffect } from 'react';
import { calendarAPI } from '../services/api';
import BlockedTimeSlotsManager from './BlockedTimeSlotsManager';

const CalendarSettings = () => {
  const [status, setStatus] = useState({});
  const [config, setConfig] = useState({});
  const [calendars, setCalendars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [setupStep, setSetupStep] = useState('check-status');
  const [authUrl, setAuthUrl] = useState('');
  
  // Form state for configuration
  const [configData, setConfigData] = useState({
    enabled: false,
    default_calendar_id: '',
    reminder_settings: {
      laundry_reminders: true,
      chore_reminders: false,
      reminder_minutes: [30, 10]
    }
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [statusResponse, configResponse] = await Promise.all([
        calendarAPI.getStatus(),
        calendarAPI.getConfig()
      ]);
      
      setStatus(statusResponse.data);
      setConfig(configResponse.data);
      setConfigData(configResponse.data);
      
      // Determine setup step based on status
      if (!statusResponse.data.google_api_available) {
        setSetupStep('dependencies-missing');
      } else if (!statusResponse.data.credentials_configured) {
        setSetupStep('upload-credentials');
      } else if (!statusResponse.data.oauth_completed) {
        setSetupStep('oauth-setup');
      } else if (statusResponse.data.fully_configured) {
        setSetupStep('configure-settings');
        // Load calendars if fully configured
        try {
          const calendarsResponse = await calendarAPI.getCalendarList();
          setCalendars(calendarsResponse.data);
        } catch (err) {
          console.error('Failed to load calendars:', err);
        }
      }
      
    } catch (err) {
      setError('Failed to load data: ' + (err.response?.data?.error || err.message));
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
      
      await calendarAPI.setupCredentials(credentials);
      setSetupStep('oauth-setup');
      loadData();
    } catch (err) {
      setError('Failed to upload credentials: ' + (err.response?.data?.error || err.message));
    }
  };

  const startOAuthFlow = async () => {
    try {
      setError(null);
      const response = await calendarAPI.getOAuthUrl();
      setAuthUrl(response.data.auth_url);
      
      // Open OAuth URL in a new window
      window.open(response.data.auth_url, '_blank', 'width=500,height=600');
      
      // Start polling to check if OAuth is complete
      const checkOAuthInterval = setInterval(async () => {
        try {
          const statusResponse = await calendarAPI.getStatus();
          if (statusResponse.data.oauth_completed) {
            clearInterval(checkOAuthInterval);
            setSetupStep('configure-settings');
            loadData();
          }
        } catch (err) {
          console.error('Error checking OAuth status:', err);
        }
      }, 2000);
      
      // Stop polling after 5 minutes
      setTimeout(() => clearInterval(checkOAuthInterval), 300000);
      
    } catch (err) {
      setError('Failed to start OAuth flow: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleConfigChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    if (name.includes('.')) {
      // Handle nested properties
      const [parent, child] = name.split('.');
      setConfigData(prev => ({
        ...prev,
        [parent]: {
          ...prev[parent],
          [child]: type === 'checkbox' ? checked : value
        }
      }));
    } else {
      setConfigData(prev => ({
        ...prev,
        [name]: type === 'checkbox' ? checked : value
      }));
    }
  };

  const handleReminderMinutesChange = (index, value) => {
    const newMinutes = [...configData.reminder_settings.reminder_minutes];
    newMinutes[index] = parseInt(value) || 0;
    setConfigData(prev => ({
      ...prev,
      reminder_settings: {
        ...prev.reminder_settings,
        reminder_minutes: newMinutes
      }
    }));
  };

  const addReminderMinute = () => {
    setConfigData(prev => ({
      ...prev,
      reminder_settings: {
        ...prev.reminder_settings,
        reminder_minutes: [...prev.reminder_settings.reminder_minutes, 15]
      }
    }));
  };

  const removeReminderMinute = (index) => {
    setConfigData(prev => ({
      ...prev,
      reminder_settings: {
        ...prev.reminder_settings,
        reminder_minutes: prev.reminder_settings.reminder_minutes.filter((_, i) => i !== index)
      }
    }));
  };

  const saveConfiguration = async () => {
    try {
      setError(null);
      await calendarAPI.saveConfig(configData);
      setConfig(configData);
      loadData();
    } catch (err) {
      setError('Failed to save configuration: ' + (err.response?.data?.error || err.message));
    }
  };

  const resetIntegration = async () => {
    if (!window.confirm('Are you sure you want to reset the Google Calendar integration? This will remove all credentials and configuration.')) {
      return;
    }
    
    // Note: In a real implementation, you'd want an endpoint to clear credentials
    setSetupStep('upload-credentials');
    setConfigData({
      enabled: false,
      default_calendar_id: '',
      reminder_settings: {
        laundry_reminders: true,
        chore_reminders: false,
        reminder_minutes: [30, 10]
      }
    });
  };

  if (loading) {
    return <div className="loading">Loading calendar settings...</div>;
  }

  return (
    <div className="calendar-settings">
      <div className="header">
        <h2>📅 Google Calendar Integration</h2>
        <div className="header-actions">
          <button onClick={loadData} className="button secondary">
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {/* Setup Steps */}
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
            <span>Credentials Uploaded</span>
          </div>
          <div className={`step ${status.oauth_completed ? 'completed' : 'pending'}`}>
            <span className="step-indicator">
              {status.oauth_completed ? '✅' : '⏳'}
            </span>
            <span>OAuth Authentication</span>
          </div>
          <div className={`step ${status.fully_configured ? 'completed' : 'pending'}`}>
            <span className="step-indicator">
              {status.fully_configured ? '✅' : '⏳'}
            </span>
            <span>Configuration Complete</span>
          </div>
        </div>
      </div>

      {/* Setup Content */}
      <div className="setup-content">
        {setupStep === 'dependencies-missing' && (
          <div className="setup-step">
            <h3>⚠️ Missing Dependencies</h3>
            <p>Google Calendar API dependencies are not installed. Please install them by running:</p>
            <code>pip install -r requirements.txt</code>
            <p>Then restart the backend server.</p>
          </div>
        )}

        {setupStep === 'upload-credentials' && (
          <div className="setup-step">
            <h3>1. Upload Google API Credentials</h3>
            <p>To integrate with Google Calendar, you need to:</p>
            <ol>
              <li>Go to the <a href="https://console.cloud.google.com/" target="_blank" rel="noopener noreferrer">Google Cloud Console</a></li>
              <li>Create a new project or select an existing one</li>
              <li>Enable the Google Calendar API</li>
              <li>Create credentials (OAuth 2.0 Client ID)</li>
              <li>Download the credentials JSON file</li>
              <li>Upload it below</li>
            </ol>
            
            <div className="file-upload">
              <label htmlFor="credentials-upload" className="button primary">
                Upload Credentials JSON
              </label>
              <input
                id="credentials-upload"
                type="file"
                accept=".json"
                onChange={handleCredentialUpload}
                style={{ display: 'none' }}
              />
            </div>
          </div>
        )}

        {setupStep === 'oauth-setup' && (
          <div className="setup-step">
            <h3>2. Authorize Access</h3>
            <p>Click the button below to authorize RoomieRoster to access your Google Calendar:</p>
            
            <button onClick={startOAuthFlow} className="button primary">
              Authorize Google Calendar Access
            </button>
            
            {authUrl && (
              <div className="oauth-instructions">
                <p>A new window should have opened for authorization. If not, click <a href={authUrl} target="_blank" rel="noopener noreferrer">here</a>.</p>
                <p>After authorizing, this page will automatically update.</p>
              </div>
            )}
          </div>
        )}

        {setupStep === 'configure-settings' && (
          <div className="setup-step">
            <h3>3. Configure Calendar Settings</h3>
            
            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  name="enabled"
                  checked={configData.enabled}
                  onChange={handleConfigChange}
                />
                Enable Google Calendar Integration
              </label>
            </div>

            {configData.enabled && (
              <>
                <div className="form-group">
                  <label>Default Calendar:</label>
                  <select
                    name="default_calendar_id"
                    value={configData.default_calendar_id}
                    onChange={handleConfigChange}
                    className="input"
                  >
                    <option value="">Select a calendar</option>
                    {calendars.map(calendar => (
                      <option key={calendar.id} value={calendar.id}>
                        {calendar.name} {calendar.primary ? '(Primary)' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="reminder-settings">
                  <h4>Reminder Settings</h4>
                  
                  <div className="form-group">
                    <label>
                      <input
                        type="checkbox"
                        name="reminder_settings.laundry_reminders"
                        checked={configData.reminder_settings.laundry_reminders}
                        onChange={handleConfigChange}
                      />
                      Create reminders for laundry slots
                    </label>
                  </div>

                  <div className="form-group">
                    <label>
                      <input
                        type="checkbox"
                        name="reminder_settings.chore_reminders"
                        checked={configData.reminder_settings.chore_reminders}
                        onChange={handleConfigChange}
                      />
                      Create reminders for chore assignments
                    </label>
                  </div>

                  <div className="form-group">
                    <label>Reminder Times (minutes before):</label>
                    <div className="reminder-minutes">
                      {configData.reminder_settings.reminder_minutes.map((minutes, index) => (
                        <div key={index} className="reminder-minute-item">
                          <input
                            type="number"
                            value={minutes}
                            onChange={(e) => handleReminderMinutesChange(index, e.target.value)}
                            min="1"
                            max="10080"
                            className="input small"
                          />
                          <button
                            type="button"
                            onClick={() => removeReminderMinute(index)}
                            className="button small danger"
                          >
                            Remove
                          </button>
                        </div>
                      ))}
                      <button
                        type="button"
                        onClick={addReminderMinute}
                        className="button small secondary"
                      >
                        Add Reminder Time
                      </button>
                    </div>
                  </div>
                </div>

                <div className="form-actions">
                  <button onClick={saveConfiguration} className="button primary">
                    Save Configuration
                  </button>
                </div>
              </>
            )}

            <div className="danger-zone">
              <h4>Danger Zone</h4>
              <button onClick={resetIntegration} className="button danger">
                Reset Integration
              </button>
              <p className="text-small">This will remove all Google Calendar credentials and configuration.</p>
            </div>
          </div>
        )}
      </div>

      {/* Blocked Time Slots Management */}
      {setupStep === 'configure-settings' && (
        <BlockedTimeSlotsManager />
      )}

      {/* Current Status */}
      <div className="current-status">
        <h3>Current Status</h3>
        <div className="status-grid">
          <div className="status-item">
            <span className="status-label">Integration Enabled:</span>
            <span className={`status-value ${config.enabled ? 'success' : 'inactive'}`}>
              {config.enabled ? 'Yes' : 'No'}
            </span>
          </div>
          <div className="status-item">
            <span className="status-label">Default Calendar:</span>
            <span className="status-value">
              {config.default_calendar_id ? 
                calendars.find(c => c.id === config.default_calendar_id)?.name || 'Unknown' : 
                'Not set'
              }
            </span>
          </div>
          <div className="status-item">
            <span className="status-label">Laundry Reminders:</span>
            <span className={`status-value ${config.reminder_settings?.laundry_reminders ? 'success' : 'inactive'}`}>
              {config.reminder_settings?.laundry_reminders ? 'Enabled' : 'Disabled'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CalendarSettings;