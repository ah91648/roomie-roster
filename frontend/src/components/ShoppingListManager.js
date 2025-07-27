import React, { useState, useEffect } from 'react';
import { shoppingListAPI, roommateAPI } from '../services/api';

const ShoppingListManager = () => {
  const [items, setItems] = useState([]);
  const [roommates, setRoommates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const [purchaseHistory, setPurchaseHistory] = useState([]);
  const [filter, setFilter] = useState('active'); // active, purchased, all
  
  // Real-time update state
  const [lastModified, setLastModified] = useState(null);
  const [isPolling, setIsPolling] = useState(true);
  const [updateAvailable, setUpdateAvailable] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    item_name: '',
    estimated_price: '',
    brand_preference: '',
    notes: '',
    added_by: '',
    added_by_name: ''
  });

  // Purchase form state
  const [purchaseData, setPurchaseData] = useState({
    purchased_by: '',
    purchased_by_name: '',
    actual_price: '',
    notes: ''
  });

  // Clear history state
  const [clearFromDate, setClearFromDate] = useState('');
  const [showClearControls, setShowClearControls] = useState(false);

  useEffect(() => {
    loadShoppingList();
    loadRoommates();
    checkForUpdates(); // Initial metadata check
  }, [filter]); // eslint-disable-line react-hooks/exhaustive-deps

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

  const loadShoppingList = async () => {
    try {
      setLoading(true);
      setError(null);
      const statusFilter = filter === 'all' ? null : filter;
      const response = await shoppingListAPI.getAll(statusFilter);
      setItems(response.data.items || []);
    } catch (err) {
      setError('Failed to load shopping list: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const loadRoommates = async () => {
    try {
      const response = await roommateAPI.getAll();
      setRoommates(response.data);
    } catch (err) {
      console.error('Failed to load roommates:', err);
    }
  };

  const loadPurchaseHistory = async () => {
    try {
      const response = await shoppingListAPI.getHistory(30);
      setPurchaseHistory(response.data.history || []);
    } catch (err) {
      setError('Failed to load purchase history: ' + (err.response?.data?.error || err.message));
    }
  };

  const checkForUpdates = async () => {
    try {
      const response = await shoppingListAPI.getMetadata();
      const newLastModified = response.data.last_modified;
      
      if (lastModified && newLastModified !== lastModified) {
        setUpdateAvailable(true);
      } else if (!lastModified) {
        // First time loading, set the timestamp without showing update notification
        setLastModified(newLastModified);
      }
    } catch (err) {
      console.error('Failed to check for updates:', err);
      // Don't show error to user for polling failures
    }
  };

  const refreshData = async () => {
    setUpdateAvailable(false);
    await loadShoppingList();
    const response = await shoppingListAPI.getMetadata();
    setLastModified(response.data.last_modified);
  };

  const resetForm = () => {
    setFormData({
      item_name: '',
      estimated_price: '',
      brand_preference: '',
      notes: '',
      added_by: '',
      added_by_name: ''
    });
    setEditingItem(null);
    setShowAddForm(false);
  };

  const resetPurchaseForm = () => {
    setPurchaseData({
      purchased_by: '',
      purchased_by_name: '',
      actual_price: '',
      notes: ''
    });
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handlePurchaseChange = (e) => {
    const { name, value } = e.target;
    setPurchaseData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleRoommateSelect = (field, roommateId) => {
    const roommate = roommates.find(r => r.id === parseInt(roommateId));
    if (field === 'added_by') {
      setFormData(prev => ({
        ...prev,
        added_by: roommate ? roommate.id : '',
        added_by_name: roommate ? roommate.name : ''
      }));
    } else if (field === 'purchased_by') {
      setPurchaseData(prev => ({
        ...prev,
        purchased_by: roommate ? roommate.id : '',
        purchased_by_name: roommate ? roommate.name : ''
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.item_name.trim() || !formData.added_by) return;

    try {
      setError(null);
      const itemData = {
        ...formData,
        estimated_price: formData.estimated_price ? parseFloat(formData.estimated_price) : null
      };

      if (editingItem) {
        // Update existing item
        const response = await shoppingListAPI.update(editingItem.id, itemData);
        setItems(items.map(item => item.id === editingItem.id ? response.data : item));
      } else {
        // Add new item
        const response = await shoppingListAPI.create(itemData);
        setItems([...items, response.data]);
      }
      
      // Update lastModified timestamp after successful mutation
      const metadataResponse = await shoppingListAPI.getMetadata();
      setLastModified(metadataResponse.data.last_modified);
      
      resetForm();
    } catch (err) {
      setError('Failed to save item: ' + (err.response?.data?.error || err.message));
    }
  };

  const deleteItem = async (id) => {
    if (!window.confirm('Are you sure you want to delete this item?')) return;

    try {
      setError(null);
      await shoppingListAPI.delete(id);
      setItems(items.filter(item => item.id !== id));
      
      // Update lastModified timestamp after successful mutation
      const metadataResponse = await shoppingListAPI.getMetadata();
      setLastModified(metadataResponse.data.last_modified);
    } catch (err) {
      setError('Failed to delete item: ' + (err.response?.data?.error || err.message));
    }
  };

  const startEditing = (item) => {
    setFormData({
      item_name: item.item_name,
      estimated_price: item.estimated_price || '',
      brand_preference: item.brand_preference || '',
      notes: item.notes || '',
      added_by: item.added_by,
      added_by_name: item.added_by_name
    });
    setEditingItem(item);
    setShowAddForm(true);
  };

  const markPurchased = async (item) => {
    if (!purchaseData.purchased_by) {
      setError('Please select who purchased the item');
      return;
    }

    try {
      setError(null);
      const purchasePayload = {
        ...purchaseData,
        actual_price: purchaseData.actual_price ? parseFloat(purchaseData.actual_price) : null
      };

      const response = await shoppingListAPI.markPurchased(item.id, purchasePayload);
      setItems(items.map(i => i.id === item.id ? response.data.item : i));
      
      // Update lastModified timestamp after successful mutation
      const metadataResponse = await shoppingListAPI.getMetadata();
      setLastModified(metadataResponse.data.last_modified);
      
      resetPurchaseForm();
    } catch (err) {
      setError('Failed to mark item as purchased: ' + (err.response?.data?.error || err.message));
    }
  };

  const formatPrice = (price) => {
    return price ? `$${price.toFixed(2)}` : 'Not specified';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  const clearAllHistory = async () => {
    if (!window.confirm('Are you sure you want to clear ALL purchase history? This will reset all purchased items to active status.')) {
      return;
    }

    try {
      const response = await shoppingListAPI.clearAllHistory();
      setError(null);
      
      // Refresh data
      await loadShoppingList();
      await loadPurchaseHistory();
      
      alert(`Successfully cleared ${response.data.cleared_count} purchased items`);
    } catch (err) {
      setError('Failed to clear purchase history: ' + (err.response?.data?.error || err.message));
    }
  };

  const clearHistoryFromDate = async () => {
    if (!clearFromDate.trim()) {
      setError('Please enter a date');
      return;
    }

    if (!window.confirm(`Are you sure you want to clear purchase history from ${clearFromDate} onward? This will reset matching purchased items to active status.`)) {
      return;
    }

    try {
      const response = await shoppingListAPI.clearHistoryFromDate(clearFromDate);
      setError(null);
      
      // Refresh data
      await loadShoppingList();
      await loadPurchaseHistory();
      
      alert(`Successfully cleared ${response.data.cleared_count} purchased items from ${clearFromDate} onward`);
      setClearFromDate('');
      setShowClearControls(false);
    } catch (err) {
      setError('Failed to clear purchase history: ' + (err.response?.data?.error || err.message));
    }
  };

  if (loading) {
    return <div className="loading">Loading shopping list...</div>;
  }

  return (
    <div className="shopping-list-manager">
      <div className="header">
        <h2>Shopping List</h2>
        <div className="header-actions">
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="button primary"
          >
            {showAddForm ? 'Cancel' : 'Add Item'}
          </button>
          <button
            onClick={() => {
              setShowHistory(!showHistory);
              if (!showHistory) loadPurchaseHistory();
            }}
            className="button secondary"
          >
            {showHistory ? 'Hide History' : 'Purchase History'}
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
            <span>🔄 New changes available from other users!</span>
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

      {/* Filter buttons */}
      <div className="filter-buttons">
        <button
          onClick={() => setFilter('active')}
          className={`filter-btn ${filter === 'active' ? 'active' : ''}`}
        >
          Active Items ({items.filter(i => i.status === 'active').length})
        </button>
        <button
          onClick={() => setFilter('purchased')}
          className={`filter-btn ${filter === 'purchased' ? 'active' : ''}`}
        >
          Purchased ({items.filter(i => i.status === 'purchased').length})
        </button>
        <button
          onClick={() => setFilter('all')}
          className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
        >
          All Items
        </button>
      </div>

      {/* Add/Edit item form */}
      {showAddForm && (
        <form onSubmit={handleSubmit} className="shopping-form">
          <h3>{editingItem ? 'Edit Item' : 'Add New Item'}</h3>
          
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="item_name">Item Name *</label>
              <input
                type="text"
                id="item_name"
                name="item_name"
                value={formData.item_name}
                onChange={handleInputChange}
                placeholder="e.g., Paper Towels"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="added_by">Added By *</label>
              <select
                id="added_by"
                value={formData.added_by}
                onChange={(e) => handleRoommateSelect('added_by', e.target.value)}
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
                placeholder="e.g., Bounty"
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
              placeholder="Any additional notes..."
              rows="3"
            />
          </div>

          <div className="form-actions">
            <button type="submit" className="button primary">
              {editingItem ? 'Update Item' : 'Add Item'}
            </button>
            <button type="button" onClick={resetForm} className="button secondary">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Purchase History */}
      {showHistory && (
        <div className="purchase-history">
          <h3>Recent Purchases (Last 30 Days)</h3>
          {purchaseHistory.length === 0 ? (
            <p>No purchases in the last 30 days.</p>
          ) : (
            <div className="history-list">
              {purchaseHistory.map(item => (
                <div key={item.id} className="history-item">
                  <div className="history-content">
                    <h4>{item.item_name}</h4>
                    <p>Purchased by: <strong>{item.purchased_by_name}</strong></p>
                    <p>Date: {formatDate(item.purchase_date)}</p>
                    <p>Price: {formatPrice(item.actual_price)}</p>
                    {item.brand_preference && <p>Brand: {item.brand_preference}</p>}
                  </div>
                </div>
              ))}
            </div>
          )}
          
          {/* Purchase History Management */}
          <div className="history-management">
            <div className="management-header">
              <h4>Manage Purchase History</h4>
              <button 
                type="button" 
                onClick={() => setShowClearControls(!showClearControls)}
                className="button secondary small"
              >
                {showClearControls ? 'Hide Controls' : 'Show Controls'}
              </button>
            </div>
            
            {showClearControls && (
              <div className="clear-controls">
                <div className="control-group">
                  <button 
                    type="button" 
                    onClick={clearAllHistory}
                    className="button danger"
                  >
                    Clear All History
                  </button>
                  <p className="help-text">Reset all purchased items to active status</p>
                </div>
                
                <div className="control-group">
                  <div className="date-clear-section">
                    <label htmlFor="clearFromDate">Clear from date onward:</label>
                    <div className="date-input-group">
                      <input
                        type="date"
                        id="clearFromDate"
                        value={clearFromDate}
                        onChange={(e) => setClearFromDate(e.target.value)}
                        className="form-input"
                      />
                      <button 
                        type="button" 
                        onClick={clearHistoryFromDate}
                        disabled={!clearFromDate}
                        className="button danger"
                      >
                        Clear From Date
                      </button>
                    </div>
                  </div>
                  <p className="help-text">Reset purchased items from the selected date onward to active status</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Shopping list items */}
      <div className="shopping-list">
        {items.length === 0 ? (
          <p className="empty-state">
            {filter === 'active' ? 'No active items in the shopping list.' : 
             filter === 'purchased' ? 'No purchased items found.' : 
             'No items in the shopping list. Add your first item above!'}
          </p>
        ) : (
          <div className="shopping-items">
            {items.map((item) => (
              <div key={item.id} className={`shopping-item ${item.status}`}>
                <div className="item-header">
                  <h4 className="item-name">{item.item_name}</h4>
                  <span className={`status-badge ${item.status}`}>
                    {item.status === 'active' ? 'Need to Buy' : 'Purchased'}
                  </span>
                </div>
                
                <div className="item-details">
                  <div className="detail-item">
                    <span className="label">Estimated Price:</span>
                    <span className="value">{formatPrice(item.estimated_price)}</span>
                  </div>
                  {item.actual_price && (
                    <div className="detail-item">
                      <span className="label">Actual Price:</span>
                      <span className="value">{formatPrice(item.actual_price)}</span>
                    </div>
                  )}
                  {item.brand_preference && (
                    <div className="detail-item">
                      <span className="label">Brand:</span>
                      <span className="value">{item.brand_preference}</span>
                    </div>
                  )}
                  <div className="detail-item">
                    <span className="label">Added by:</span>
                    <span className="value">{item.added_by_name}</span>
                  </div>
                  {item.purchased_by_name && (
                    <div className="detail-item">
                      <span className="label">Purchased by:</span>
                      <span className="value">{item.purchased_by_name}</span>
                    </div>
                  )}
                  {item.notes && (
                    <div className="detail-item notes">
                      <span className="label">Notes:</span>
                      <span className="value">{item.notes}</span>
                    </div>
                  )}
                </div>

                <div className="item-actions">
                  {item.status === 'active' && (
                    <>
                      <div className="purchase-section">
                        <h5>Mark as Purchased</h5>
                        <div className="purchase-form">
                          <select
                            value={purchaseData.purchased_by}
                            onChange={(e) => handleRoommateSelect('purchased_by', e.target.value)}
                          >
                            <option value="">Who bought this?</option>
                            {roommates.map(roommate => (
                              <option key={roommate.id} value={roommate.id}>
                                {roommate.name}
                              </option>
                            ))}
                          </select>
                          <input
                            type="number"
                            placeholder="Actual price"
                            step="0.01"
                            min="0"
                            value={purchaseData.actual_price}
                            onChange={handlePurchaseChange}
                            name="actual_price"
                          />
                          <button
                            onClick={() => markPurchased(item)}
                            className="button small primary"
                          >
                            Mark Purchased
                          </button>
                        </div>
                      </div>
                      <div className="item-controls">
                        <button
                          onClick={() => startEditing(item)}
                          className="button small secondary"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => deleteItem(item.id)}
                          className="button small danger"
                        >
                          Delete
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ShoppingListManager;