import React, { useState, useEffect } from 'react';
import { shoppingListAPI, roommateAPI } from '../services/api';
import CategoryManager from './CategoryManager';
import CategorySection from './CategorySection';

const ShoppingListManager = () => {
  const [categorizedItems, setCategorizedItems] = useState({});
  const [categories, setCategories] = useState(['General']);
  const [roommates, setRoommates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
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
    category: 'General',
    notes: ''
  });

  useEffect(() => {
    loadCategories();
    loadCategorizedItems();
    loadRoommates();
    checkForUpdates();
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

  const loadCategories = async () => {
    try {
      const response = await shoppingListAPI.getCategories();
      setCategories(response.data.categories || ['General']);
    } catch (err) {
      console.error('Failed to load categories:', err);
      setCategories(['General']);
    }
  };

  const loadCategorizedItems = async () => {
    try {
      setLoading(true);
      setError(null);
      const statusFilter = filter === 'all' ? null : filter;
      const response = await shoppingListAPI.getByCategory(statusFilter);
      setCategorizedItems(response.data.categories || {});
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

  const checkForUpdates = async () => {
    try {
      const response = await shoppingListAPI.getMetadata();
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
    await loadCategories();
    await loadCategorizedItems();
    const response = await shoppingListAPI.getMetadata();
    setLastModified(response.data.last_modified);
  };

  const resetForm = () => {
    setFormData({
      item_name: '',
      estimated_price: '',
      brand_preference: '',
      category: 'General',
      notes: ''
    });
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
    if (!formData.item_name.trim()) return;

    try {
      setError(null);
      const itemData = {
        ...formData,
        estimated_price: formData.estimated_price ? parseFloat(formData.estimated_price) : null
      };

      await shoppingListAPI.create(itemData);

      // Update timestamp and refresh
      const metadataResponse = await shoppingListAPI.getMetadata();
      setLastModified(metadataResponse.data.last_modified);

      await loadCategorizedItems();
      resetForm();
    } catch (err) {
      setError('Failed to save item: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleUpdateItem = async (itemId, itemData) => {
    try {
      await shoppingListAPI.update(itemId, itemData);
      const metadataResponse = await shoppingListAPI.getMetadata();
      setLastModified(metadataResponse.data.last_modified);
      await loadCategorizedItems();
    } catch (err) {
      throw new Error('Failed to update item: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleDeleteItem = async (itemId) => {
    try {
      await shoppingListAPI.delete(itemId);
      const metadataResponse = await shoppingListAPI.getMetadata();
      setLastModified(metadataResponse.data.last_modified);
      await loadCategorizedItems();
    } catch (err) {
      throw new Error('Failed to delete item: ' + (err.response?.data?.error || err.message));
    }
  };

  const handlePurchaseItem = async (itemId, purchaseData) => {
    try {
      const purchasePayload = {
        ...purchaseData,
        actual_price: purchaseData.actual_price ? parseFloat(purchaseData.actual_price) : null
      };

      await shoppingListAPI.markPurchased(itemId, purchasePayload);
      const metadataResponse = await shoppingListAPI.getMetadata();
      setLastModified(metadataResponse.data.last_modified);
      await loadCategorizedItems();
    } catch (err) {
      throw new Error('Failed to mark as purchased: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleAddCategory = async (categoryName) => {
    try {
      const response = await shoppingListAPI.createCategory(categoryName);
      setCategories(response.data.categories);
      // Auto-select new category in form
      setFormData(prev => ({ ...prev, category: categoryName }));
    } catch (err) {
      throw err;
    }
  };

  const handleRenameCategory = async (oldName, newName) => {
    try {
      const response = await shoppingListAPI.renameCategory(oldName, newName);
      setCategories(response.data.categories);
      await loadCategorizedItems();
    } catch (err) {
      throw err;
    }
  };

  const handleDeleteCategory = async (categoryName) => {
    try {
      const response = await shoppingListAPI.deleteCategory(categoryName);
      setCategories(response.data.categories);
      await loadCategorizedItems();
    } catch (err) {
      alert('Failed to delete category: ' + (err.response?.data?.error || err.message));
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <h2>Loading shopping list...</h2>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ margin: 0 }}>Shopping List</h1>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            style={{
              padding: '10px 20px',
              backgroundColor: showAddForm ? '#6c757d' : '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '16px',
              fontWeight: 'bold'
            }}
          >
            {showAddForm ? 'Cancel' : 'Add Item'}
          </button>
          <button
            onClick={() => setIsPolling(!isPolling)}
            style={{
              padding: '10px 20px',
              backgroundColor: isPolling ? '#28a745' : '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '16px',
              fontWeight: 'bold'
            }}
            title={isPolling ? 'Real-time updates enabled' : 'Real-time updates disabled'}
          >
            {isPolling ? '🔄 Live' : '⏸️ Paused'}
          </button>
        </div>
      </div>

      {/* Update notification */}
      {updateAvailable && (
        <div
          style={{
            backgroundColor: '#d1ecf1',
            border: '1px solid #bee5eb',
            borderRadius: '8px',
            padding: '16px',
            marginBottom: '20px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <span style={{ color: '#0c5460', fontWeight: 'bold' }}>
            🔄 New changes available from other users!
          </span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={refreshData}
              style={{
                padding: '8px 16px',
                backgroundColor: '#17a2b8',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Refresh Now
            </button>
            <button
              onClick={() => setUpdateAvailable(false)}
              style={{
                padding: '8px 16px',
                backgroundColor: '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {error && (
        <div
          style={{
            backgroundColor: '#f8d7da',
            border: '1px solid #f5c6cb',
            borderRadius: '8px',
            padding: '16px',
            marginBottom: '20px',
            color: '#721c24'
          }}
        >
          {error}
        </div>
      )}

      {/* Filter buttons */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
        <button
          onClick={() => setFilter('active')}
          style={{
            padding: '10px 20px',
            backgroundColor: filter === 'active' ? '#007bff' : '#e9ecef',
            color: filter === 'active' ? 'white' : '#495057',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
        >
          Active Items
        </button>
        <button
          onClick={() => setFilter('purchased')}
          style={{
            padding: '10px 20px',
            backgroundColor: filter === 'purchased' ? '#007bff' : '#e9ecef',
            color: filter === 'purchased' ? 'white' : '#495057',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
        >
          Purchased
        </button>
        <button
          onClick={() => setFilter('all')}
          style={{
            padding: '10px 20px',
            backgroundColor: filter === 'all' ? '#007bff' : '#e9ecef',
            color: filter === 'all' ? 'white' : '#495057',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
        >
          All Items
        </button>
      </div>

      {/* Add item form */}
      {showAddForm && (
        <form
          onSubmit={handleSubmit}
          style={{
            backgroundColor: '#f8f9fa',
            border: '2px solid #007bff',
            borderRadius: '12px',
            padding: '24px',
            marginBottom: '24px'
          }}
        >
          <h3 style={{ marginTop: 0 }}>Add New Item</h3>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              Item Name *
            </label>
            <input
              type="text"
              name="item_name"
              value={formData.item_name}
              onChange={handleInputChange}
              placeholder="e.g., Paper Towels"
              required
              style={{
                width: '100%',
                padding: '10px',
                border: '1px solid #ced4da',
                borderRadius: '6px',
                fontSize: '14px'
              }}
            />
            <p style={{ fontSize: '12px', color: '#666', marginTop: '4px', marginBottom: 0 }}>
              This will be automatically assigned to you
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginBottom: '16px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Estimated Price
              </label>
              <input
                type="number"
                name="estimated_price"
                value={formData.estimated_price}
                onChange={handleInputChange}
                step="0.01"
                min="0"
                placeholder="0.00"
                style={{
                  width: '100%',
                  padding: '10px',
                  border: '1px solid #ced4da',
                  borderRadius: '6px',
                  fontSize: '14px'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Brand Preference
              </label>
              <input
                type="text"
                name="brand_preference"
                value={formData.brand_preference}
                onChange={handleInputChange}
                placeholder="e.g., Bounty"
                style={{
                  width: '100%',
                  padding: '10px',
                  border: '1px solid #ced4da',
                  borderRadius: '6px',
                  fontSize: '14px'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Category *
              </label>
              <select
                name="category"
                value={formData.category}
                onChange={handleInputChange}
                required
                style={{
                  width: '100%',
                  padding: '10px',
                  border: '1px solid #ced4da',
                  borderRadius: '6px',
                  fontSize: '14px'
                }}
              >
                {categories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              Notes
            </label>
            <textarea
              name="notes"
              value={formData.notes}
              onChange={handleInputChange}
              placeholder="Any additional notes..."
              rows="3"
              style={{
                width: '100%',
                padding: '10px',
                border: '1px solid #ced4da',
                borderRadius: '6px',
                fontSize: '14px',
                resize: 'vertical'
              }}
            />
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              type="submit"
              style={{
                padding: '10px 24px',
                backgroundColor: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '16px',
                fontWeight: 'bold'
              }}
            >
              Add Item
            </button>
            <button
              type="button"
              onClick={resetForm}
              style={{
                padding: '10px 24px',
                backgroundColor: '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '16px'
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Category Manager */}
      <CategoryManager
        categories={categories}
        onAddCategory={handleAddCategory}
        onRenameCategory={handleRenameCategory}
        onRefresh={loadCategories}
      />

      {/* Category Sections */}
      {categories.map(category => (
        categorizedItems[category] && (
          <CategorySection
            key={category}
            categoryName={category}
            categoryData={categorizedItems[category]}
            roommates={roommates}
            onUpdateItem={handleUpdateItem}
            onDeleteItem={handleDeleteItem}
            onPurchaseItem={handlePurchaseItem}
            onDeleteCategory={handleDeleteCategory}
            filter={filter}
          />
        )
      ))}

      {Object.keys(categorizedItems).length === 0 && (
        <div
          style={{
            textAlign: 'center',
            padding: '60px 20px',
            backgroundColor: '#f8f9fa',
            borderRadius: '12px',
            border: '2px dashed #dee2e6'
          }}
        >
          <h3 style={{ color: '#6c757d' }}>No items yet</h3>
          <p style={{ color: '#6c757d' }}>Click "Add Item" to start your shopping list</p>
        </div>
      )}
    </div>
  );
};

export default ShoppingListManager;
