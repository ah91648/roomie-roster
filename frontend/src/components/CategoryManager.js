import React, { useState } from 'react';

const CategoryManager = ({ categories, onAddCategory, onRefresh }) => {
  const [isAdding, setIsAdding] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [error, setError] = useState('');

  const handleAddCategory = async () => {
    const trimmedName = newCategoryName.trim();

    if (!trimmedName) {
      setError('Category name cannot be empty');
      return;
    }

    if (trimmedName.length > 100) {
      setError('Category name must be 100 characters or less');
      return;
    }

    if (categories.includes(trimmedName)) {
      setError('This category already exists');
      return;
    }

    try {
      await onAddCategory(trimmedName);
      setNewCategoryName('');
      setIsAdding(false);
      setError('');
      if (onRefresh) {
        onRefresh();
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to add category');
    }
  };

  const handleCancel = () => {
    setIsAdding(false);
    setNewCategoryName('');
    setError('');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleAddCategory();
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  return (
    <div
      style={{
        backgroundColor: '#f8f9fa',
        border: '2px dashed #6c757d',
        borderRadius: '12px',
        padding: '20px',
        marginBottom: '24px'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <h3 style={{ margin: 0, color: '#495057' }}>
          📁 Shopping Categories ({categories.length})
        </h3>
        {!isAdding && (
          <button
            onClick={() => setIsAdding(true)}
            style={{
              padding: '8px 16px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: 'bold'
            }}
          >
            ➕ Add Category
          </button>
        )}
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: isAdding ? '16px' : '0' }}>
        {categories.map((category) => (
          <span
            key={category}
            style={{
              padding: '6px 12px',
              backgroundColor: category === 'General' ? '#007bff' : '#6c757d',
              color: 'white',
              borderRadius: '16px',
              fontSize: '14px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            {category}
            {category === 'General' && (
              <span style={{ fontSize: '10px', opacity: 0.8 }}>(default)</span>
            )}
          </span>
        ))}
      </div>

      {isAdding && (
        <div
          style={{
            marginTop: '16px',
            padding: '16px',
            backgroundColor: 'white',
            borderRadius: '8px',
            border: '1px solid #dee2e6'
          }}
        >
          <h4 style={{ margin: '0 0 12px 0', color: '#495057' }}>Add New Category</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div>
              <input
                type="text"
                value={newCategoryName}
                onChange={(e) => {
                  setNewCategoryName(e.target.value);
                  setError('');
                }}
                onKeyDown={handleKeyPress}
                placeholder="e.g., Groceries, Furniture, Electronics..."
                autoFocus
                style={{
                  width: '100%',
                  padding: '10px',
                  border: error ? '2px solid #dc3545' : '1px solid #ced4da',
                  borderRadius: '6px',
                  fontSize: '14px'
                }}
              />
              {error && (
                <div style={{ color: '#dc3545', fontSize: '12px', marginTop: '4px' }}>
                  {error}
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={handleAddCategory}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: 'bold'
                }}
              >
                Add Category
              </button>
              <button
                onClick={handleCancel}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                Cancel
              </button>
            </div>
          </div>
          <div style={{ marginTop: '12px', fontSize: '12px', color: '#6c757d' }}>
            <strong>Examples:</strong> Groceries, Furniture, Electronics, Cleaning Supplies, Office Supplies, Pet Supplies
          </div>
        </div>
      )}
    </div>
  );
};

export default CategoryManager;
