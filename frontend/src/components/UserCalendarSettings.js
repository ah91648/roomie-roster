import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { userCalendarAPI } from '../services/api';

const UserCalendarSettings = () => {
  const { isAuthenticated, hasRoommate, user } = useAuth();
  const [config, setConfig] = useState({});
  const [calendars, setCalendars] = useState([]);
  const [syncStatus, setSyncStatus] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState(null);
  const [lastSyncResult, setLastSyncResult] = useState(null);

  useEffect(() => {
    if (isAuthenticated) {
      loadData();
    }
  }, [isAuthenticated]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [configResponse, syncStatusResponse] = await Promise.all([
        userCalendarAPI.getConfig(),
        userCalendarAPI.getSyncStatus()
      ]);
      
      setConfig(configResponse.data);
      setSyncStatus(syncStatusResponse.data);
      
      // Load calendars if user has credentials
      if (syncStatusResponse.data.has_credentials) {
        try {
          const calendarsResponse = await userCalendarAPI.getCalendars();
          setCalendars(calendarsResponse.data);
        } catch (err) {
          console.error('Failed to load calendars:', err);
          setError('Failed to load calendars. Please check your Google account permissions.');
        }
      }
      
    } catch (err) {
      setError('Failed to load calendar settings: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleConfigChange = (path, value) => {
    setConfig(prev => {
      const newConfig = { ...prev };
      const keys = path.split('.');
      let current = newConfig;
      
      for (let i = 0; i < keys.length - 1; i++) {
        if (!current[keys[i]]) current[keys[i]] = {};
        current = current[keys[i]];
      }
      
      current[keys[keys.length - 1]] = value;
      return newConfig;
    });
  };

  const handleReminderMinutesChange = (index, value) => {
    const newMinutes = [...(config.reminder_settings?.reminder_minutes || [])];
    newMinutes[index] = parseInt(value) || 0;
    handleConfigChange('reminder_settings.reminder_minutes', newMinutes);
  };

  const addReminderMinute = () => {
    const currentMinutes = config.reminder_settings?.reminder_minutes || [];
    handleConfigChange('reminder_settings.reminder_minutes', [...currentMinutes, 15]);
  };

  const removeReminderMinute = (index) => {
    const currentMinutes = config.reminder_settings?.reminder_minutes || [];
    handleConfigChange('reminder_settings.reminder_minutes', 
      currentMinutes.filter((_, i) => i !== index)
    );
  };

  const saveConfig = async () => {
    try {
      setSaving(true);
      setError(null);
      
      await userCalendarAPI.saveConfig(config);
      await loadData(); // Reload to get updated status
      
    } catch (err) {
      setError('Failed to save configuration: ' + (err.response?.data?.error || err.message));
    } finally {
      setSaving(false);
    }
  };

  const syncNow = async () => {
    try {
      setSyncing(true);
      setError(null);
      
      const response = await userCalendarAPI.syncChores();
      setLastSyncResult(response.data);
      
      // Reload sync status
      const statusResponse = await userCalendarAPI.getSyncStatus();
      setSyncStatus(statusResponse.data);
      
    } catch (err) {
      setError('Failed to sync chores: ' + (err.response?.data?.error || err.message));
    } finally {
      setSyncing(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="user-calendar-settings">
        <div className="auth-required">
          <h3>🔐 Authentication Required</h3>
          <p>Please sign in with Google to access personal calendar settings.</p>
        </div>
      </div>
    );
  }

  if (!hasRoommate) {
    return (
      <div className="user-calendar-settings">
        <div className="roommate-required">
          <h3>🏠 Roommate Linking Required</h3>
          <p>Please link your Google account to a roommate to sync chores to your personal calendar.</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="user-calendar-settings">
        <div className="loading">Loading personal calendar settings...</div>
      </div>
    );
  }

  return (
    <div className="user-calendar-settings">
      <div className="header">
        <h2>📅 Personal Calendar Settings</h2>
        <div className="user-info">
          <span>For: {user?.name} ({user?.roommate?.name})</span>
        </div>
      </div>

      {error && (
        <div className="error">
          {error}
          <button onClick={() => setError(null)} className="button small">×</button>
        </div>
      )}

      {/* Sync Status Overview */}
      <div className="sync-status-overview">
        <h3>Sync Status</h3>
        <div className="status-grid">
          <div className="status-item">
            <span className="status-label">Calendar Sync:</span>
            <span className={`status-value ${syncStatus.sync_enabled ? 'success' : 'inactive'}`}>
              {syncStatus.sync_enabled ? 'Enabled' : 'Disabled'}
            </span>
          </div>
          <div className="status-item">
            <span className="status-label">Current Assignments:</span>
            <span className="status-value">
              {syncStatus.current_assignments_count || 0}
            </span>
          </div>
          <div className="status-item">
            <span className="status-label">Google Credentials:</span>
            <span className={`status-value ${syncStatus.has_credentials ? 'success' : 'error'}`}>
              {syncStatus.has_credentials ? 'Connected' : 'Not Connected'}
            </span>
          </div>
        </div>
      </div>

      {!syncStatus.has_credentials && (
        <div className="credentials-warning">
          <h4>⚠️ Google Calendar Access Required</h4>
          <p>Your Google account needs calendar permissions to sync chores. This was granted when you logged in.</p>
          <p>If sync is not working, try logging out and back in to refresh permissions.</p>
        </div>
      )}

      {/* Calendar Selection */}
      <div className="calendar-selection">
        <h3>Calendar Configuration</h3>
        
        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={config.chore_sync_enabled || false}
              onChange={(e) => handleConfigChange('chore_sync_enabled', e.target.checked)}
            />
            Enable chore sync to my Google Calendar
          </label>
        </div>

        {config.chore_sync_enabled && (
          <>
            <div className="form-group">
              <label>Target Calendar:</label>
              <select
                value={config.selected_calendar_id || 'primary'}
                onChange={(e) => handleConfigChange('selected_calendar_id', e.target.value)}
                className="input"
              >
                <option value="primary">Primary Calendar</option>
                {calendars.map(calendar => (
                  <option key={calendar.id} value={calendar.id}>
                    {calendar.name} {calendar.primary ? '(Primary)' : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Sync Preferences */}
            <div className="sync-preferences">
              <h4>Sync Preferences</h4>
              
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={config.sync_preferences?.sync_assigned_chores !== false}
                    onChange={(e) => handleConfigChange('sync_preferences.sync_assigned_chores', e.target.checked)}
                  />
                  Sync assigned chores
                </label>
              </div>

              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={config.sync_preferences?.include_sub_chores !== false}
                    onChange={(e) => handleConfigChange('sync_preferences.include_sub_chores', e.target.checked)}
                  />
                  Include sub-chore details
                </label>
              </div>

              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={config.sync_preferences?.auto_sync !== false}
                    onChange={(e) => handleConfigChange('sync_preferences.auto_sync', e.target.checked)}
                  />
                  Automatically sync new assignments
                </label>
              </div>
            </div>

            {/* Event Settings */}
            <div className="event-settings">
              <h4>Event Settings</h4>
              
              <div className="form-group">
                <label>Event Title Prefix:</label>
                <input
                  type="text"
                  value={config.event_settings?.event_prefix || '🧹'}
                  onChange={(e) => handleConfigChange('event_settings.event_prefix', e.target.value)}
                  className="input small"
                  placeholder="🧹"
                />
              </div>

              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={config.event_settings?.include_points !== false}
                    onChange={(e) => handleConfigChange('event_settings.include_points', e.target.checked)}
                  />
                  Include points in event title
                </label>
              </div>

              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={config.reminder_settings?.all_day_events || false}
                    onChange={(e) => handleConfigChange('reminder_settings.all_day_events', e.target.checked)}
                  />
                  Create as all-day events
                </label>
              </div>
            </div>

            {/* Reminder Settings */}
            <div className="reminder-settings">
              <h4>Reminder Settings</h4>
              
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={config.reminder_settings?.chore_reminders !== false}
                    onChange={(e) => handleConfigChange('reminder_settings.chore_reminders', e.target.checked)}
                  />
                  Enable popup reminders
                </label>
              </div>

              {config.reminder_settings?.chore_reminders !== false && (
                <div className="form-group">
                  <label>Reminder Times (minutes before due):</label>
                  <div className="reminder-minutes">
                    {(config.reminder_settings?.reminder_minutes || [30, 10]).map((minutes, index) => (
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
              )}
            </div>
          </>
        )}
      </div>

      {/* Action Buttons */}
      <div className="action-buttons">
        <button
          onClick={saveConfig}
          disabled={saving}
          className="button primary"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>

        {config.chore_sync_enabled && syncStatus.has_credentials && (
          <button
            onClick={syncNow}
            disabled={syncing || !hasRoommate}
            className="button secondary"
          >
            {syncing ? 'Syncing...' : 'Sync Now'}
          </button>
        )}

        <button
          onClick={loadData}
          className="button secondary"
        >
          Refresh
        </button>
      </div>

      {/* Last Sync Result */}
      {lastSyncResult && (
        <div className="sync-result">
          <h4>Last Sync Result</h4>
          <div className="sync-summary">
            <p>✅ Synced {lastSyncResult.synced_count} chores to calendar</p>
            {lastSyncResult.errors && lastSyncResult.errors.length > 0 && (
              <div className="sync-errors">
                <h5>Errors:</h5>
                <ul>
                  {lastSyncResult.errors.map((error, index) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
              </div>
            )}
            {lastSyncResult.events && lastSyncResult.events.length > 0 && (
              <div className="synced-events">
                <h5>Synced Events:</h5>
                <ul>
                  {lastSyncResult.events.map((event, index) => (
                    <li key={index}>
                      <a href={event.event_link} target="_blank" rel="noopener noreferrer">
                        Chore ID {event.chore_id}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Help Section */}
      <div className="help-section">
        <h4>ℹ️ How It Works</h4>
        <ul>
          <li>When enabled, your assigned chores automatically appear in your Google Calendar</li>
          <li>Events include chore details, points, and due dates</li>
          <li>Popup reminders help ensure you don't miss deadlines</li>
          <li>Manual sync updates your calendar with current assignments</li>
          <li>All-day events appear at the top of your calendar day</li>
        </ul>
      </div>
    </div>
  );
};

export default UserCalendarSettings;