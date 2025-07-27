import React, { useState, useEffect } from 'react';
import { requestAPI, roommateAPI } from '../services/api';

const RequestManager = () => {
  const [requests, setRequests] = useState([]);
  const [roommates, setRoommates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showRequestForm, setShowRequestForm] = useState(false);
  const [activeTab, setActiveTab] = useState('pending'); // pending, my-requests, all
  const [selectedUser, setSelectedUser] = useState(null);

  // Real-time update state
  const [lastModified, setLastModified] = useState(null);
  const [isPolling, setIsPolling] = useState(true);
  const [updateAvailable, setUpdateAvailable] = useState(false);

  // Form state for new requests
  const [formData, setFormData] = useState({
    item_name: '',
    estimated_price: '',
    brand_preference: '',
    notes: '',
    requested_by: '',
    requested_by_name: '',
    approval_threshold: 2,
    auto_approve_under: 10.00
  });

  // Approval form state
  const [approvalNotes, setApprovalNotes] = useState({});

  useEffect(() => {
    loadRequests();
    loadRoommates();
    checkForUpdates();
  }, [activeTab]);

  // Polling effect for real-time updates
  useEffect(() => {
    if (!isPolling) return;

    const pollInterval = setInterval(() => {
      checkForUpdates();
    }, 5000); // Check every 5 seconds

    return () => clearInterval(pollInterval);
  }, [isPolling, lastModified]); // eslint-disable-line react-hooks/exhaustive-deps

  // Clean up polling when component unmounts
  useEffect(() => {
    return () => setIsPolling(false);
  }, []);

  const loadRequests = async () => {
    try {
      setLoading(true);
      setError(null);
      
      let response;
      if (activeTab === 'pending' && selectedUser) {
        response = await requestAPI.getPendingForUser(selectedUser.id);
      } else if (activeTab === 'my-requests' && selectedUser) {
        response = await requestAPI.getAll();
        // Filter to show only current user's requests
        const allRequests = response.data.requests || [];
        const myRequests = allRequests.filter(req => req.requested_by === selectedUser.id);
        setRequests(myRequests);
        return;
      } else {
        response = await requestAPI.getAll(activeTab === 'all' ? null : activeTab);
      }
      
      setRequests(response.data.requests || []);
    } catch (err) {
      setError('Failed to load requests: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const loadRoommates = async () => {
    try {
      const response = await roommateAPI.getAll();
      setRoommates(response.data);
      
      // Auto-select first roommate if none selected
      if (!selectedUser && response.data.length > 0) {
        setSelectedUser(response.data[0]);
      }
    } catch (err) {
      console.error('Failed to load roommates:', err);
    }
  };

  const checkForUpdates = async () => {
    try {
      const response = await requestAPI.getMetadata();
      const newLastModified = response.data.last_modified;
      
      if (lastModified && newLastModified !== lastModified) {
        setUpdateAvailable(true);
      } else if (!lastModified) {
        setLastModified(newLastModified);
      }
    } catch (err) {
      console.error('Failed to check for updates:', err);
    }
  };

  const refreshData = async () => {
    setUpdateAvailable(false);
    await loadRequests();
    const response = await requestAPI.getMetadata();
    setLastModified(response.data.last_modified);
  };

  const resetForm = () => {
    setFormData({
      item_name: '',
      estimated_price: '',
      brand_preference: '',
      notes: '',
      requested_by: '',
      requested_by_name: '',
      approval_threshold: 2,
      auto_approve_under: 10.00
    });
    setShowRequestForm(false);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleRoommateSelect = (roommateId) => {
    const roommate = roommates.find(r => r.id === parseInt(roommateId));
    setFormData(prev => ({
      ...prev,
      requested_by: roommate ? roommate.id : '',
      requested_by_name: roommate ? roommate.name : ''
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.item_name.trim() || !formData.requested_by) return;

    try {
      setError(null);
      const requestData = {
        ...formData,
        estimated_price: formData.estimated_price ? parseFloat(formData.estimated_price) : null,
        approval_threshold: parseInt(formData.approval_threshold),
        auto_approve_under: parseFloat(formData.auto_approve_under)
      };

      await requestAPI.create(requestData);
      await loadRequests();
      
      // Update lastModified timestamp after successful mutation
      const metadataResponse = await requestAPI.getMetadata();
      setLastModified(metadataResponse.data.last_modified);
      
      resetForm();
    } catch (err) {
      setError('Failed to submit request: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleApproval = async (requestId, approvalStatus) => {
    if (!selectedUser) {
      setError('Please select a user to approve requests');
      return;
    }

    try {
      setError(null);
      const approvalData = {
        approved_by: selectedUser.id,
        approved_by_name: selectedUser.name,
        approval_status: approvalStatus,
        notes: approvalNotes[requestId] || ''
      };

      await requestAPI.approve(requestId, approvalData);
      await loadRequests();
      
      // Update lastModified timestamp after successful mutation
      const metadataResponse = await requestAPI.getMetadata();
      setLastModified(metadataResponse.data.last_modified);
      
      // Clear approval notes for this request
      setApprovalNotes(prev => ({ ...prev, [requestId]: '' }));
    } catch (err) {
      setError('Failed to process approval: ' + (err.response?.data?.error || err.message));
    }
  };

  const deleteRequest = async (requestId) => {
    if (!window.confirm('Are you sure you want to delete this request?')) return;

    try {
      setError(null);
      await requestAPI.delete(requestId);
      await loadRequests();
      
      // Update lastModified timestamp after successful mutation
      const metadataResponse = await requestAPI.getMetadata();
      setLastModified(metadataResponse.data.last_modified);
    } catch (err) {
      setError('Failed to delete request: ' + (err.response?.data?.error || err.message));
    }
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'pending': return 'status-pending';
      case 'approved': return 'status-approved';
      case 'declined': return 'status-declined';
      case 'auto-approved': return 'status-auto-approved';
      default: return 'status-unknown';
    }
  };

  const formatPrice = (price) => {
    return price ? `$${price.toFixed(2)}` : 'Not specified';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return <div className="loading">Loading requests...</div>;
  }

  return (
    <div className="request-manager">
      <div className="header">
        <h2>Item Requests</h2>
        <div className="header-actions">
          <select
            value={selectedUser?.id || ''}
            onChange={(e) => {
              const user = roommates.find(r => r.id === parseInt(e.target.value));
              setSelectedUser(user);
            }}
            className="user-selector"
          >
            <option value="">Select User...</option>
            {roommates.map(roommate => (
              <option key={roommate.id} value={roommate.id}>
                {roommate.name}
              </option>
            ))}
          </select>
          <button
            onClick={() => setShowRequestForm(!showRequestForm)}
            className="button primary"
          >
            {showRequestForm ? 'Cancel' : 'New Request'}
          </button>
          <button
            onClick={() => setIsPolling(!isPolling)}
            className={`button ${isPolling ? 'success' : 'secondary'}`}
            title={isPolling ? 'Real-time updates enabled' : 'Real-time updates disabled'}
          >
            {isPolling ? '🔄 Live' : '⏸️ Paused'}
          </button>
        </div>
      </div>

      {/* Update notification */}
      {updateAvailable && (
        <div className="update-notification">
          <div className="update-content">
            <span>🔄 New request changes available!</span>
            <button onClick={refreshData} className="button small primary">
              Refresh Now
            </button>
            <button onClick={() => setUpdateAvailable(false)} className="button small secondary">
              Dismiss
            </button>
          </div>
        </div>
      )}

      {error && <div className="error">{error}</div>}

      {/* Tab navigation */}
      <div className="tab-navigation">
        <button
          onClick={() => setActiveTab('pending')}
          className={`tab-btn ${activeTab === 'pending' ? 'active' : ''}`}
        >
          Pending Approvals ({requests.filter(r => r.status === 'pending').length})
        </button>
        <button
          onClick={() => setActiveTab('my-requests')}
          className={`tab-btn ${activeTab === 'my-requests' ? 'active' : ''}`}
        >
          My Requests
        </button>
        <button
          onClick={() => setActiveTab('all')}
          className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`}
        >
          All Requests
        </button>
      </div>

      {/* Request submission form */}
      {showRequestForm && (
        <form onSubmit={handleSubmit} className="request-form">
          <h3>Submit New Request</h3>
          
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="item_name">Item Name *</label>
              <input
                type="text"
                id="item_name"
                name="item_name"
                value={formData.item_name}
                onChange={handleInputChange}
                placeholder="e.g., Premium Coffee Beans"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="requested_by">Requested By *</label>
              <select
                id="requested_by"
                value={formData.requested_by}
                onChange={(e) => handleRoommateSelect(e.target.value)}
                required
              >
                <option value="">Select roommate...</option>
                {roommates.map(roommate => (
                  <option key={roommate.id} value={roommate.id}>
                    {roommate.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="estimated_price">Estimated Price</label>
              <input
                type="number"
                id="estimated_price"
                name="estimated_price"
                value={formData.estimated_price}
                onChange={handleInputChange}
                step="0.01"
                min="0"
                placeholder="0.00"
              />
            </div>

            <div className="form-group">
              <label htmlFor="brand_preference">Brand Preference</label>
              <input
                type="text"
                id="brand_preference"
                name="brand_preference"
                value={formData.brand_preference}
                onChange={handleInputChange}
                placeholder="e.g., Blue Bottle"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="auto_approve_under">Auto-approve under</label>
              <input
                type="number"
                id="auto_approve_under"
                name="auto_approve_under"
                value={formData.auto_approve_under}
                onChange={handleInputChange}
                step="0.01"
                min="0"
                placeholder="10.00"
              />
            </div>

            <div className="form-group">
              <label htmlFor="approval_threshold">Approvals needed</label>
              <input
                type="number"
                id="approval_threshold"
                name="approval_threshold"
                value={formData.approval_threshold}
                onChange={handleInputChange}
                min="1"
                max="10"
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="notes">Notes</label>
            <textarea
              id="notes"
              name="notes"
              value={formData.notes}
              onChange={handleInputChange}
              placeholder="Why do you need this item?"
              rows="3"
            />
          </div>

          <div className="form-actions">
            <button type="submit" className="button primary">
              Submit Request
            </button>
            <button type="button" onClick={resetForm} className="button secondary">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Requests list */}
      <div className="requests-list">
        {requests.length === 0 ? (
          <p className="empty-state">
            {activeTab === 'pending' ? 'No pending requests to approve.' :
             activeTab === 'my-requests' ? 'You have not submitted any requests.' :
             'No requests found.'}
          </p>
        ) : (
          <div className="request-cards">
            {requests.map((request) => (
              <div key={request.id} className={`request-card ${getStatusBadgeClass(request.status)}`}>
                <div className="request-header">
                  <h4 className="request-name">{request.item_name}</h4>
                  <span className={`status-badge ${getStatusBadgeClass(request.status)}`}>
                    {request.status.replace('-', ' ').toUpperCase()}
                  </span>
                </div>
                
                <div className="request-details">
                  <div className="detail-item">
                    <span className="label">Estimated Price:</span>
                    <span className="value">{formatPrice(request.estimated_price)}</span>
                  </div>
                  {request.brand_preference && (
                    <div className="detail-item">
                      <span className="label">Brand:</span>
                      <span className="value">{request.brand_preference}</span>
                    </div>
                  )}
                  <div className="detail-item">
                    <span className="label">Requested by:</span>
                    <span className="value">{request.requested_by_name}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Date:</span>
                    <span className="value">{formatDate(request.date_requested)}</span>
                  </div>
                  {request.notes && (
                    <div className="detail-item notes">
                      <span className="label">Notes:</span>
                      <span className="value">{request.notes}</span>
                    </div>
                  )}
                </div>

                {/* Approval section for pending requests */}
                {request.status === 'pending' && activeTab === 'pending' && selectedUser && 
                 request.requested_by !== selectedUser.id && (
                  <div className="approval-section">
                    <h5>Your Decision</h5>
                    <textarea
                      placeholder="Optional approval notes..."
                      value={approvalNotes[request.id] || ''}
                      onChange={(e) => setApprovalNotes(prev => ({ 
                        ...prev, 
                        [request.id]: e.target.value 
                      }))}
                      rows="2"
                    />
                    <div className="approval-actions">
                      <button
                        onClick={() => handleApproval(request.id, 'approved')}
                        className="button small success"
                      >
                        ✅ Approve
                      </button>
                      <button
                        onClick={() => handleApproval(request.id, 'declined')}
                        className="button small danger"
                      >
                        ❌ Decline
                      </button>
                    </div>
                  </div>
                )}

                {/* Approval history */}
                {request.approvals && request.approvals.length > 0 && (
                  <div className="approval-history">
                    <h5>Approval History</h5>
                    {request.approvals.map((approval, index) => (
                      <div key={index} className={`approval-item ${approval.approval_status}`}>
                        <span className="approval-user">{approval.approved_by_name}</span>
                        <span className={`approval-status ${approval.approval_status}`}>
                          {approval.approval_status === 'approved' ? '✅' : '❌'} {approval.approval_status}
                        </span>
                        {approval.notes && <span className="approval-notes">"{approval.notes}"</span>}
                      </div>
                    ))}
                  </div>
                )}

                {/* Action buttons for my requests */}
                {activeTab === 'my-requests' && request.status === 'pending' && (
                  <div className="request-actions">
                    <button
                      onClick={() => deleteRequest(request.id)}
                      className="button small danger"
                    >
                      Delete Request
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default RequestManager;