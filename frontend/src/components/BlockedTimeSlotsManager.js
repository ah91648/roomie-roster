import React, { useState, useEffect } from 'react';
import { blockedTimeSlotsAPI } from '../services/api';

const BlockedTimeSlotsManager = () => {
  const [blockedSlots, setBlockedSlots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingSlot, setEditingSlot] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);

  // Form state
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    time_slot: '',
    reason: '',
    sync_to_calendars: true
  });

  const timeSlots = [
    '06:00-08:00', '08:00-10:00', '10:00-12:00', '12:00-14:00',
    '14:00-16:00', '16:00-18:00', '18:00-20:00', '20:00-22:00'
  ];

  useEffect(() => {
    loadBlockedSlots();
  }, []);

  const loadBlockedSlots = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await blockedTimeSlotsAPI.getAll();
      setBlockedSlots(response.data);
    } catch (err) {
      setError('Failed to load blocked time slots: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.date || !formData.time_slot || !formData.reason) {
      setError('Please fill in all required fields');
      return;
    }

    try {
      setError(null);
      
      if (editingSlot) {
        // Update existing slot
        const response = await blockedTimeSlotsAPI.update(editingSlot.id, formData);
        setBlockedSlots(blockedSlots.map(slot => 
          slot.id === editingSlot.id ? response.data : slot
        ));
      } else {
        // Create new slot
        const response = await blockedTimeSlotsAPI.create(formData);
        setBlockedSlots([...blockedSlots, response.data]);
      }
      
      resetForm();
    } catch (err) {
      if (err.response?.status === 409) {
        setError(`Time slot conflict: ${err.response.data.error}`);
      } else {
        setError('Failed to save blocked slot: ' + (err.response?.data?.error || err.message));
      }
    }
  };

  const handleEdit = (slot) => {
    setEditingSlot(slot);
    setFormData({
      date: slot.date,
      time_slot: slot.time_slot,
      reason: slot.reason,
      sync_to_calendars: slot.sync_to_calendars !== false
    });
    setShowAddForm(true);
  };

  const handleDelete = async (slotId) => {
    if (!window.confirm('Are you sure you want to unblock this time slot?')) return;

    try {
      setError(null);
      await blockedTimeSlotsAPI.delete(slotId);
      setBlockedSlots(blockedSlots.filter(slot => slot.id !== slotId));
    } catch (err) {
      setError('Failed to delete blocked slot: ' + (err.response?.data?.error || err.message));
    }
  };

  const resetForm = () => {
    setFormData({
      date: new Date().toISOString().split('T')[0],
      time_slot: '',
      reason: '',
      sync_to_calendars: true
    });
    setEditingSlot(null);
    setShowAddForm(false);
  };

  const getFilteredSlots = () => {
    return blockedSlots.filter(slot => {
      if (selectedDate && slot.date !== selectedDate) return false;
      return true;
    });
  };

  if (loading) {
    return <div className="loading">Loading blocked time slots...</div>;
  }

  const filteredSlots = getFilteredSlots();

  return (
    <div className="blocked-time-slots-manager">
      <div className="header">
        <h3>🚫 Blocked Time Slots</h3>
        <p className="text-small">
          Block laundry time slots to prevent booking. Blocked slots will be synced to all users' calendars.
        </p>
        <div className="header-actions">
          <button 
            onClick={() => setShowAddForm(!showAddForm)} 
            className="button primary"
          >
            {showAddForm ? 'Cancel' : 'Block Time Slot'}
          </button>
          <button onClick={loadBlockedSlots} className="button secondary">
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {/* Date Filter */}
      <div className="filters">
        <div className="form-group">
          <label>Filter by Date:</label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="input"
          />
        </div>
      </div>

      {/* Add/Edit Form */}
      {showAddForm && (
        <div className="blocked-slot-form">
          <h4>{editingSlot ? 'Edit Blocked Time Slot' : 'Block New Time Slot'}</h4>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label>Date *</label>
                <input
                  type="date"
                  name="date"
                  value={formData.date}
                  onChange={handleInputChange}
                  required
                  className="input"
                />
              </div>
              <div className="form-group">
                <label>Time Slot *</label>
                <select
                  name="time_slot"
                  value={formData.time_slot}
                  onChange={handleInputChange}
                  required
                  className="input"
                >
                  <option value="">Select Time Slot</option>
                  {timeSlots.map(slot => (
                    <option key={slot} value={slot}>{slot}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label>Reason for Blocking *</label>
              <input
                type="text"
                name="reason"
                value={formData.reason}
                onChange={handleInputChange}
                placeholder="e.g., Maintenance, Deep cleaning, etc."
                required
                className="input"
              />
            </div>

            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  name="sync_to_calendars"
                  checked={formData.sync_to_calendars}
                  onChange={handleInputChange}
                />
                Sync to all users' calendars
              </label>
              <p className="text-small">
                When enabled, this blocked time slot will appear in all users' Google Calendars
              </p>
            </div>

            <div className="form-actions">
              <button type="submit" className="button primary">
                {editingSlot ? 'Update Block' : 'Block Time Slot'}
              </button>
              <button type="button" onClick={resetForm} className="button secondary">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Blocked Slots List */}
      <div className="blocked-slots-list">
        <h4>
          Blocked Time Slots
          {selectedDate && ` for ${new Date(selectedDate).toLocaleDateString()}`}
          ({filteredSlots.length} blocked)
        </h4>
        
        {filteredSlots.length === 0 ? (
          <div className="empty-state">
            {selectedDate 
              ? `No blocked time slots found for ${new Date(selectedDate).toLocaleDateString()}.`
              : 'No blocked time slots found.'
            } {showAddForm ? 'Fill out the form above to block a time slot.' : 'Click "Block Time Slot" to get started!'}
          </div>
        ) : (
          <div className="items-grid">
            {filteredSlots.map(slot => (
              <div key={slot.id} className="item-card blocked-slot-card">
                <div className="card-header">
                  <h5>🚫 {slot.time_slot}</h5>
                  <span className="status-badge blocked">
                    BLOCKED
                  </span>
                </div>
                
                <div className="card-content">
                  <div className="detail-item">
                    <span className="label">Date:</span>
                    <span>{new Date(slot.date).toLocaleDateString()}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Reason:</span>
                    <span>{slot.reason}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Created by:</span>
                    <span>{slot.created_by || 'System'}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Calendar Sync:</span>
                    <span className={slot.sync_to_calendars !== false ? 'success' : 'inactive'}>
                      {slot.sync_to_calendars !== false ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                  {slot.created_date && (
                    <div className="detail-item">
                      <span className="label">Created:</span>
                      <span>{new Date(slot.created_date).toLocaleString()}</span>
                    </div>
                  )}
                </div>

                <div className="item-actions">
                  <button 
                    onClick={() => handleEdit(slot)}
                    className="button small secondary"
                  >
                    Edit
                  </button>
                  <button 
                    onClick={() => handleDelete(slot.id)}
                    className="button small danger"
                  >
                    Unblock
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Summary Stats */}
      <div className="blocked-slots-stats">
        <h4>Blocking Summary</h4>
        <div className="stats-grid">
          <div className="stat-item">
            <span className="stat-value">{blockedSlots.length}</span>
            <span className="stat-label">Total Blocked</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">
              {blockedSlots.filter(s => s.sync_to_calendars !== false).length}
            </span>
            <span className="stat-label">Synced to Calendars</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">
              {blockedSlots.filter(s => s.date >= new Date().toISOString().split('T')[0]).length}
            </span>
            <span className="stat-label">Future Blocks</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BlockedTimeSlotsManager;