import React, { useState } from 'react';

const CollapsibleShoppingItem = ({
  item,
  roommates,
  onUpdate,
  onDelete,
  onPurchase
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isPurchasing, setIsPurchasing] = useState(false);
  const [editData, setEditData] = useState({
    item_name: item.item_name,
    estimated_price: item.estimated_price || '',
    brand_preference: item.brand_preference || '',
    category: item.category || 'General',
    notes: item.notes || ''
  });
  const [purchaseData, setPurchaseData] = useState({
    actual_price: item.estimated_price || '',
    notes: ''
  });

  const toggleExpand = () => {
    if (!isEditing && !isPurchasing) {
      setIsExpanded(!isExpanded);
    }
  };

  const handleEdit = (e) => {
    e.stopPropagation();
    setIsEditing(true);
    setIsExpanded(true);
  };

  const handleSaveEdit = async (e) => {
    e.stopPropagation();
    try {
      await onUpdate(item.id, editData);
      setIsEditing(false);
    } catch (error) {
      alert('Failed to update item: ' + error.message);
    }
  };

  const handleCancelEdit = (e) => {
    e.stopPropagation();
    setIsEditing(false);
    setEditData({
      item_name: item.item_name,
      estimated_price: item.estimated_price || '',
      brand_preference: item.brand_preference || '',
      category: item.category || 'General',
      notes: item.notes || ''
    });
  };

  const handleStartPurchase = (e) => {
    e.stopPropagation();
    setIsPurchasing(true);
    setIsExpanded(true);
  };

  const handleQuickPurchase = async (e) => {
    e.stopPropagation();
    try {
      // Quick purchase with estimated price, auto-assigned to logged-in user
      await onPurchase(item.id, {
        actual_price: item.estimated_price || null,
        notes: null
      });
    } catch (error) {
      alert('Failed to mark as purchased: ' + error.message);
    }
  };

  const handleCompletePurchase = async (e) => {
    e.stopPropagation();
    try {
      await onPurchase(item.id, purchaseData);
      setIsPurchasing(false);
    } catch (error) {
      alert('Failed to mark as purchased: ' + error.message);
    }
  };

  const handleCancelPurchase = (e) => {
    e.stopPropagation();
    setIsPurchasing(false);
    setPurchaseData({
      actual_price: item.estimated_price || '',
      notes: ''
    });
  };

  const handleDelete = async (e) => {
    e.stopPropagation();
    if (window.confirm(`Are you sure you want to delete "${item.item_name}"?`)) {
      try {
        await onDelete(item.id);
      } catch (error) {
        alert('Failed to delete item: ' + error.message);
      }
    }
  };

  const isPurchased = item.status === 'purchased';

  return (
    <div
      style={{
        border: '1px solid #ddd',
        borderRadius: '8px',
        marginBottom: '10px',
        backgroundColor: isPurchased ? '#f0f8f0' : '#fff',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        overflow: 'hidden'
      }}
    >
      {/* Collapsed Header - Always Visible */}
      <div
        onClick={toggleExpand}
        style={{
          padding: '12px 16px',
          cursor: 'pointer',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: isExpanded ? '#f8f9fa' : 'transparent',
          transition: 'background-color 0.2s'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
          {/* Quick Purchase Checkbox */}
          {!isPurchased && (
            <div
              onClick={handleQuickPurchase}
              style={{
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                border: '2px solid #007bff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                transition: 'all 0.2s',
                backgroundColor: '#fff'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#e7f3ff';
                e.currentTarget.style.borderColor = '#0056b3';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#fff';
                e.currentTarget.style.borderColor = '#007bff';
              }}
              title="Quick purchase at estimated price"
            >
            </div>
          )}
          {isPurchased && (
            <div
              style={{
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                border: '2px solid #28a745',
                backgroundColor: '#28a745',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontSize: '16px',
                fontWeight: 'bold'
              }}
            >
              ✓
            </div>
          )}
          <span style={{ fontSize: '18px' }}>
            {isExpanded ? '▼' : '▶'}
          </span>
          <div style={{ flex: 1 }}>
            <strong style={{ fontSize: '16px' }}>{item.item_name}</strong>
            {item.brand_preference && (
              <span style={{ marginLeft: '8px', color: '#666', fontSize: '14px' }}>
                ({item.brand_preference})
              </span>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{
              fontWeight: 'bold',
              fontSize: '16px',
              color: isPurchased ? '#28a745' : '#007bff'
            }}>
              ${isPurchased ? (item.actual_price || item.estimated_price) : item.estimated_price || '0.00'}
            </span>
            <span style={{
              padding: '4px 8px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: 'bold',
              backgroundColor: isPurchased ? '#d4edda' : '#fff3cd',
              color: isPurchased ? '#155724' : '#856404'
            }}>
              {isPurchased ? 'PURCHASED' : 'NEED TO BUY'}
            </span>
          </div>
        </div>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div style={{ padding: '16px', borderTop: '1px solid #eee' }}>
          {isEditing ? (
            // Edit Mode
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>Item Name:</label>
                <input
                  type="text"
                  value={editData.item_name}
                  onChange={(e) => setEditData({ ...editData, item_name: e.target.value })}
                  style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>Estimated Price:</label>
                  <input
                    type="number"
                    step="0.01"
                    value={editData.estimated_price}
                    onChange={(e) => setEditData({ ...editData, estimated_price: parseFloat(e.target.value) || '' })}
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>Brand:</label>
                  <input
                    type="text"
                    value={editData.brand_preference}
                    onChange={(e) => setEditData({ ...editData, brand_preference: e.target.value })}
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                  />
                </div>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>Notes:</label>
                <textarea
                  value={editData.notes}
                  onChange={(e) => setEditData({ ...editData, notes: e.target.value })}
                  rows="3"
                  style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                />
              </div>
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                <button
                  onClick={handleSaveEdit}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Save Changes
                </button>
                <button
                  onClick={handleCancelEdit}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : isPurchasing ? (
            // Purchase Mode - Detailed purchase with notes/price
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <h4>Mark as Purchased with Details</h4>
              <p style={{ color: '#666', fontSize: '14px', margin: '0 0 8px 0' }}>
                This will be automatically assigned to you. Add actual price or notes below.
              </p>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>Actual Price:</label>
                <input
                  type="number"
                  step="0.01"
                  value={purchaseData.actual_price}
                  onChange={(e) => setPurchaseData({ ...purchaseData, actual_price: parseFloat(e.target.value) || '' })}
                  style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>Notes (optional):</label>
                <textarea
                  value={purchaseData.notes}
                  onChange={(e) => setPurchaseData({ ...purchaseData, notes: e.target.value })}
                  style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px', minHeight: '60px' }}
                  placeholder="Add any notes about this purchase..."
                />
              </div>
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                <button
                  onClick={handleCompletePurchase}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Mark Purchased
                </button>
                <button
                  onClick={handleCancelPurchase}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            // View Mode
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: '8px' }}>
                <span style={{ fontWeight: 'bold' }}>Estimated Price:</span>
                <span>${item.estimated_price?.toFixed(2) || '0.00'}</span>

                {item.brand_preference && (
                  <>
                    <span style={{ fontWeight: 'bold' }}>Brand:</span>
                    <span>{item.brand_preference}</span>
                  </>
                )}

                <span style={{ fontWeight: 'bold' }}>Category:</span>
                <span>{item.category || 'General'}</span>

                <span style={{ fontWeight: 'bold' }}>Added by:</span>
                <span>{item.added_by_name}</span>

                {isPurchased && (
                  <>
                    <span style={{ fontWeight: 'bold' }}>Purchased by:</span>
                    <span>{item.purchased_by_name}</span>

                    <span style={{ fontWeight: 'bold' }}>Actual Price:</span>
                    <span>${item.actual_price?.toFixed(2) || item.estimated_price?.toFixed(2) || '0.00'}</span>

                    <span style={{ fontWeight: 'bold' }}>Purchase Date:</span>
                    <span>{new Date(item.purchase_date).toLocaleDateString()}</span>
                  </>
                )}
              </div>

              {item.notes && (
                <div>
                  <span style={{ fontWeight: 'bold' }}>Notes:</span>
                  <p style={{ margin: '4px 0', fontStyle: 'italic', color: '#666' }}>{item.notes}</p>
                </div>
              )}

              <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                {!isPurchased && (
                  <button
                    onClick={handleStartPurchase}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: '#28a745',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    Mark Purchased
                  </button>
                )}
                <button
                  onClick={handleEdit}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Edit
                </button>
                <button
                  onClick={handleDelete}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#dc3545',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CollapsibleShoppingItem;
