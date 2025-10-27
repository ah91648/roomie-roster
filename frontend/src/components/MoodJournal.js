import React, { useState, useEffect } from 'react';
import { moodAPI } from '../services/api';
import RoommateSelector from './RoommateSelector';
import { useAuth } from '../contexts/AuthContext';

const MoodJournal = () => {
  // Auth context for roommate linking
  const { user } = useAuth();

  // State
  const [todayEntry, setTodayEntry] = useState(null);
  const [recentEntries, setRecentEntries] = useState([]);
  const [isEditing, setIsEditing] = useState(false);

  // Form state
  const [moodLevel, setMoodLevel] = useState(3);
  const [energyLevel, setEnergyLevel] = useState(3);
  const [notes, setNotes] = useState('');

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');
  const [showRoommateSelector, setShowRoommateSelector] = useState(false);

  // Constants
  const MOOD_EMOJIS = ['😞', '😕', '😐', '🙂', '😄'];
  const MOOD_LABELS = ['Very Bad', 'Bad', 'Okay', 'Good', 'Great'];
  const ENERGY_EMOJIS = ['⚡'];

  useEffect(() => {
    loadData();
  }, []);

  // Watch for roommate linking completion
  useEffect(() => {
    if (showRoommateSelector && user?.roommate) {
      // User just linked to a roommate, call the success handler
      handleRoommateLinked();
    }
  }, [user?.roommate, showRoommateSelector]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get today's date in ISO format
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const todayStr = today.toISOString().split('T')[0];

      // Get last 7 days
      const sevenDaysAgo = new Date(today);
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
      const sevenDaysAgoStr = sevenDaysAgo.toISOString().split('T')[0];

      // Load entries
      const response = await moodAPI.getEntries({
        start_date: sevenDaysAgoStr,
        end_date: todayStr,
        limit: 10
      });

      const entries = response.data || [];

      // Find today's entry
      const todayEntry = entries.find(entry => {
        const entryDate = new Date(entry.date).toISOString().split('T')[0];
        return entryDate === todayStr;
      });

      if (todayEntry) {
        setTodayEntry(todayEntry);
        setMoodLevel(todayEntry.mood_level);
        setEnergyLevel(todayEntry.energy_level);
        setNotes(todayEntry.notes || '');
      } else {
        setTodayEntry(null);
        setMoodLevel(3);
        setEnergyLevel(3);
        setNotes('');
      }

      // Filter out today's entry from recent entries
      const recent = entries.filter(entry => {
        const entryDate = new Date(entry.date).toISOString().split('T')[0];
        return entryDate !== todayStr;
      });

      setRecentEntries(recent);
    } catch (err) {
      // Check if this is a roommate linking error
      const errorMessage = err.response?.data?.error || err.message;
      const isRoommateError = err.response?.status === 403 &&
        (errorMessage.includes('roommate') || errorMessage.includes('link'));

      if (isRoommateError) {
        // Show the roommate selector modal instead of error message
        setShowRoommateSelector(true);
        setError(null); // Clear error since we're showing the modal
      } else {
        setError('Failed to load mood entries: ' + errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      setError(null);
      setSuccessMessage('');

      const entryData = {
        mood_level: moodLevel,
        energy_level: energyLevel,
        notes: notes.trim() || null,
      };

      if (todayEntry) {
        // Update existing entry
        await moodAPI.update(todayEntry.id, entryData);
        setSuccessMessage('Mood entry updated successfully!');
      } else {
        // Create new entry
        await moodAPI.create(entryData);
        setSuccessMessage('Mood entry saved successfully!');
      }

      setIsEditing(false);
      await loadData();

      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setError('Failed to save mood entry: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleCancel = () => {
    if (todayEntry) {
      setMoodLevel(todayEntry.mood_level);
      setEnergyLevel(todayEntry.energy_level);
      setNotes(todayEntry.notes || '');
    }
    setIsEditing(false);
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) return 'Today';
    if (date.toDateString() === yesterday.toDateString()) return 'Yesterday';

    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric'
    });
  };

  const renderEnergyBars = (level, maxLevel = 5, size = 'medium') => {
    const bars = [];
    for (let i = 0; i < maxLevel; i++) {
      bars.push(
        <span
          key={i}
          className={`energy-bar ${i < level ? 'filled' : 'empty'} size-${size}`}
        >
          {i < level ? ENERGY_EMOJIS[0] : '○'}
        </span>
      );
    }
    return bars;
  };

  const handleRoommateLinked = async () => {
    console.log('[MOOD] Roommate linked successfully, closing modal...');
    setShowRoommateSelector(false);

    // Retry loading data
    console.log('[MOOD] Reloading mood data...');
    setTimeout(() => {
      loadData();
    }, 800);
  };

  const handleRoommateSelectorCancel = () => {
    console.log('[MOOD] User cancelled roommate linking');
    setShowRoommateSelector(false);
    setError('You must link your account to a roommate to use productivity features');
  };

  if (loading) {
    return (
      <div className="mood-journal">
        <div className="loading">Loading mood journal...</div>
      </div>
    );
  }

  return (
    <div className="mood-journal">
      <div className="mood-header">
        <h2>Mood Journal</h2>
        <p className="subtitle">Track your daily mood and energy levels</p>
      </div>

      {error && (
        <div className="error-message">
          <p>{error}</p>
          <button onClick={() => setError(null)} className="dismiss-btn">Dismiss</button>
        </div>
      )}

      {successMessage && (
        <div className="success-message">
          <p>{successMessage}</p>
        </div>
      )}

      {/* Today's Entry */}
      <div className="today-entry-card">
        <div className="card-header">
          <h3>How are you feeling today?</h3>
          {todayEntry && !isEditing && (
            <button onClick={() => setIsEditing(true)} className="button secondary small">
              Edit Entry
            </button>
          )}
        </div>

        {(!todayEntry || isEditing) ? (
          <form onSubmit={handleSubmit} className="mood-form">
            {/* Mood Level Selector */}
            <div className="form-section">
              <label className="section-label">Mood:</label>
              <div className="mood-selector">
                {MOOD_EMOJIS.map((emoji, index) => {
                  const level = index + 1;
                  return (
                    <button
                      key={level}
                      type="button"
                      className={`mood-option ${moodLevel === level ? 'selected' : ''}`}
                      onClick={() => setMoodLevel(level)}
                      title={MOOD_LABELS[index]}
                    >
                      <div className="mood-emoji">{emoji}</div>
                      <div className="mood-label">{MOOD_LABELS[index]}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Energy Level Selector */}
            <div className="form-section">
              <label className="section-label">Energy Level:</label>
              <div className="energy-selector">
                {[1, 2, 3, 4, 5].map(level => (
                  <button
                    key={level}
                    type="button"
                    className={`energy-option ${energyLevel === level ? 'selected' : ''}`}
                    onClick={() => setEnergyLevel(level)}
                    title={`${level} / 5`}
                  >
                    {renderEnergyBars(level, 5, 'large')}
                  </button>
                ))}
              </div>
            </div>

            {/* Notes */}
            <div className="form-section">
              <label htmlFor="notes" className="section-label">
                Notes (optional):
              </label>
              <textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows="4"
                placeholder="Anything you'd like to remember about today..."
                className="notes-textarea"
              />
            </div>

            {/* Actions */}
            <div className="form-actions">
              <button type="submit" className="button primary">
                {todayEntry ? 'Update Entry' : 'Save Entry'}
              </button>
              {isEditing && (
                <button type="button" onClick={handleCancel} className="button secondary">
                  Cancel
                </button>
              )}
            </div>
          </form>
        ) : (
          /* Display Today's Entry */
          <div className="entry-display">
            <div className="entry-mood">
              <div className="mood-emoji-large">{MOOD_EMOJIS[todayEntry.mood_level - 1]}</div>
              <div className="mood-label-large">{MOOD_LABELS[todayEntry.mood_level - 1]}</div>
            </div>

            <div className="entry-energy">
              <label>Energy:</label>
              <div className="energy-display">
                {renderEnergyBars(todayEntry.energy_level, 5, 'medium')}
              </div>
            </div>

            {todayEntry.notes && (
              <div className="entry-notes">
                <label>Notes:</label>
                <p>{todayEntry.notes}</p>
              </div>
            )}

            <div className="entry-timestamp">
              Logged at {new Date(todayEntry.created_at || todayEntry.date).toLocaleTimeString('en-US', {
                hour: 'numeric',
                minute: '2-digit'
              })}
            </div>
          </div>
        )}
      </div>

      {/* Recent Entries */}
      {recentEntries.length > 0 && (
        <div className="recent-entries-card">
          <h3>Recent Entries</h3>
          <div className="entries-list">
            {recentEntries.map(entry => (
              <div key={entry.id} className="entry-item">
                <div className="entry-date">
                  {formatDate(entry.date)}
                </div>
                <div className="entry-info">
                  <div className="entry-mood-small">
                    <span className="mood-emoji-small">{MOOD_EMOJIS[entry.mood_level - 1]}</span>
                    <span className="mood-text">{MOOD_LABELS[entry.mood_level - 1]}</span>
                  </div>
                  <div className="entry-energy-small">
                    <label>Energy:</label>
                    {renderEnergyBars(entry.energy_level, 5, 'small')}
                  </div>
                </div>
                {entry.notes && (
                  <div className="entry-notes-preview">
                    {entry.notes.length > 100 ? entry.notes.substring(0, 100) + '...' : entry.notes}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {recentEntries.length === 0 && !loading && (
        <div className="empty-state">
          <p>No previous mood entries. Start tracking your mood daily to see trends!</p>
        </div>
      )}

      {/* Roommate Linking Modal - Shown when productivity features require roommate link */}
      {showRoommateSelector && (
        <div className="modal-overlay" onClick={(e) => {
          // Only close if clicking the overlay background, not the modal content
          if (e.target.className === 'modal-overlay') {
            handleRoommateSelectorCancel();
          }
        }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Roommate Linking Required</h2>
              <button
                className="modal-close"
                onClick={handleRoommateSelectorCancel}
                aria-label="Close modal"
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <p className="modal-info">
                Productivity features (Pomodoro, Todos, Mood Journal) require you to link your Google account to a roommate profile.
                Please select which roommate you are:
              </p>
              <RoommateSelector
                onCancel={handleRoommateSelectorCancel}
                title="Select Your Roommate Profile"
                subtitle="Choose your profile to continue using productivity features"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MoodJournal;
