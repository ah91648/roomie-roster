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
        onSubChoresChange(editingSubChore 
          ? subChores.map(sc => sc.id === editingSubChore.id ? formData : sc)
          : [...subChores, formData]
        );
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
      <div className="sub-chore-header">
        <h4>Sub-tasks for "{chore?.name}"</h4>
        <button 
          onClick={() => setShowAddForm(true)}
          className="btn-add-sub-chore"
        >
          + Add Sub-task
        </button>
      </div>

      {error && (
        <div className="error-message">{error}</div>
      )}

      {showAddForm && (
        <div className="sub-chore-form-overlay">
          <div className="sub-chore-form">
            <h3>{editingSubChore ? 'Edit Sub-task' : 'Add New Sub-task'}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="subChoreName">Sub-task Name:</label>
                <input
                  type="text"
                  id="subChoreName"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  placeholder="Enter sub-task description..."
                  required
                />
              </div>
              <div className="form-actions">
                <button type="submit" className="btn-primary">
                  {editingSubChore ? 'Update' : 'Add'} Sub-task
                </button>
                <button 
                  type="button" 
                  onClick={resetForm}
                  className="btn-secondary"
                >
                  Cancel
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
            <div className="no-sub-chores">
              No sub-tasks defined. Click "Add Sub-task" to break this chore into smaller steps.
            </div>
          ) : (
            <ul className="sub-chores">
              {subChores.map(subChore => (
                <li key={subChore.id} className="sub-chore-item">
                  <div className="sub-chore-content">
                    <span className="sub-chore-name">{subChore.name}</span>
                  </div>
                  <div className="sub-chore-actions">
                    <button 
                      onClick={() => startEditing(subChore)}
                      className="btn-edit"
                      title="Edit sub-task"
                    >
                      ✏️
                    </button>
                    <button 
                      onClick={() => deleteSubChore(subChore.id)}
                      className="btn-delete"
                      title="Delete sub-task"
                    >
                      🗑️
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};

export default SubChoreManager;