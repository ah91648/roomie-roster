import React, { useState, useEffect } from 'react';
import { roommateAPI } from '../services/api';

const RoommateManager = () => {
  const [roommates, setRoommates] = useState([]);
  const [newRoommateName, setNewRoommateName] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editingName, setEditingName] = useState('');

  useEffect(() => {
    loadRoommates();
  }, []);

  const loadRoommates = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await roommateAPI.getAll();
      setRoommates(response.data);
    } catch (err) {
      setError('Failed to load roommates: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const addRoommate = async (e) => {
    e.preventDefault();
    if (!newRoommateName.trim()) return;

    try {
      setError(null);
      const response = await roommateAPI.create({ name: newRoommateName.trim() });
      setRoommates([...roommates, response.data]);
      setNewRoommateName('');
    } catch (err) {
      setError('Failed to add roommate: ' + (err.response?.data?.error || err.message));
    }
  };

  const deleteRoommate = async (id) => {
    if (!window.confirm('Are you sure you want to delete this roommate?')) return;

    try {
      setError(null);
      await roommateAPI.delete(id);
      setRoommates(roommates.filter(r => r.id !== id));
    } catch (err) {
      setError('Failed to delete roommate: ' + (err.response?.data?.error || err.message));
    }
  };

  const startEditing = (roommate) => {
    setEditingId(roommate.id);
    setEditingName(roommate.name);
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditingName('');
  };

  const saveEdit = async (id) => {
    if (!editingName.trim()) return;

    try {
      setError(null);
      const response = await roommateAPI.update(id, { name: editingName.trim() });
      setRoommates(roommates.map(r => r.id === id ? response.data : r));
      setEditingId(null);
      setEditingName('');
    } catch (err) {
      setError('Failed to update roommate: ' + (err.response?.data?.error || err.message));
    }
  };

  if (loading) {
    return <div className="loading">Loading roommates...</div>;
  }

  return (
    <div className="roommate-manager">
      <h2>Manage Roommates</h2>
      
      {error && <div className="error">{error}</div>}

      {/* Add new roommate form */}
      <form onSubmit={addRoommate} className="add-form">
        <div className="form-group">
          <input
            type="text"
            value={newRoommateName}
            onChange={(e) => setNewRoommateName(e.target.value)}
            placeholder="Enter roommate name"
            className="input"
          />
          <button type="submit" className="button primary">
            Add Roommate
          </button>
        </div>
      </form>

      {/* Roommates list */}
      <div className="roommates-list">
        {roommates.length === 0 ? (
          <p className="empty-state">No roommates added yet. Add your first roommate above!</p>
        ) : (
          <div className="roommates-grid">
            {roommates.map((roommate) => (
              <div key={roommate.id} className="roommate-card">
                {editingId === roommate.id ? (
                  <div className="edit-mode">
                    <input
                      type="text"
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      className="input"
                      autoFocus
                    />
                    <div className="edit-actions">
                      <button
                        onClick={() => saveEdit(roommate.id)}
                        className="button small primary"
                      >
                        Save
                      </button>
                      <button
                        onClick={cancelEditing}
                        className="button small secondary"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="view-mode">
                    <h3 className="roommate-name">{roommate.name}</h3>
                    <p className="roommate-points">
                      Current Cycle Points: <strong>{roommate.current_cycle_points || 0}</strong>
                    </p>
                    <div className="roommate-actions">
                      <button
                        onClick={() => startEditing(roommate)}
                        className="button small secondary"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => deleteRoommate(roommate.id)}
                        className="button small danger"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="stats">
        <p>Total Roommates: <strong>{roommates.length}</strong></p>
      </div>
    </div>
  );
};

export default RoommateManager;