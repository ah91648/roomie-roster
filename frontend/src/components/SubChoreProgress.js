import React, { useState, useEffect } from 'react';
import { subChoreAPI } from '../services/api';

const SubChoreProgress = ({ chore, assignment, assignmentIndex, onProgressUpdate }) => {
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [subChores, setSubChores] = useState([]);

  useEffect(() => {
    if (chore && chore.id) {
      loadProgressAndSubChores();
    }
  }, [chore, assignment]);

  const loadProgressAndSubChores = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Load sub-chores for the chore
      const subChoresResponse = await subChoreAPI.getAll(chore.id);
      setSubChores(subChoresResponse.data);
      
      // Load progress for the assignment
      const progressResponse = await subChoreAPI.getProgress(chore.id, assignmentIndex);
      setProgress(progressResponse.data);
      
      if (onProgressUpdate) {
        onProgressUpdate(progressResponse.data);
      }
    } catch (err) {
      setError('Failed to load progress: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const toggleSubChoreCompletion = async (subChoreId) => {
    try {
      setError(null);
      await subChoreAPI.toggle(chore.id, subChoreId, assignmentIndex);
      
      // Reload progress after toggle
      await loadProgressAndSubChores();
    } catch (err) {
      setError('Failed to update sub-chore: ' + (err.response?.data?.error || err.message));
    }
  };

  const getCompletionPercentage = () => {
    if (!progress || progress.total_sub_chores === 0) return 0;
    return progress.completion_percentage;
  };

  const isSubChoreCompleted = (subChoreId) => {
    if (!progress || !progress.sub_chore_statuses) return false;
    return progress.sub_chore_statuses[subChoreId.toString()] === true;
  };

  if (loading) {
    return <div className="sub-chore-progress-loading">Loading progress...</div>;
  }

  if (error) {
    return <div className="sub-chore-progress-error">{error}</div>;
  }

  if (!subChores || subChores.length === 0) {
    return null; // Don't show anything if there are no sub-chores
  }

  const percentage = getCompletionPercentage();
  const isAssignedToCurrentUser = assignment && assignment.roommate_name; // Could be enhanced with user context

  return (
    <div className="sub-chore-progress">
      <div className="progress-header">
        <h4>Task Progress</h4>
        <div className="progress-summary">
          <span className="progress-percentage">{percentage}%</span>
          <span className="progress-fraction">
            ({progress?.completed_sub_chores || 0} of {progress?.total_sub_chores || 0} completed)
          </span>
        </div>
      </div>

      <div className="progress-bar-container">
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ width: `${percentage}%` }}
          ></div>
        </div>
      </div>

      <div className="sub-chores-checklist">
        {subChores.map(subChore => {
          const isCompleted = isSubChoreCompleted(subChore.id);
          return (
            <div key={subChore.id} className={`sub-chore-item ${isCompleted ? 'completed' : ''}`}>
              <label className="sub-chore-checkbox">
                <input
                  type="checkbox"
                  checked={isCompleted}
                  onChange={() => toggleSubChoreCompletion(subChore.id)}
                  disabled={loading}
                />
                <span className="checkmark"></span>
                <span className={`sub-chore-text ${isCompleted ? 'completed-text' : ''}`}>
                  {subChore.name}
                </span>
              </label>
            </div>
          );
        })}
      </div>

      {assignment && (
        <div className="assignment-info">
          <small>
            Assigned to: <strong>{assignment.roommate_name}</strong>
            {assignment.due_date && (
              <span> • Due: {new Date(assignment.due_date).toLocaleDateString()}</span>
            )}
          </small>
        </div>
      )}
    </div>
  );
};

export default SubChoreProgress;