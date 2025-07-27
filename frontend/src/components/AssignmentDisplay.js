import React, { useState, useEffect } from 'react';
import { assignmentAPI, stateAPI } from '../services/api';
import SubChoreProgress from './SubChoreProgress';

const AssignmentDisplay = () => {
  const [assignments, setAssignments] = useState([]);
  const [groupedAssignments, setGroupedAssignments] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastAssignmentDate, setLastAssignmentDate] = useState(null);
  const [isAssigning, setIsAssigning] = useState(false);

  useEffect(() => {
    loadCurrentAssignments();
    loadAppState();
  }, []);

  const loadCurrentAssignments = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await assignmentAPI.getCurrent();
      setAssignments(response.data.assignments || []);
      setGroupedAssignments(response.data.grouped_by_roommate || {});
    } catch (err) {
      setError('Failed to load assignments: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const loadAppState = async () => {
    try {
      const response = await stateAPI.get();
      setLastAssignmentDate(response.data.last_run_date);
    } catch (err) {
      console.error('Failed to load app state:', err);
    }
  };

  const assignChores = async () => {
    setIsAssigning(true);
    try {
      setError(null);
      const response = await assignmentAPI.assignChores();
      setAssignments(response.data.assignments || []);
      
      // Group assignments by roommate
      const grouped = {};
      response.data.assignments.forEach(assignment => {
        const roommateName = assignment.roommate_name;
        if (!grouped[roommateName]) {
          grouped[roommateName] = [];
        }
        grouped[roommateName].push(assignment);
      });
      setGroupedAssignments(grouped);
      setLastAssignmentDate(new Date().toISOString());
      
    } catch (err) {
      setError('Failed to assign chores: ' + (err.response?.data?.error || err.message));
    } finally {
      setIsAssigning(false);
    }
  };

  const resetCycle = async () => {
    if (!window.confirm('Are you sure you want to reset the assignment cycle? This will reset all roommate points to 0.')) {
      return;
    }

    try {
      setError(null);
      await assignmentAPI.resetCycle();
      // Reload assignments after reset
      await loadCurrentAssignments();
    } catch (err) {
      setError('Failed to reset cycle: ' + (err.response?.data?.error || err.message));
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' at ' + date.toLocaleTimeString();
  };

  const formatDueDate = (dueDateString) => {
    const dueDate = new Date(dueDateString);
    const now = new Date();
    const diffTime = dueDate - now;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) {
      return `Overdue by ${Math.abs(diffDays)} day(s)`;
    } else if (diffDays === 0) {
      return 'Due today';
    } else if (diffDays === 1) {
      return 'Due tomorrow';
    } else {
      return `Due in ${diffDays} day(s)`;
    }
  };

  const getTypeIcon = (type) => {
    return type === 'predefined' ? '🔄' : '🎲';
  };

  if (loading) {
    return <div className="loading">Loading assignments...</div>;
  }

  return (
    <div className="assignment-display">
      <div className="header">
        <h2>Chore Assignments</h2>
        <div className="header-actions">
          <button
            onClick={assignChores}
            disabled={isAssigning}
            className="button primary large"
          >
            {isAssigning ? 'Assigning...' : 'Assign Chores'}
          </button>
          <button
            onClick={resetCycle}
            className="button secondary"
          >
            Reset Cycle
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="assignment-info">
        <p className="last-assignment">
          Last Assignment: <strong>{formatDate(lastAssignmentDate)}</strong>
        </p>
        <p className="assignment-count">
          Current Assignments: <strong>{assignments.length}</strong>
        </p>
      </div>

      {assignments.length === 0 ? (
        <div className="empty-state">
          <h3>No chores assigned yet</h3>
          <p>Click "Assign Chores" to generate assignments for your roommates.</p>
          <p>Make sure you have both chores and roommates set up first!</p>
        </div>
      ) : (
        <div className="assignments-container">
          {/* Grouped by Roommate View */}
          <div className="assignments-by-roommate">
            <h3>Assignments by Roommate</h3>
            {Object.keys(groupedAssignments).map(roommateName => (
              <div key={roommateName} className="roommate-assignments">
                <h4 className="roommate-header">{roommateName}'s Chores</h4>
                <div className="chore-assignments">
                  {groupedAssignments[roommateName].map((assignment, index) => (
                    <div key={index} className="assignment-card">
                      <div className="assignment-header">
                        <span className="chore-name">{assignment.chore_name}</span>
                        <span className="type-icon" title={assignment.type}>
                          {getTypeIcon(assignment.type)}
                        </span>
                      </div>
                      <div className="assignment-details">
                        <div className="detail">
                          <span className="label">Frequency:</span>
                          <span className="value">{assignment.frequency}</span>
                        </div>
                        <div className="detail">
                          <span className="label">Points:</span>
                          <span className="value">{assignment.points}</span>
                        </div>
                        <div className="detail">
                          <span className="label">Due:</span>
                          <span className={`value due-date ${formatDueDate(assignment.due_date).includes('Overdue') ? 'overdue' : ''}`}>
                            {formatDueDate(assignment.due_date)}
                          </span>
                        </div>
                      </div>
                      
                      {/* Sub-chore progress */}
                      <SubChoreProgress 
                        chore={{
                          id: assignment.chore_id,
                          name: assignment.chore_name
                        }}
                        assignment={assignment}
                        assignmentIndex={assignments.findIndex(a => 
                          a.chore_id === assignment.chore_id && 
                          a.roommate_id === assignment.roommate_id
                        )}
                        onProgressUpdate={(progress) => {
                          // Handle progress updates if needed for UI feedback
                          console.log(`Progress for ${assignment.chore_name}:`, progress);
                        }}
                      />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Summary Statistics */}
          <div className="assignment-summary">
            <h3>Assignment Summary</h3>
            <div className="summary-stats">
              {Object.keys(groupedAssignments).map(roommateName => {
                const roommateAssignments = groupedAssignments[roommateName];
                const totalPoints = roommateAssignments.reduce((sum, assignment) => sum + assignment.points, 0);
                
                return (
                  <div key={roommateName} className="roommate-summary">
                    <span className="roommate-name">{roommateName}</span>
                    <span className="chore-count">{roommateAssignments.length} chore(s)</span>
                    <span className="total-points">{totalPoints} points</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Assignment Instructions */}
      <div className="instructions">
        <h3>How Assignments Work</h3>
        <div className="instruction-grid">
          <div className="instruction-item">
            <span className="icon">🔄</span>
            <div>
              <strong>Predefined Chores</strong>
              <p>Rotate between roommates in order</p>
            </div>
          </div>
          <div className="instruction-item">
            <span className="icon">🎲</span>
            <div>
              <strong>Random Chores</strong>
              <p>Assigned using weighted selection based on current cycle points</p>
            </div>
          </div>
          <div className="instruction-item">
            <span className="icon">⚖️</span>
            <div>
              <strong>Fair Distribution</strong>
              <p>Points help ensure balanced workload across all roommates</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AssignmentDisplay;