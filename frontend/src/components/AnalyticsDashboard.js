import React, { useState, useEffect } from 'react';
import { analyticsAPI, assignmentAPI } from '../services/api';
import RoommateSelector from './RoommateSelector';
import { useAuth } from '../contexts/AuthContext';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

const AnalyticsDashboard = () => {
  // Auth context for roommate linking
  const { user } = useAuth();

  // State
  const [dashboardData, setDashboardData] = useState(null);
  const [period, setPeriod] = useState('week');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showRoommateSelector, setShowRoommateSelector] = useState(false);

  // Load dashboard data
  useEffect(() => {
    loadDashboard();
  }, [period]);

  // Watch for roommate linking completion
  useEffect(() => {
    if (showRoommateSelector && user?.roommate) {
      // User just linked to a roommate, call the success handler
      handleRoommateLinked();
    }
  }, [user?.roommate, showRoommateSelector]);

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await analyticsAPI.getDashboard(period);
      setDashboardData(response.data);
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
        setError('Failed to load analytics: ' + errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const formatPeriodLabel = (period) => {
    if (period === 'week') return 'This Week';
    if (period === 'month') return 'This Month';
    if (period === 'all') return 'All Time';
    return period;
  };

  const formatMoodData = (moodTrends) => {
    if (!moodTrends || !moodTrends.daily_moods) return [];

    return moodTrends.daily_moods.map(item => ({
      date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      mood: item.avg_mood,
      energy: item.avg_energy,
    }));
  };

  const formatPomodoroData = (pomodoroStats) => {
    if (!pomodoroStats || !pomodoroStats.sessions_by_day) return [];

    return pomodoroStats.sessions_by_day.map(item => ({
      date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      focus: item.focus_count || 0,
      breaks: (item.short_break_count || 0) + (item.long_break_count || 0),
      total: item.total_count || 0,
    }));
  };

  const handleRoommateLinked = async () => {
    console.log('[ANALYTICS] Roommate linked successfully, closing modal...');
    setShowRoommateSelector(false);

    // Retry loading dashboard
    console.log('[ANALYTICS] Reloading analytics dashboard...');
    setTimeout(() => {
      loadDashboard();
    }, 800);
  };

  const handleRoommateSelectorCancel = () => {
    console.log('[ANALYTICS] User cancelled roommate linking');
    setShowRoommateSelector(false);
    setError('You must link your account to a roommate to use productivity features');
  };

  if (loading) {
    return (
      <div className="analytics-dashboard">
        <div className="loading">Loading analytics...</div>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="analytics-dashboard">
        <div className="error-message">No dashboard data available</div>
      </div>
    );
  }

  const {
    current_cycle,
    pomodoro,
    mood,
    snapshots,
    insights
  } = dashboardData;

  return (
    <div className="analytics-dashboard">
      <div className="dashboard-header">
        <h2>Analytics Dashboard</h2>
        <div className="period-selector">
          <label>Period:</label>
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="period-select"
          >
            <option value="week">Week</option>
            <option value="month">Month</option>
            <option value="all">All Time</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="error-message">
          <p>{error}</p>
          <button onClick={() => setError(null)} className="dismiss-btn">Dismiss</button>
        </div>
      )}

      {/* Summary Cards */}
      <div className="summary-cards">
        <div className="summary-card">
          <div className="card-icon">📊</div>
          <div className="card-content">
            <h3>Productivity Summary</h3>
            <div className="card-stats">
              <div className="stat-item">
                <span className="stat-label">Total Pomodoros:</span>
                <span className="stat-value">{pomodoro?.total_sessions || 0}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Avg per Day:</span>
                <span className="stat-value">
                  {insights?.avg_daily_pomodoros?.toFixed(1) || 0}
                </span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Total Focus Time:</span>
                <span className="stat-value">
                  {pomodoro?.total_focus_minutes ? `${Math.floor(pomodoro.total_focus_minutes / 60)}h ${pomodoro.total_focus_minutes % 60}m` : '0h 0m'}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="summary-card">
          <div className="card-icon">✅</div>
          <div className="card-content">
            <h3>Current Cycle</h3>
            <div className="card-stats">
              <div className="stat-item">
                <span className="stat-label">Chores Assigned:</span>
                <span className="stat-value">{current_cycle?.chores_assigned || 0}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Completion Rate:</span>
                <span className="stat-value">
                  {current_cycle?.completion_rate !== undefined
                    ? `${Math.round(current_cycle.completion_rate)}%`
                    : '0%'}
                </span>
              </div>
              <div className="completion-bar-container">
                <div
                  className="completion-bar"
                  style={{
                    width: `${current_cycle?.completion_rate || 0}%`,
                    backgroundColor: current_cycle?.completion_rate >= 80 ? '#4CAF50' : '#FFC107'
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="summary-card">
          <div className="card-icon">😊</div>
          <div className="card-content">
            <h3>Mood & Energy</h3>
            <div className="card-stats">
              <div className="stat-item">
                <span className="stat-label">Avg Mood:</span>
                <span className="stat-value">
                  {mood?.average_mood ? `${mood.average_mood.toFixed(1)} / 5` : 'N/A'}
                </span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Avg Energy:</span>
                <span className="stat-value">
                  {mood?.average_energy ? `${mood.average_energy.toFixed(1)} / 5` : 'N/A'}
                </span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Entries Logged:</span>
                <span className="stat-value">{mood?.total_entries || 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Mood Trend Chart */}
      {mood && mood.daily_moods && mood.daily_moods.length > 0 && (
        <div className="chart-card">
          <h3>Mood & Energy Trends</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={formatMoodData(mood)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis domain={[0, 5]} />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="mood"
                stroke="#8884d8"
                strokeWidth={2}
                name="Mood Level"
                dot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="energy"
                stroke="#82ca9d"
                strokeWidth={2}
                name="Energy Level"
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Pomodoro Activity Chart */}
      {pomodoro && pomodoro.sessions_by_day && pomodoro.sessions_by_day.length > 0 && (
        <div className="chart-card">
          <h3>Pomodoro Activity</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={formatPomodoroData(pomodoro)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="focus" fill="#FF6B6B" name="Focus Sessions" />
              <Bar dataKey="breaks" fill="#4ECDC4" name="Break Sessions" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Insights */}
      {insights && Object.keys(insights).length > 0 && (
        <div className="insights-card">
          <h3>💡 Insights</h3>
          <div className="insights-list">
            {insights.most_productive_day && (
              <div className="insight-item">
                <strong>Most productive day:</strong> {insights.most_productive_day}
              </div>
            )}
            {insights.avg_daily_pomodoros !== undefined && (
              <div className="insight-item">
                <strong>Average daily Pomodoros:</strong> {insights.avg_daily_pomodoros.toFixed(1)}
              </div>
            )}
            {insights.mood_trend !== undefined && (
              <div className="insight-item">
                <strong>Mood trend:</strong>{' '}
                {insights.mood_trend > 0 ? (
                  <span className="trend-up">↑ Improved by {(insights.mood_trend * 100).toFixed(0)}%</span>
                ) : insights.mood_trend < 0 ? (
                  <span className="trend-down">↓ Decreased by {Math.abs(insights.mood_trend * 100).toFixed(0)}%</span>
                ) : (
                  <span>Stable</span>
                )}
              </div>
            )}
            {insights.total_focus_hours !== undefined && (
              <div className="insight-item">
                <strong>Total focus time:</strong> {insights.total_focus_hours.toFixed(1)} hours
              </div>
            )}
            {insights.completion_rate_trend !== undefined && (
              <div className="insight-item">
                <strong>Chore completion trend:</strong>{' '}
                {insights.completion_rate_trend === 'improving' ? (
                  <span className="trend-up">↑ Improving</span>
                ) : insights.completion_rate_trend === 'declining' ? (
                  <span className="trend-down">↓ Declining</span>
                ) : (
                  <span>Stable</span>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Analytics Snapshots */}
      {snapshots && snapshots.length > 0 && (
        <div className="snapshots-card">
          <h3>Daily Snapshots</h3>
          <div className="snapshots-list">
            {snapshots.slice(0, 7).map(snapshot => (
              <div key={snapshot.id} className="snapshot-item">
                <div className="snapshot-date">
                  {new Date(snapshot.date).toLocaleDateString('en-US', {
                    weekday: 'short',
                    month: 'short',
                    day: 'numeric'
                  })}
                </div>
                <div className="snapshot-stats">
                  <span>Pomodoros: {snapshot.pomodoros_completed || 0}</span>
                  <span>•</span>
                  <span>Todos: {snapshot.todos_completed || 0}</span>
                  <span>•</span>
                  <span>Mood: {snapshot.mood_level ? `${snapshot.mood_level}/5` : 'N/A'}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {(!pomodoro || pomodoro.total_sessions === 0) &&
       (!mood || mood.total_entries === 0) &&
       (!snapshots || snapshots.length === 0) && (
        <div className="empty-state">
          <p>Start using Pomodoro and Mood Journal to see your analytics here!</p>
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

export default AnalyticsDashboard;
