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
  const [viewMode, setViewMode] = useState('month'); // 'day', 'week', 'month', 'all'
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

  // Helper function to convert 24hr time to 12hr AM/PM format
  const formatTimeToAMPM = (time24) => {
    const [hours, minutes] = time24.split(':').map(Number);
    const period = hours >= 12 ? 'PM' : 'AM';
    const hours12 = hours === 0 ? 12 : hours > 12 ? hours - 12 : hours;
    return `${hours12}:${minutes.toString().padStart(2, '0')} ${period}`;
  };

  // Helper function to convert time slot range to display format
  const formatTimeSlot = (timeSlot) => {
    const [start, end] = timeSlot.split('-');
    return `${formatTimeToAMPM(start)}-${formatTimeToAMPM(end)}`;
  };

  const timeSlots = [
    { value: '06:00-08:00', label: '6:00 AM-8:00 AM' },
    { value: '08:00-10:00', label: '8:00 AM-10:00 AM' },
    { value: '10:00-12:00', label: '10:00 AM-12:00 PM' },
    { value: '12:00-14:00', label: '12:00 PM-2:00 PM' },
    { value: '14:00-16:00', label: '2:00 PM-4:00 PM' },
    { value: '16:00-18:00', label: '4:00 PM-6:00 PM' },
    { value: '18:00-20:00', label: '6:00 PM-8:00 PM' },
    { value: '20:00-22:00', label: '8:00 PM-10:00 PM' }
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
    
    let processedValue = value;
    if (type === 'number') {
      processedValue = parseInt(value) || 0;
    } else if (name === 'roommate_id') {
      // Keep roommate_id as string for form state, convert to int only on submit
      processedValue = value;
    }
    
    setFormData(prev => ({
      ...prev,
      [name]: processedValue
    }));

    // Auto-fill roommate name when roommate is selected
    if (name === 'roommate_id' && value) {
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
      
      // Convert and validate roommate_id first
      const roommateId = parseInt(formData.roommate_id);
      if (isNaN(roommateId) || roommateId < 1) {
        setError('Please select a valid roommate');
        return;
      }
      
      // Prepare data with proper types
      const submitData = {
        ...formData,
        roommate_id: roommateId,
        estimated_loads: parseInt(formData.estimated_loads) || 1,
        duration_hours: parseInt(formData.duration_hours) || 2
      };
      
      // Check for conflicts
      const conflictCheck = await laundryAPI.checkConflicts({
        date: submitData.date,
        time_slot: submitData.time_slot,
        machine_type: submitData.machine_type,
        exclude_slot_id: editingSlot?.id
      });

      if (conflictCheck.data.has_conflicts) {
        const conflict = conflictCheck.data.conflicts[0];
        setError(`Time slot conflict with ${conflict.roommate_name} at ${conflict.time_slot}`);
        return;
      }

      if (editingSlot) {
        // Update existing slot
        const response = await laundryAPI.update(editingSlot.id, submitData);
        setSlots(slots.map(slot => slot.id === editingSlot.id ? response.data : slot));
      } else {
        // Create new slot
        const response = await laundryAPI.create(submitData);
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
      // Roommate filter
      if (filterRoommate && slot.roommate_id !== parseInt(filterRoommate)) return false;

      // Status filter
      if (filterStatus && slot.status !== filterStatus) return false;

      // Date range filter based on view mode
      const slotDate = new Date(slot.date + 'T00:00:00');
      const baseDate = new Date(selectedDate + 'T00:00:00');

      switch(viewMode) {
        case 'day':
          return slot.date === selectedDate;
        case 'week': {
          // Calculate week start (Sunday) and end (Saturday)
          const weekStart = new Date(baseDate);
          weekStart.setDate(baseDate.getDate() - baseDate.getDay());
          const weekEnd = new Date(weekStart);
          weekEnd.setDate(weekStart.getDate() + 6);
          weekEnd.setHours(23, 59, 59);
          return slotDate >= weekStart && slotDate <= weekEnd;
        }
        case 'month':
          return slotDate.getMonth() === baseDate.getMonth() &&
                 slotDate.getFullYear() === baseDate.getFullYear();
        case 'all':
          return true;
        default:
          return true;
      }
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

  // Get description of current view range
  const getViewRangeDescription = () => {
    const baseDate = new Date(selectedDate + 'T00:00:00');
    const options = { month: 'long', day: 'numeric', year: 'numeric' };

    switch(viewMode) {
      case 'day':
        return baseDate.toLocaleDateString(undefined, options);
      case 'week': {
        const weekStart = new Date(baseDate);
        weekStart.setDate(baseDate.getDate() - baseDate.getDay());
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekStart.getDate() + 6);
        return `${weekStart.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} - ${weekEnd.toLocaleDateString(undefined, options)}`;
      }
      case 'month':
        return baseDate.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
      case 'all':
        return 'All Time';
      default:
        return '';
    }
  };

  // Navigate to previous period
  const navigatePrevious = () => {
    const baseDate = new Date(selectedDate + 'T00:00:00');

    switch(viewMode) {
      case 'day':
        baseDate.setDate(baseDate.getDate() - 1);
        break;
      case 'week':
        baseDate.setDate(baseDate.getDate() - 7);
        break;
      case 'month':
        baseDate.setMonth(baseDate.getMonth() - 1);
        break;
      default:
        return;
    }

    setSelectedDate(baseDate.toISOString().split('T')[0]);
  };

  // Navigate to next period
  const navigateNext = () => {
    const baseDate = new Date(selectedDate + 'T00:00:00');

    switch(viewMode) {
      case 'day':
        baseDate.setDate(baseDate.getDate() + 1);
        break;
      case 'week':
        baseDate.setDate(baseDate.getDate() + 7);
        break;
      case 'month':
        baseDate.setMonth(baseDate.getMonth() + 1);
        break;
      default:
        return;
    }

    setSelectedDate(baseDate.toISOString().split('T')[0]);
  };

  // Group slots by date for multi-day views
  const groupSlotsByDate = (slots) => {
    const grouped = {};

    slots.forEach(slot => {
      if (!grouped[slot.date]) {
        grouped[slot.date] = [];
      }
      grouped[slot.date].push(slot);
    });

    // Sort dates and sort slots within each date by time
    return Object.keys(grouped)
      .sort()
      .map(date => ({
        date,
        slots: grouped[date].sort((a, b) => a.time_slot.localeCompare(b.time_slot))
      }));
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

      {/* Info Banner */}
      <div className="info-banner" style={{
        backgroundColor: '#e3f2fd',
        border: '1px solid #2196f3',
        borderRadius: '4px',
        padding: '12px 16px',
        margin: '16px 0',
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        <span style={{ fontSize: '1.2rem' }}>ℹ️</span>
        <span style={{ fontSize: '0.9rem', color: '#1976d2' }}>
          <strong>App-Only Feature:</strong> Laundry scheduling is managed within RoomieRoster and does not sync to Google Calendar. All roommates can view the schedule here in the app.
        </span>
      </div>

      {error && <div className="error">{error}</div>}

      {/* View Controls */}
      <div className="filters">
        <div className="form-row" style={{ alignItems: 'center', gap: '16px' }}>
          {/* View Mode Selector */}
          <div className="form-group">
            <label>View:</label>
            <select
              value={viewMode}
              onChange={(e) => setViewMode(e.target.value)}
              className="input"
              style={{ fontWeight: '500' }}
            >
              <option value="day">Today</option>
              <option value="week">This Week</option>
              <option value="month">This Month</option>
              <option value="all">All Time</option>
            </select>
          </div>

          {/* Date Navigation */}
          {viewMode !== 'all' && (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button
                onClick={navigatePrevious}
                className="button small secondary"
                title="Previous"
              >
                ◀
              </button>
              <span style={{
                minWidth: '200px',
                textAlign: 'center',
                fontWeight: '500',
                fontSize: '0.95rem'
              }}>
                {getViewRangeDescription()}
              </span>
              <button
                onClick={navigateNext}
                className="button small secondary"
                title="Next"
              >
                ▶
              </button>
              <button
                onClick={() => setSelectedDate(new Date().toISOString().split('T')[0])}
                className="button small secondary"
                style={{ marginLeft: '8px' }}
              >
                Today
              </button>
            </div>
          )}
        </div>

        {/* Filters Row */}
        <div className="form-row" style={{ marginTop: '12px' }}>
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
                    <option key={slot.value} value={slot.value}>{slot.label}</option>
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
          {viewMode === 'all' && ' - All Time'}
          {' '}({filteredSlots.length} {filteredSlots.length === 1 ? 'slot' : 'slots'})
        </h3>

        {filteredSlots.length === 0 ? (
          <div className="empty-state">
            No laundry slots found for {getViewRangeDescription().toLowerCase()}. {showAddForm ? 'Fill out the form above to schedule your first laundry session.' : 'Click "Schedule Laundry" to get started!'}
          </div>
        ) : viewMode === 'day' ? (
          // Single day view - show flat list
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
                    <span className="label">Time:</span>
                    <span>{formatTimeSlot(slot.time_slot)}</span>
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
        ) : (
          // Multi-day view - group by date
          <div>
            {groupSlotsByDate(filteredSlots).map(({ date, slots: dateSlots }) => (
              <div key={date} style={{ marginBottom: '24px' }}>
                <h4 style={{
                  backgroundColor: '#f5f5f5',
                  padding: '8px 12px',
                  borderRadius: '4px',
                  marginBottom: '12px',
                  fontSize: '1rem',
                  fontWeight: '600',
                  color: '#333'
                }}>
                  {new Date(date + 'T00:00:00').toLocaleDateString(undefined, {
                    weekday: 'long',
                    month: 'long',
                    day: 'numeric',
                    year: 'numeric'
                  })} ({dateSlots.length} {dateSlots.length === 1 ? 'slot' : 'slots'})
                </h4>
                <div className="items-grid">
                  {dateSlots.map(slot => (
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
                          <span className="label">Time:</span>
                          <span>{formatTimeSlot(slot.time_slot)}</span>
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