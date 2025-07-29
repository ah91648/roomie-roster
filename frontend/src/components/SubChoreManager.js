import React, { useState, useEffect } from 'react';
import { subChoreAPI } from '../services/api';

const SubChoreManager = ({ chore, onSubChoresChange }) => {
  const [subChores, setSubChores] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingSubChore, setEditingSubChore] = useState(null);
  const [formData, setFormData] = useState({ name: '' });

  useEffect(() => {
    if (chore && chore.id) {
      loadSubChores();
    }
  }, [chore]);

  const loadSubChores = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await subChoreAPI.getAll(chore.id);
      setSubChores(response.data);
      if (onSubChoresChange) {
        onSubChoresChange(response.data);
      }
    } catch (err) {
      setError('Failed to load sub-chores: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

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
      if (editingSubChore) {
        // Update existing sub-chore
        const response = await subChoreAPI.update(chore.id, editingSubChore.id, formData);
        setSubChores(subChores.map(sc => sc.id === editingSubChore.id ? response.data : sc));
      } else {
        // Add new sub-chore
        const response = await subChoreAPI.create(chore.id, formData);
        setSubChores([...subChores, response.data]);
      }
      if (onSubChoresChange) {
        const updatedSubChores = editingSubChore 
          ? subChores.map(sc => sc.id === editingSubChore.id ? response.data : sc)
          : [...subChores, response.data];
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
        <div className="error-message">{error}</div>
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
        <div className="loading">Loading sub-tasks...</div>
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