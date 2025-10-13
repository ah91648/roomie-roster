import React, { useState, useEffect, useCallback, useRef } from 'react';
import { subChoreAPI } from '../services/api';

// Helper function to create AbortSignal with timeout (Context7 best practice)
function createTimeoutAbortSignal(timeoutMs) {
  const abortController = new AbortController();
  const timeoutId = setTimeout(() => abortController.abort(), timeoutMs || 0);
  
  // Store timeout ID for cleanup
  abortController.timeoutId = timeoutId;
  return abortController;
}

const SubChoreManager = ({ chore, onSubChoresChange }) => {
  const [subChores, setSubChores] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingSubChore, setEditingSubChore] = useState(null);
  const [formData, setFormData] = useState({ name: '' });
  const [retryCount, setRetryCount] = useState(0);
  
  // Refs to prevent stale closures and race conditions
  const mountedRef = useRef(true);
  const currentRequestRef = useRef(null);
  const loadingTimeoutRef = useRef(null);
  const loadingStateRef = useRef(false);
  const onSubChoresChangeRef = useRef(onSubChoresChange);

  // Update the ref when the callback changes
  useEffect(() => {
    onSubChoresChangeRef.current = onSubChoresChange;
  }, [onSubChoresChange]);

  // Stable callback to prevent useEffect re-runs
  const stableOnSubChoresChange = useCallback((subChores) => {
    if (onSubChoresChangeRef.current && mountedRef.current) {
      onSubChoresChangeRef.current(subChores);
    }
  }, []); // No dependencies to prevent re-renders

  // Load sub-chores function with comprehensive error handling
  const loadSubChores = useCallback(async (choreId, attempt = 0) => {
    if (!mountedRef.current || !choreId) return;

    // Cancel any existing request
    if (currentRequestRef.current) {
      currentRequestRef.current.abort();
      if (currentRequestRef.current.timeoutId) {
        clearTimeout(currentRequestRef.current.timeoutId);
      }
    }

    // Clear any existing loading timeout
    if (loadingTimeoutRef.current) {
      clearTimeout(loadingTimeoutRef.current);
      loadingTimeoutRef.current = null;
    }

    // Development logging
    if (process.env.NODE_ENV === 'development') {
      console.log(`[SubChoreManager] Loading sub-chores for chore ${choreId}, attempt ${attempt + 1}`);
    }

    try {
      if (mountedRef.current) {
        setLoading(true);
        loadingStateRef.current = true;
        setError(null);
      }

      // Create abort controller with timeout
      const abortController = createTimeoutAbortSignal(8000); // 8 second API timeout
      currentRequestRef.current = abortController;

      // Set a loading timeout fallback (12 seconds - longer than API timeout)
      loadingTimeoutRef.current = setTimeout(() => {
        if (mountedRef.current && loadingStateRef.current) {
          console.warn('[SubChoreManager] Loading timeout reached');
          setError('Loading sub-tasks is taking longer than expected. Please try refreshing the page.');
          setLoading(false);
          loadingStateRef.current = false;
        }
      }, 12000);

      const response = await subChoreAPI.getAll(choreId, {
        signal: abortController.signal,
        timeout: 7000 // Axios timeout (shorter than AbortController timeout)
      });

      // Clear timeouts on success
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
        loadingTimeoutRef.current = null;
      }
      if (abortController.timeoutId) {
        clearTimeout(abortController.timeoutId);
      }

      // Update state only if component is still mounted
      if (mountedRef.current) {
        setSubChores(response.data);
        setRetryCount(0); // Reset retry count on success
        loadingStateRef.current = false;
        stableOnSubChoresChange(response.data);
        
        if (process.env.NODE_ENV === 'development') {
          console.log(`[SubChoreManager] Successfully loaded ${response.data.length} sub-chores`);
        }
      }
    } catch (err) {
      // Clear timeouts on error
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
        loadingTimeoutRef.current = null;
      }

      if (!mountedRef.current) return;

      if (process.env.NODE_ENV === 'development') {
        console.error('[SubChoreManager] Error loading sub-chores:', err);
      }

      let errorMessage = 'Failed to load sub-tasks.';
      
      if (err.name === 'AbortError') {
        errorMessage = 'Request was cancelled. This might happen if the request took too long.';
      } else if (err.code === 'ECONNABORTED' || err.message.includes('timeout')) {
        errorMessage = 'Request timed out. Please check your connection and try again.';
      } else if (err.response?.status >= 500) {
        errorMessage = 'Server error occurred. Please try again in a moment.';
      } else if (err.response?.status === 404) {
        errorMessage = 'Sub-tasks not found for this chore.';
      } else if (err.response?.data?.error) {
        errorMessage = `Error: ${err.response.data.error}`;
      } else if (err.message) {
        errorMessage = `Network error: ${err.message}`;
      }

      setError(errorMessage);
      setRetryCount(prev => prev + 1);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
        loadingStateRef.current = false;
      }
      currentRequestRef.current = null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Removed stableOnSubChoresChange dependency since it's now stable

  // Effect to load sub-chores when chore changes
  useEffect(() => {
    if (chore?.id) {
      loadSubChores(chore.id);
    } else {
      // Clear data when no chore
      setSubChores([]);
      setError(null);
      setLoading(false);
      loadingStateRef.current = false;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chore?.id]); // Removed loadSubChores dependency to prevent infinite re-renders

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;
    
    return () => {
      mountedRef.current = false;
      
      // Cancel any pending request
      if (currentRequestRef.current) {
        currentRequestRef.current.abort();
        if (currentRequestRef.current.timeoutId) {
          clearTimeout(currentRequestRef.current.timeoutId);
        }
      }
      
      // Clear loading timeout
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
        loadingTimeoutRef.current = null;
      }
    };
  }, []);

  // Retry function for manual retries
  const retryLoadSubChores = useCallback(() => {
    if (chore?.id) {
      loadSubChores(chore.id, retryCount);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chore?.id, retryCount]); // Removed loadSubChores dependency

  const resetForm = () => {
    setFormData({ name: '' });
    setEditingSubChore(null);
    setShowAddForm(false);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) return;

    try {
      setError(null);
      let updatedSubChores;
      
      if (editingSubChore) {
        // Update existing sub-chore
        const response = await subChoreAPI.update(chore.id, editingSubChore.id, formData);
        updatedSubChores = subChores.map(sc => sc.id === editingSubChore.id ? response.data : sc);
        setSubChores(updatedSubChores);
      } else {
        // Add new sub-chore
        const response = await subChoreAPI.create(chore.id, formData);
        updatedSubChores = [...subChores, response.data];
        setSubChores(updatedSubChores);
      }
      
      // Use the calculated updatedSubChores for the callback
      if (onSubChoresChange) {
        onSubChoresChange(updatedSubChores);
      }
      resetForm();
    } catch (err) {
      setError('Failed to save sub-chore: ' + (err.response?.data?.error || err.message));
    }
  };

  const deleteSubChore = async (id) => {
    if (!window.confirm('Are you sure you want to delete this sub-chore?')) return;

    try {
      setError(null);
      await subChoreAPI.delete(chore.id, id);
      const updatedSubChores = subChores.filter(sc => sc.id !== id);
      setSubChores(updatedSubChores);
      if (onSubChoresChange) {
        onSubChoresChange(updatedSubChores);
      }
    } catch (err) {
      setError('Failed to delete sub-chore: ' + (err.response?.data?.error || err.message));
    }
  };

  const startEditing = (subChore) => {
    setFormData({ name: subChore.name });
    setEditingSubChore(subChore);
    setShowAddForm(true);
  };

  return (
    <div className="sub-chore-manager">
      <div className="sub-chore-header modern-header">
        <div className="header-content">
          <div className="header-icon">📋</div>
          <div className="header-text">
            <h4>Sub-tasks</h4>
            <span className="chore-name">"{chore?.name}"</span>
          </div>
        </div>
        <button 
          onClick={() => setShowAddForm(true)}
          className="btn-add-sub-chore modern-add-btn"
          disabled={loading}
        >
          <span className="btn-icon">➕</span>
          <span className="btn-text">Add Sub-task</span>
        </button>
      </div>

      {error && (
        <div className="error-message">
          <div className="error-text">{error}</div>
          <button 
            onClick={retryLoadSubChores}
            className="btn-retry"
            disabled={loading}
          >
            {loading ? 'Retrying...' : 'Try Again'}
          </button>
          {retryCount > 2 && (
            <div className="error-help">
              <small>If this problem persists, try refreshing the page or check your internet connection.</small>
            </div>
          )}
        </div>
      )}

      {showAddForm && (
        <div className="sub-chore-form-overlay" onClick={(e) => e.target === e.currentTarget && resetForm()}>
          <div className="sub-chore-form modern-modal">
            <div className="modal-header">
              <div className="modal-title">
                <span className="modal-icon">
                  {editingSubChore ? '✏️' : '➕'}
                </span>
                <h3>{editingSubChore ? 'Edit Sub-task' : 'Add New Sub-task'}</h3>
              </div>
              <button 
                type="button" 
                onClick={resetForm}
                className="modal-close-button"
                title="Close"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-group modern-input-group">
                  <label htmlFor="subChoreName">Sub-task Description</label>
                  <div className="input-wrapper">
                    <input
                      type="text"
                      id="subChoreName"
                      name="name"
                      value={formData.name}
                      onChange={handleInputChange}
                      placeholder="e.g., Scrub the bathtub, Clean mirrors..."
                      className="modern-input"
                      required
                      autoFocus
                    />
                  </div>
                  <small className="input-help">Be specific to make it easier to track completion</small>
                </div>
              </div>
              <div className="modal-footer">
                <button 
                  type="button" 
                  onClick={resetForm}
                  className="btn-cancel"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-save">
                  <span className="btn-icon">
                    {editingSubChore ? '💾' : '➕'}
                  </span>
                  {editingSubChore ? 'Update Sub-task' : 'Add Sub-task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <div className="loading">
          <div className="loading-spinner">⏳</div>
          <div className="loading-text">
            Loading sub-tasks...
            {retryCount > 0 && <span className="retry-indicator"> (Attempt {retryCount + 1})</span>}
          </div>
          <div className="loading-progress">
            <div className="progress-bar">
              <div className="progress-fill"></div>
            </div>
            <small>This usually takes a few seconds</small>
          </div>
        </div>
      ) : (
        <div className="sub-chores-list">
          {subChores.length === 0 ? (
            <div className="no-sub-chores modern-empty-state">
              <div className="empty-state-icon">📝</div>
              <div className="empty-state-text">
                <h4>No sub-tasks yet</h4>
                <p>Break this chore into smaller, manageable steps to track progress more easily.</p>
              </div>
            </div>
          ) : (
            <div className="sub-chores-grid">
              <div className="sub-chores-count">
                <span className="count-badge">{subChores.length}</span>
                <span className="count-label">sub-task{subChores.length !== 1 ? 's' : ''}</span>
              </div>
              <ul className="sub-chores modern-list">
                {subChores.map((subChore, index) => (
                  <li key={subChore.id} className="sub-chore-item modern-item">
                    <div className="item-index">{index + 1}</div>
                    <div className="sub-chore-content">
                      <span className="sub-chore-name">{subChore.name}</span>
                    </div>
                    <div className="sub-chore-actions">
                      <button 
                        onClick={() => startEditing(subChore)}
                        className="btn-edit modern-action-btn"
                        title="Edit sub-task"
                      >
                        <span className="btn-icon">✏️</span>
                        <span className="btn-text">Edit</span>
                      </button>
                      <button 
                        onClick={() => deleteSubChore(subChore.id)}
                        className="btn-delete modern-action-btn danger"
                        title="Delete sub-task"
                      >
                        <span className="btn-icon">🗑️</span>
                        <span className="btn-text">Delete</span>
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SubChoreManager;