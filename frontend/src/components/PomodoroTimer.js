import React, { useState, useEffect, useCallback, useRef } from 'react';
import { pomodoroAPI, choreAPI, todoAPI, laundryAPI } from '../services/api';
import RoommateSelector from './RoommateSelector';
import { useAuth } from '../contexts/AuthContext';

const PomodoroTimer = () => {
  // Auth context for roommate linking
  const { user } = useAuth();

  // Active session state
  const [activeSession, setActiveSession] = useState(null);
  const [timeRemaining, setTimeRemaining] = useState(null);

  // Form state for starting new session
  const [sessionType, setSessionType] = useState('focus');
  const [duration, setDuration] = useState(25);
  const [linkedChoreId, setLinkedChoreId] = useState('');
  const [linkedTodoId, setLinkedTodoId] = useState('');
  const [linkedLaundrySlotId, setLinkedLaundrySlotId] = useState('');
  const [notes, setNotes] = useState('');

  // Data state
  const [recentSessions, setRecentSessions] = useState([]);
  const [chores, setChores] = useState([]);
  const [todos, setTodos] = useState([]);
  const [laundrySlots, setLaundrySlots] = useState([]);

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notificationPermission, setNotificationPermission] = useState('default');
  const [showRoommateSelector, setShowRoommateSelector] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);

  // Refs for intervals
  const pollIntervalRef = useRef(null);
  const timerIntervalRef = useRef(null);

  // Request notification permission on mount
  useEffect(() => {
    if ('Notification' in window) {
      setNotificationPermission(Notification.permission);
      if (Notification.permission === 'default') {
        Notification.requestPermission().then(permission => {
          setNotificationPermission(permission);
        });
      }
    }
  }, []);

  // Load initial data
  useEffect(() => {
    loadInitialData();
  }, []);

  // Poll for active session
  useEffect(() => {
    pollActiveSession();
    pollIntervalRef.current = setInterval(pollActiveSession, 2000);

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  // Watch for roommate linking completion
  useEffect(() => {
    if (showRoommateSelector && user?.roommate) {
      // User just linked to a roommate, call the success handler
      handleRoommateLinked();
    }
  }, [user?.roommate, showRoommateSelector]);

  // Client-side timer for countdown
  useEffect(() => {
    if (activeSession && activeSession.status === 'in_progress') {
      updateTimeRemaining();
      timerIntervalRef.current = setInterval(updateTimeRemaining, 1000);

      return () => {
        if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      };
    }
  }, [activeSession]);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load recent sessions, chores, todos, and laundry slots in parallel
      const [sessionsRes, choresRes, todosRes, laundryRes] = await Promise.all([
        pomodoroAPI.getHistory({ limit: 5, status: 'completed' }),
        choreAPI.getAll(),
        todoAPI.getAll({ status: 'pending' }),
        laundryAPI.getAll({ status: 'scheduled' })
      ]);

      setRecentSessions(sessionsRes.data || []);
      setChores(choresRes.data || []);
      setTodos(todosRes.data || []);
      setLaundrySlots(laundryRes.data || []);
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
        setError('Failed to load data: ' + errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const pollActiveSession = async () => {
    try {
      const response = await pomodoroAPI.getActive();
      const session = response.data;

      // Check if session just completed
      if (activeSession && !session) {
        // Session completed, send notification
        sendNotification('Pomodoro session completed!', 'Time for a break!');
        // Refresh recent sessions
        loadRecentSessions();
      }

      setActiveSession(session);
    } catch (err) {
      console.error('Failed to poll active session:', err);
    }
  };

  const loadRecentSessions = async () => {
    try {
      const response = await pomodoroAPI.getHistory({ limit: 5, status: 'completed' });
      setRecentSessions(response.data || []);
    } catch (err) {
      console.error('Failed to load recent sessions:', err);
    }
  };

  const updateTimeRemaining = () => {
    if (!activeSession) return;

    const startTime = new Date(activeSession.start_time);
    const now = new Date();
    const elapsedMinutes = (now - startTime) / 1000 / 60;
    const remainingMinutes = activeSession.planned_duration_minutes - elapsedMinutes;

    if (remainingMinutes <= 0) {
      setTimeRemaining(0);
    } else {
      setTimeRemaining(Math.ceil(remainingMinutes * 60)); // Convert to seconds
    }
  };

  const sendNotification = (title, body) => {
    if (notificationPermission === 'granted') {
      new Notification(title, { body, icon: '/favicon.ico' });
    }
  };

  const handleStartSession = async (e) => {
    e.preventDefault();

    try {
      setError(null);

      const sessionData = {
        session_type: sessionType,
        planned_duration_minutes: parseInt(duration),
        notes: notes || null,
      };

      if (linkedChoreId) sessionData.chore_id = parseInt(linkedChoreId);
      if (linkedTodoId) sessionData.todo_id = parseInt(linkedTodoId);
      if (linkedLaundrySlotId) sessionData.laundry_slot_id = parseInt(linkedLaundrySlotId);

      await pomodoroAPI.start(sessionData);

      // Reset form
      setNotes('');
      setLinkedChoreId('');
      setLinkedTodoId('');
      setLinkedLaundrySlotId('');

      // Refresh active session
      await pollActiveSession();
    } catch (err) {
      // ENHANCED ERROR HANDLING: Detect roommate linking errors
      const errorMessage = err.response?.data?.error || err.message;
      const isRoommateError = err.response?.status === 403 &&
        (errorMessage.includes('roommate') || errorMessage.includes('link'));

      if (isRoommateError) {
        // Save the action to retry after linking
        setPendingAction(() => handleStartSession);
        setShowRoommateSelector(true);
        setError(null); // Clear error since we're showing the modal
      } else {
        setError('Failed to start session: ' + errorMessage);
      }
    }
  };

  const handlePauseSession = async () => {
    if (!activeSession) return;

    try {
      setError(null);
      await pomodoroAPI.pause(activeSession.id);
      await pollActiveSession();
    } catch (err) {
      setError('Failed to pause session: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleCompleteSession = async () => {
    if (!activeSession) return;

    try {
      setError(null);
      await pomodoroAPI.complete(activeSession.id);
      sendNotification('Session completed!', `You completed a ${activeSession.session_type} session`);
      await pollActiveSession();
      await loadRecentSessions();
    } catch (err) {
      setError('Failed to complete session: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleSessionTypeChange = (type) => {
    setSessionType(type);
    // Update default duration based on type
    if (type === 'focus') setDuration(25);
    else if (type === 'short_break') setDuration(5);
    else if (type === 'long_break') setDuration(15);
  };

  const formatTime = (seconds) => {
    if (seconds === null || seconds === undefined) return '--:--';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const formatSessionType = (type) => {
    if (type === 'focus') return 'Focus';
    if (type === 'short_break') return 'Short Break';
    if (type === 'long_break') return 'Long Break';
    return type;
  };

  // Calculate progress percentage for circular timer
  const calculateProgress = () => {
    if (!activeSession || timeRemaining === null) return 0;
    const totalSeconds = activeSession.planned_duration_minutes * 60;
    const progress = (timeRemaining / totalSeconds) * 100;
    return Math.max(0, Math.min(100, progress));
  };

  // Determine timer color class based on session type and remaining time
  const getTimerColorClass = () => {
    if (!activeSession) return 'timer-focus';

    const remainingMinutes = timeRemaining ? timeRemaining / 60 : 0;

    // Critical state: ≤ 1 minute
    if (remainingMinutes <= 1) return 'timer-critical';

    // Warning state: ≤ 5 minutes
    if (remainingMinutes <= 5) return 'timer-warning';

    // Normal state: based on session type
    if (activeSession.session_type === 'focus') return 'timer-focus';
    if (activeSession.session_type === 'short_break') return 'timer-short-break';
    if (activeSession.session_type === 'long_break') return 'timer-long-break';

    return 'timer-focus';
  };

  // Get wave animation speed class based on session type
  const getWaveSpeedClass = () => {
    if (!activeSession) return 'wave-focus';
    if (activeSession.session_type === 'focus') return 'wave-focus';
    if (activeSession.session_type === 'short_break') return 'wave-short-break';
    if (activeSession.session_type === 'long_break') return 'wave-long-break';
    return 'wave-focus';
  };

  const getRelativeTime = (timestamp) => {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now - then;
    const diffMins = Math.floor(diffMs / 1000 / 60);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return `${Math.floor(diffMins / 1440)}d ago`;
  };

  const handleRoommateLinked = async () => {
    console.log('[POMODORO] Roommate linked successfully, closing modal...');
    setShowRoommateSelector(false);

    // Retry the pending action if there is one
    if (pendingAction) {
      console.log('[POMODORO] Retrying pending action...');
      // Small delay to ensure session is fully updated on backend
      setTimeout(() => {
        const action = pendingAction;
        setPendingAction(null);
        action({ preventDefault: () => {} }); // Call with mock event
      }, 800);
    }
  };

  const handleRoommateSelectorCancel = () => {
    console.log('[POMODORO] User cancelled roommate linking');
    setShowRoommateSelector(false);
    setPendingAction(null);
    setError('You must link your account to a roommate to use productivity features');
  };

  if (loading) {
    return (
      <div className="pomodoro-timer">
        <div className="loading">Loading Pomodoro timer...</div>
      </div>
    );
  }

  return (
    <div className="pomodoro-timer">
      <div className="pomodoro-header">
        <h2>Pomodoro Timer</h2>
        <p className="subtitle">Stay focused and productive</p>
      </div>

      {error && (
        <div className="error-message">
          <p>{error}</p>
          <button onClick={() => setError(null)} className="dismiss-btn">Dismiss</button>
        </div>
      )}

      {/* Active Session Display */}
      {activeSession ? (
        <div className={`active-session-card ${getTimerColorClass()}`}>
          {/* Animated wave background */}
          <div className={`wave-background ${getWaveSpeedClass()}`}>
            <div className="wave-layer wave-1"></div>
            <div className="wave-layer wave-2"></div>
            <div className="wave-layer wave-3"></div>
          </div>

          <div className="session-header">
            <h3>Current Session: {formatSessionType(activeSession.session_type)}</h3>
            <span className={`session-status status-${activeSession.status}`}>
              {activeSession.status}
            </span>
          </div>

          {/* Circular Timer Display */}
          <div className="circular-timer-container">
            <svg className="circular-timer" viewBox="0 0 300 300">
              {/* Background circle */}
              <circle
                className="timer-background-circle"
                cx="150"
                cy="150"
                r="135"
                fill="none"
                stroke="rgba(255, 255, 255, 0.2)"
                strokeWidth="12"
              />
              {/* Progress circle */}
              <circle
                className="timer-progress-circle"
                cx="150"
                cy="150"
                r="135"
                fill="none"
                strokeWidth="12"
                strokeLinecap="round"
                strokeDasharray={`${2 * Math.PI * 135}`}
                strokeDashoffset={`${2 * Math.PI * 135 * (1 - calculateProgress() / 100)}`}
                transform="rotate(-90 150 150)"
              />
            </svg>

            {/* Center content */}
            <div className="timer-center-content">
              <div className="time-remaining">
                {formatTime(timeRemaining)}
              </div>
              <div className="time-label">remaining</div>
              <div className="progress-percentage">
                {Math.round(calculateProgress())}%
              </div>
            </div>
          </div>

          {activeSession.notes && (
            <div className="session-notes">
              <strong>Notes:</strong> {activeSession.notes}
            </div>
          )}

          <div className="session-controls">
            {activeSession.status === 'in_progress' && (
              <>
                <button onClick={handlePauseSession} className="button secondary">
                  Pause
                </button>
                <button onClick={handleCompleteSession} className="button primary">
                  Complete
                </button>
              </>
            )}
            {activeSession.status === 'paused' && (
              <button onClick={handleCompleteSession} className="button primary">
                Complete Session
              </button>
            )}
          </div>
        </div>
      ) : (
        /* Start New Session Form */
        <div className="start-session-card">
          <h3>Start New Session</h3>

          <form onSubmit={handleStartSession}>
            <div className="form-row">
              <div className="form-group">
                <label>Session Type:</label>
                <div className="session-type-buttons">
                  <button
                    type="button"
                    className={`type-btn ${sessionType === 'focus' ? 'active' : ''}`}
                    onClick={() => handleSessionTypeChange('focus')}
                  >
                    Focus
                  </button>
                  <button
                    type="button"
                    className={`type-btn ${sessionType === 'short_break' ? 'active' : ''}`}
                    onClick={() => handleSessionTypeChange('short_break')}
                  >
                    Short Break
                  </button>
                  <button
                    type="button"
                    className={`type-btn ${sessionType === 'long_break' ? 'active' : ''}`}
                    onClick={() => handleSessionTypeChange('long_break')}
                  >
                    Long Break
                  </button>
                </div>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="duration">Duration (minutes):</label>
                <input
                  type="number"
                  id="duration"
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                  min="1"
                  max="120"
                  required
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="linkedChore">Link to Chore (optional):</label>
                <select
                  id="linkedChore"
                  value={linkedChoreId}
                  onChange={(e) => setLinkedChoreId(e.target.value)}
                >
                  <option value="">-- No chore --</option>
                  {chores.map(chore => (
                    <option key={chore.id} value={chore.id}>
                      {chore.description}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="linkedTodo">Link to Todo (optional):</label>
                <select
                  id="linkedTodo"
                  value={linkedTodoId}
                  onChange={(e) => setLinkedTodoId(e.target.value)}
                >
                  <option value="">-- No todo --</option>
                  {todos.map(todo => (
                    <option key={todo.id} value={todo.id}>
                      {todo.title}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="linkedLaundrySlot">Link to Laundry Slot (optional):</label>
                <select
                  id="linkedLaundrySlot"
                  value={linkedLaundrySlotId}
                  onChange={(e) => setLinkedLaundrySlotId(e.target.value)}
                >
                  <option value="">-- No laundry slot --</option>
                  {laundrySlots.map(slot => (
                    <option key={slot.id} value={slot.id}>
                      {slot.date} {slot.time_slot} - {slot.load_type}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="notes">Notes (optional):</label>
                <textarea
                  id="notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows="3"
                  placeholder="What are you working on?"
                />
              </div>
            </div>

            <button type="submit" className="button primary start-btn">
              Start Session
            </button>
          </form>
        </div>
      )}

      {/* Recent Sessions */}
      {recentSessions.length > 0 && (
        <div className="recent-sessions-card">
          <h3>Recent Completions</h3>
          <div className="sessions-list">
            {recentSessions.map(session => (
              <div key={session.id} className="session-item">
                <div className="session-icon">✓</div>
                <div className="session-details">
                  <div className="session-type-time">
                    <strong>{formatSessionType(session.session_type)}</strong>
                    <span className="separator">•</span>
                    <span>{session.actual_duration_minutes || session.planned_duration_minutes}min</span>
                    <span className="separator">•</span>
                    <span className="time-ago">{getRelativeTime(session.end_time || session.start_time)}</span>
                  </div>
                  {session.notes && (
                    <div className="session-note">{session.notes}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Notification Permission Reminder */}
      {notificationPermission === 'denied' && (
        <div className="notification-warning">
          Browser notifications are blocked. Enable them in your browser settings to get alerts when sessions complete.
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

export default PomodoroTimer;
