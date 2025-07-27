import React, { useState, useEffect } from 'react';
import { laundryAPI, roommateAPI } from '../services/api';

const LaundryScheduler = () => {
  // State for laundry slots data
  const [slots, setSlots] = useState([]);
  const [roommates, setRoommates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingSlot, setEditingSlot] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [filterRoommate, setFilterRoommate] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  // Form state for new/edit slot
  const [formData, setFormData] = useState({
    roommate_id: '',
    roommate_name: '',
    date: new Date().toISOString().split('T')[0],
    time_slot: '',
    duration_hours: 2,
    load_type: 'mixed',
    machine_type: 'washer',
    estimated_loads: 1,
    notes: ''
  });

  const timeSlots = [
    '06:00-08:00', '08:00-10:00', '10:00-12:00', '12:00-14:00',
    '14:00-16:00', '16:00-18:00', '18:00-20:00', '20:00-22:00'
  ];

  const loadTypes = [
    { value: 'darks', label: 'Darks' },
    { value: 'lights', label: 'Lights' },
    { value: 'delicates', label: 'Delicates' },
    { value: 'bedding', label: 'Bedding' },
    { value: 'towels', label: 'Towels' },
    { value: 'mixed', label: 'Mixed' }
  ];

  const machineTypes = [
    { value: 'washer', label: 'Washer' },
    { value: 'dryer', label: 'Dryer' },
    { value: 'combo', label: 'Washer/Dryer' }
  ];

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [slotsResponse, roommatesResponse] = await Promise.all([
        laundryAPI.getAll(),
        roommateAPI.getAll()
      ]);
      
      setSlots(slotsResponse.data);
      setRoommates(roommatesResponse.data);
    } catch (err) {
      setError('Failed to load data: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? parseInt(value) || 0 : value
    }));

    // Auto-fill roommate name when roommate is selected
    if (name === 'roommate_id') {
      const selectedRoommate = roommates.find(r => r.id === parseInt(value));
      if (selectedRoommate) {
        setFormData(prev => ({
          ...prev,
          roommate_name: selectedRoommate.name
        }));
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.roommate_id || !formData.date || !formData.time_slot) {
      setError('Please fill in all required fields');
      return;
    }

    try {
      setError(null);
      
      // Check for conflicts
      const conflictCheck = await laundryAPI.checkConflicts({
        date: formData.date,
        time_slot: formData.time_slot,
        machine_type: formData.machine_type,
        exclude_slot_id: editingSlot?.id
      });

      if (conflictCheck.data.has_conflicts) {
        const conflict = conflictCheck.data.conflicts[0];
        setError(`Time slot conflict with ${conflict.roommate_name} at ${conflict.time_slot}`);
        return;
      }

      if (editingSlot) {
        // Update existing slot
        const response = await laundryAPI.update(editingSlot.id, formData);
        setSlots(slots.map(slot => slot.id === editingSlot.id ? response.data : slot));
      } else {
        // Create new slot
        const response = await laundryAPI.create(formData);
        setSlots([...slots, response.data]);
      }
      
      resetForm();
    } catch (err) {
      if (err.response?.status === 409) {
        const conflict = err.response.data.conflict;
        setError(`Time slot conflict with ${conflict.existing_roommate} at ${conflict.conflicting_time}`);
      } else {
        setError('Failed to save slot: ' + (err.response?.data?.error || err.message));
      }
    }
  };

  const handleEdit = (slot) => {
    setEditingSlot(slot);
    setFormData({
      roommate_id: slot.roommate_id,
      roommate_name: slot.roommate_name,
      date: slot.date,
      time_slot: slot.time_slot,
      duration_hours: slot.duration_hours,
      load_type: slot.load_type,
      machine_type: slot.machine_type,
      estimated_loads: slot.estimated_loads,
      notes: slot.notes || ''
    });
    setShowAddForm(true);
  };

  const handleDelete = async (slotId) => {
    if (!window.confirm('Are you sure you want to delete this laundry slot?')) return;

    try {
      setError(null);
      await laundryAPI.delete(slotId);
      setSlots(slots.filter(slot => slot.id !== slotId));
    } catch (err) {
      setError('Failed to delete slot: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleComplete = async (slotId) => {
    const actualLoads = window.prompt('How many loads were actually completed?');
    if (actualLoads === null) return;

    const completionNotes = window.prompt('Any completion notes? (optional)') || '';

    try {
      setError(null);
      const response = await laundryAPI.complete(slotId, {
        actual_loads: parseInt(actualLoads) || undefined,
        completion_notes: completionNotes
      });
      setSlots(slots.map(slot => slot.id === slotId ? response.data : slot));
    } catch (err) {
      setError('Failed to complete slot: ' + (err.response?.data?.error || err.message));
    }
  };

  const resetForm = () => {
    setFormData({
      roommate_id: '',
      roommate_name: '',
      date: new Date().toISOString().split('T')[0],
      time_slot: '',
      duration_hours: 2,
      load_type: 'mixed',
      machine_type: 'washer',
      estimated_loads: 1,
      notes: ''
    });
    setEditingSlot(null);
    setShowAddForm(false);
  };

  const getFilteredSlots = () => {
    return slots.filter(slot => {
      if (filterRoommate && slot.roommate_id !== parseInt(filterRoommate)) return false;
      if (filterStatus && slot.status !== filterStatus) return false;
      if (selectedDate && slot.date !== selectedDate) return false;
      return true;
    });
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'scheduled': return '#007bff';
      case 'in_progress': return '#ffc107';
      case 'completed': return '#28a745';
      case 'cancelled': return '#6c757d';
      default: return '#007bff';
    }
  };

  if (loading) {
    return <div className="loading">Loading laundry schedule...</div>;
  }

  const filteredSlots = getFilteredSlots();

  return (
    <div className="laundry-scheduler">
      <div className="header">
        <h2>🧺 Laundry Schedule</h2>
        <div className="header-actions">
          <button 
            onClick={() => setShowAddForm(!showAddForm)} 
            className="button primary"
          >
            {showAddForm ? 'Cancel' : 'Schedule Laundry'}
          </button>
          <button onClick={loadData} className="button secondary">
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {/* Filters */}
      <div className="filters">
        <div className="form-row">
          <div className="form-group">
            <label>Filter by Date:</label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="input"
            />
          </div>
          <div className="form-group">
            <label>Filter by Roommate:</label>
            <select
              value={filterRoommate}
              onChange={(e) => setFilterRoommate(e.target.value)}
              className="input"
            >
              <option value="">All Roommates</option>
              {roommates.map(roommate => (
                <option key={roommate.id} value={roommate.id}>
                  {roommate.name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Filter by Status:</label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="input"
            >
              <option value="">All Statuses</option>
              <option value="scheduled">Scheduled</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>
      </div>

      {/* Add/Edit Form */}
      {showAddForm && (
        <div className="laundry-form">
          <h3>{editingSlot ? 'Edit Laundry Slot' : 'Schedule New Laundry'}</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label>Roommate *</label>
                <select
                  name="roommate_id"
                  value={formData.roommate_id}
                  onChange={handleInputChange}
                  required
                  className="input"
                >
                  <option value="">Select Roommate</option>
                  {roommates.map(roommate => (
                    <option key={roommate.id} value={roommate.id}>
                      {roommate.name}
                    </option>
                  ))}
                </select>
              </div>
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
            </div>

            <div className="form-row">
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
              <div className="form-group">
                <label>Machine Type</label>
                <select
                  name="machine_type"
                  value={formData.machine_type}
                  onChange={handleInputChange}
                  className="input"
                >
                  {machineTypes.map(type => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Load Type</label>
                <select
                  name="load_type"
                  value={formData.load_type}
                  onChange={handleInputChange}
                  className="input"
                >
                  {loadTypes.map(type => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Estimated Loads</label>
                <input
                  type="number"
                  name="estimated_loads"
                  value={formData.estimated_loads}
                  onChange={handleInputChange}
                  min="1"
                  max="10"
                  className="input"
                />
              </div>
            </div>

            <div className="form-group">
              <label>Notes</label>
              <textarea
                name="notes"
                value={formData.notes}
                onChange={handleInputChange}
                placeholder="Additional notes about this laundry session..."
                className="input"
                rows="3"
              />
            </div>

            <div className="form-actions">
              <button type="submit" className="button primary">
                {editingSlot ? 'Update Slot' : 'Schedule Laundry'}
              </button>
              <button type="button" onClick={resetForm} className="button secondary">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Laundry Slots List */}
      <div className="laundry-slots">
        <h3>
          Laundry Slots
          {selectedDate && ` for ${new Date(selectedDate).toLocaleDateString()}`}
          ({filteredSlots.length} slots)
        </h3>
        
        {filteredSlots.length === 0 ? (
          <div className="empty-state">
            No laundry slots found. {showAddForm ? 'Fill out the form above to schedule your first laundry session.' : 'Click "Schedule Laundry" to get started!'}
          </div>
        ) : (
          <div className="items-grid">
            {filteredSlots.map(slot => (
              <div key={slot.id} className="item-card laundry-slot-card">
                <div className="card-header">
                  <h4>{slot.roommate_name}</h4>
                  <span 
                    className="status-badge"
                    style={{ backgroundColor: getStatusColor(slot.status) }}
                  >
                    {slot.status.replace('_', ' ')}
                  </span>
                </div>
                
                <div className="card-content">
                  <div className="detail-item">
                    <span className="label">Date:</span>
                    <span>{new Date(slot.date).toLocaleDateString()}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Time:</span>
                    <span>{slot.time_slot}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Machine:</span>
                    <span>{slot.machine_type}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Load Type:</span>
                    <span>{slot.load_type}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Loads:</span>
                    <span>
                      {slot.status === 'completed' 
                        ? `${slot.actual_loads || slot.estimated_loads} completed`
                        : `${slot.estimated_loads} estimated`
                      }
                    </span>
                  </div>
                  {slot.notes && (
                    <div className="detail-item">
                      <span className="label">Notes:</span>
                      <span>{slot.notes}</span>
                    </div>
                  )}
                </div>

                <div className="item-actions">
                  {slot.status === 'scheduled' && (
                    <>
                      <button 
                        onClick={() => handleEdit(slot)}
                        className="button small secondary"
                      >
                        Edit
                      </button>
                      <button 
                        onClick={() => handleComplete(slot.id)}
                        className="button small primary"
                      >
                        Complete
                      </button>
                    </>
                  )}
                  <button 
                    onClick={() => handleDelete(slot.id)}
                    className="button small danger"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Summary Stats */}
      <div className="laundry-stats">
        <h3>Schedule Summary</h3>
        <div className="stats-grid">
          <div className="stat-item">
            <span className="stat-value">{slots.filter(s => s.status === 'scheduled').length}</span>
            <span className="stat-label">Scheduled</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{slots.filter(s => s.status === 'completed').length}</span>
            <span className="stat-label">Completed</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{slots.reduce((sum, s) => sum + (s.actual_loads || s.estimated_loads || 0), 0)}</span>
            <span className="stat-label">Total Loads</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LaundryScheduler;