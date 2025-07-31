import React, { useState, useEffect } from 'react';
import { subChoreAPI } from '../services/api';

const SubChoreManager = ({ chore, onSubChoresChange }) => {
  const [subChores, setSubChores] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingSubChore, setEditingSubChore] = useState(null);
  const [formData, setFormData] = useState({ name: '' });

  // Simple, reliable loading function
  const loadSubChores = async () => {
    if (!chore?.id) return;
    
    setLoading(true);
    setError(null);
    
    try {
      console.log('Loading sub-chores for chore:', chore.id);
      const response = await subChoreAPI.getAll(chore.id);
      console.log('Sub-chores loaded:', response.data);
      setSubChores(response.data || []);
      if (onSubChoresChange) {
        onSubChoresChange(response.data || []);
      }
    } catch (err) {
      console.error('Error loading sub-chores:', err);
      setError('Failed to load sub-tasks: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  // Load sub-chores when chore changes
  useEffect(() => {
    if (chore?.id) {
      loadSubChores();
    } else {
      setSubChores([]);
      setError(null);
      setLoading(false);
    }
  }, [chore?.id]);

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
      } else {
        // Add new sub-chore
        const response = await subChoreAPI.create(chore.id, formData);
        updatedSubChores = [...subChores, response.data];
      }
      
      setSubChores(updatedSubChores);
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
            <h4>Sub-tasks for "{chore?.name}"</h4>
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
        <div className="error-message" style={{
          background: '#fee',
          border: '1px solid #faa',
          borderRadius: '4px',
          padding: '10px',
          margin: '10px 0',
          color: '#c33'
        }}>
          <div className="error-text">{error}</div>
          <button 
            onClick={loadSubChores}
            style={{
              background: '#007cba',
              color: 'white',
              border: 'none',
              padding: '5px 10px',
              borderRadius: '3px',
              marginTop: '5px',
              cursor: 'pointer'
            }}
            disabled={loading}
          >
            {loading ? 'Retrying...' : 'Try Again'}
          </button>
        </div>
      )}

      {showAddForm && (
        <div 
          className="sub-chore-form-overlay" 
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}
          onClick={(e) => e.target === e.currentTarget && resetForm()}
        >
          <div 
            className="sub-chore-form modern-modal"
            style={{
              background: 'white',
              borderRadius: '8px',
              padding: '20px',
              minWidth: '400px',
              maxWidth: '90%'
            }}
          >
            <div className="modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3>{editingSubChore ? 'Edit Sub-task' : 'Add New Sub-task'}</h3>
              <button 
                type="button" 
                onClick={resetForm}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '20px',
                  cursor: 'pointer'
                }}
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group" style={{ marginBottom: '15px' }}>
                <label htmlFor="subChoreName" style={{ display: 'block', marginBottom: '5px' }}>Sub-task Description</label>
                <input
                  type="text"
                  id="subChoreName"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  placeholder="e.g., Scrub the bathtub, Clean mirrors..."
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '14px'
                  }}
                  required
                  autoFocus
                />
                <small style={{ color: '#666', fontSize: '12px' }}>Be specific to make it easier to track completion</small>
              </div>
              <div className="modal-footer" style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button 
                  type="button" 
                  onClick={resetForm}
                  style={{
                    padding: '8px 16px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    background: '#f5f5f5',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  style={{
                    padding: '8px 16px',
                    border: 'none',
                    borderRadius: '4px',
                    background: '#007cba',
                    color: 'white',
                    cursor: 'pointer'
                  }}
                >
                  {editingSubChore ? 'Update Sub-task' : 'Add Sub-task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <div 
          className="loading" 
          style={{
            textAlign: 'center',
            padding: '20px',
            background: '#f9f9f9',
            borderRadius: '4px',
            margin: '10px 0'
          }}
        >
          <div style={{ fontSize: '18px', marginBottom: '10px' }}>⏳</div>
          <div>Loading sub-tasks...</div>
        </div>
      ) : (
        <div className="sub-chores-list">
          {subChores.length === 0 ? (
            <div 
              className="no-sub-chores" 
              style={{
                textAlign: 'center',
                padding: '40px',
                background: '#f9f9f9',
                borderRadius: '4px',
                margin: '10px 0'
              }}
            >
              <div style={{ fontSize: '32px', marginBottom: '10px' }}>📝</div>
              <h4>No sub-tasks yet</h4>
              <p>Break this chore into smaller, manageable steps to track progress more easily.</p>
            </div>
          ) : (
            <div>
              <div style={{ marginBottom: '10px', fontSize: '14px', color: '#666' }}>
                <span style={{ 
                  background: '#007cba', 
                  color: 'white', 
                  padding: '2px 8px', 
                  borderRadius: '12px',
                  marginRight: '5px'
                }}>
                  {subChores.length}
                </span>
                sub-task{subChores.length !== 1 ? 's' : ''}
              </div>
              <div className="sub-chores-grid">
                {subChores.map((subChore, index) => (
                  <div 
                    key={subChore.id} 
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '10px',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      margin: '5px 0',
                      background: 'white'
                    }}
                  >
                    <div style={{ 
                      background: '#f0f0f0', 
                      borderRadius: '50%', 
                      width: '24px', 
                      height: '24px', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      marginRight: '10px',
                      fontSize: '12px',
                      fontWeight: 'bold'
                    }}>
                      {index + 1}
                    </div>
                    <div style={{ flex: 1 }}>
                      <span>{subChore.name}</span>
                    </div>
                    <div style={{ display: 'flex', gap: '5px' }}>
                      <button 
                        onClick={() => startEditing(subChore)}
                        style={{
                          padding: '4px 8px',
                          border: '1px solid #ddd',
                          borderRadius: '3px',
                          background: 'white',
                          cursor: 'pointer',
                          fontSize: '12px'
                        }}
                        title="Edit sub-task"
                      >
                        ✏️ Edit
                      </button>
                      <button 
                        onClick={() => deleteSubChore(subChore.id)}
                        style={{
                          padding: '4px 8px',
                          border: '1px solid #faa',
                          borderRadius: '3px',
                          background: '#fee',
                          color: '#c33',
                          cursor: 'pointer',
                          fontSize: '12px'
                        }}
                        title="Delete sub-task"
                      >
                        🗑️ Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SubChoreManager;