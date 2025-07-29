import React, { useState, useEffect } from 'react';
import { choreAPI } from '../services/api';
import SubChoreManager from './SubChoreManager';

const ChoreManager = () => {
  const [chores, setChores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingChore, setEditingChore] = useState(null);
  const [showingSubChores, setShowingSubChores] = useState(null);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    frequency: 'weekly',
    type: 'random',
    points: 5
  });

  useEffect(() => {
    loadChores();
  }, []);

  const loadChores = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await choreAPI.getAll();
      setChores(response.data);
    } catch (err) {
      setError('Failed to load chores: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      frequency: 'weekly',
      type: 'random',
      points: 5
    });
    setEditingChore(null);
    setShowAddForm(false);
  };

  const handleInputChange = (e) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? parseInt(value) || 0 : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) return;

    try {
      setError(null);
      if (editingChore) {
        // Update existing chore
        const response = await choreAPI.update(editingChore.id, formData);
        setChores(chores.map(c => c.id === editingChore.id ? response.data : c));
      } else {
        // Add new chore
        const response = await choreAPI.create(formData);
        setChores([...chores, response.data]);
      }
      resetForm();
    } catch (err) {
      setError('Failed to save chore: ' + (err.response?.data?.error || err.message));
    }
  };

  const deleteChore = async (id) => {
    if (!window.confirm('Are you sure you want to delete this chore?')) return;

    try {
      setError(null);
      setLoading(true);
      await choreAPI.delete(id);
      // Force a complete reload to ensure UI is in sync
      await loadChores();
    } catch (err) {
      setError('Failed to delete chore: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const startEditing = (chore) => {
    setFormData({
      name: chore.name,
      frequency: chore.frequency,
      type: chore.type,
      points: chore.points
    });
    setEditingChore(chore);
    setShowAddForm(true);
  };

  const getFrequencyLabel = (frequency) => {
    switch (frequency) {
      case 'daily': return 'Daily';
      case 'weekly': return 'Weekly';
      case 'bi-weekly': return 'Bi-weekly';
      default: return frequency;
    }
  };

  const getTypeLabel = (type) => {
    return type === 'predefined' ? 'Predefined Rotation' : 'Random Assignment';
  };

  const toggleSubChores = (choreId) => {
    setShowingSubChores(showingSubChores === choreId ? null : choreId);
  };

  const handleSubChoresChange = (choreId, subChores) => {
    // Update the chore with new sub-chores (for UI consistency)
    setChores(chores.map(chore => 
      chore.id === choreId 
        ? { ...chore, sub_chores: subChores }
        : chore
    ));
  };

  if (loading) {
    return <div className="loading">Loading chores...</div>;
  }

  return (
    <div className="chore-manager">
      <div className="header">
        <h2>Manage Chores</h2>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="button primary"
        >
          {showAddForm ? 'Cancel' : 'Add New Chore'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {/* Add/Edit chore form */}
      {showAddForm && (
        <form onSubmit={handleSubmit} className="chore-form">
          <h3>{editingChore ? 'Edit Chore' : 'Add New Chore'}</h3>
          
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="name">Chore Name *</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                placeholder="e.g., Clean Bathroom"
                className="input"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="frequency">Frequency *</label>
              <select
                id="frequency"
                name="frequency"
                value={formData.frequency}
                onChange={handleInputChange}
                className="input"
                required
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="bi-weekly">Bi-weekly</option>
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="type">Assignment Type *</label>
              <select
                id="type"
                name="type"
                value={formData.type}
                onChange={handleInputChange}
                className="input"
                required
              >
                <option value="random">Random Assignment</option>
                <option value="predefined">Predefined Rotation</option>
              </select>
              <small className="help-text">
                Random: Weighted by current points. Predefined: Round-robin rotation.
              </small>
            </div>

            <div className="form-group">
              <label htmlFor="points">Points (Difficulty) *</label>
              <input
                type="number"
                id="points"
                name="points"
                value={formData.points}
                onChange={handleInputChange}
                min="1"
                max="20"
                className="input"
                required
              />
              <small className="help-text">1-20 points (higher = more difficult)</small>
            </div>
          </div>

          <div className="form-actions">
            <button type="submit" className="button primary">
              {editingChore ? 'Update Chore' : 'Add Chore'}
            </button>
            <button type="button" onClick={resetForm} className="button secondary">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Chores list */}
      <div className="chores-list">
        {chores.length === 0 ? (
          <p className="empty-state">No chores added yet. Add your first chore above!</p>
        ) : (
          <div className="chores-grid">
            {chores.map((chore) => (
              <div key={chore.id} className={`chore-card ${chore.type}`}>
                <div className="chore-header">
                  <h3 className="chore-name">{chore.name}</h3>
                  <span className={`chore-type-badge ${chore.type}`}>
                    {getTypeLabel(chore.type)}
                  </span>
                </div>
                
                <div className="chore-details">
                  <div className="detail-item">
                    <span className="label">Frequency:</span>
                    <span className="value">{getFrequencyLabel(chore.frequency)}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Points:</span>
                    <span className="value">{chore.points}</span>
                  </div>
                </div>

                <div className="chore-actions">
                  <button
                    onClick={() => toggleSubChores(chore.id)}
                    className="button small secondary"
                  >
                    {showingSubChores === chore.id ? 'Hide Sub-tasks' : 'Manage Sub-tasks'}
                  </button>
                  <button
                    onClick={() => startEditing(chore)}
                    className="button small secondary"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => deleteChore(chore.id)}
                    className="button small danger"
                  >
                    Delete
                  </button>
                </div>

                {/* Sub-chore management */}
                {showingSubChores === chore.id && (
                  <SubChoreManager 
                    chore={chore}
                    onSubChoresChange={(subChores) => handleSubChoresChange(chore.id, subChores)}
                  />
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="stats">
        <p>Total Chores: <strong>{chores.length}</strong></p>
        <p>
          Predefined: <strong>{chores.filter(c => c.type === 'predefined').length}</strong>,
          Random: <strong>{chores.filter(c => c.type === 'random').length}</strong>
        </p>
      </div>
    </div>
  );
};

export default ChoreManager;