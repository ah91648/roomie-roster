import React, { useState } from 'react';
import CollapsibleShoppingItem from './CollapsibleShoppingItem';

const CategorySection = ({
  categoryName,
  categoryData,
  roommates,
  onUpdateItem,
  onDeleteItem,
  onPurchaseItem,
  onDeleteCategory,
  filter = 'active' // 'active', 'purchased', or 'all'
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const toggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };

  const handleDeleteCategory = () => {
    if (window.confirm(`Are you sure you want to delete the "${categoryName}" category? All items will be moved to "General".`)) {
      onDeleteCategory(categoryName);
    }
  };

  // Filter items based on the filter prop
  const getFilteredItems = () => {
    if (filter === 'all') {
      return categoryData.items || [];
    } else if (filter === 'active') {
      return categoryData.active_items || [];
    } else if (filter === 'purchased') {
      return categoryData.purchased_items || [];
    }
    return categoryData.items || [];
  };

  const filteredItems = getFilteredItems();
  const activeTotal = categoryData.total_active || 0;
  const purchasedTotal = categoryData.total_purchased || 0;
  const activeCount = categoryData.active_count || 0;
  const purchasedCount = categoryData.purchased_count || 0;

  // Don't show empty categories when filtering
  if (filteredItems.length === 0) {
    return null;
  }

  return (
    <div
      style={{
        border: '2px solid #007bff',
        borderRadius: '12px',
        marginBottom: '24px',
        overflow: 'hidden',
        backgroundColor: '#fff'
      }}
    >
      {/* Category Header */}
      <div
        style={{
          backgroundColor: '#007bff',
          color: 'white',
          padding: '16px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
          <button
            onClick={toggleCollapse}
            style={{
              background: 'none',
              border: 'none',
              color: 'white',
              fontSize: '20px',
              cursor: 'pointer',
              padding: '0',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            {isCollapsed ? '▶' : '▼'}
          </button>
          <h2 style={{ margin: 0, fontSize: '24px' }}>{categoryName}</h2>
          <span style={{ fontSize: '14px', opacity: 0.9 }}>
            ({filteredItems.length} {filteredItems.length === 1 ? 'item' : 'items'})
          </span>
        </div>
        {categoryName !== 'General' && (
          <button
            onClick={handleDeleteCategory}
            style={{
              background: 'rgba(255,255,255,0.2)',
              border: '1px solid white',
              color: 'white',
              padding: '6px 12px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            Delete Category
          </button>
        )}
      </div>

      {/* Category Content */}
      {!isCollapsed && (
        <>
          {/* Category Totals */}
          <div
            style={{
              backgroundColor: '#f8f9fa',
              padding: '16px 20px',
              borderBottom: '2px solid #dee2e6',
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '16px'
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <span style={{ fontSize: '14px', color: '#666', fontWeight: 'bold' }}>
                Active Items
              </span>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ fontSize: '24px', fontWeight: 'bold', color: '#007bff' }}>
                  ${activeTotal.toFixed(2)}
                </span>
                <span style={{ fontSize: '14px', color: '#666' }}>
                  {activeCount} {activeCount === 1 ? 'item' : 'items'}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <span style={{ fontSize: '14px', color: '#666', fontWeight: 'bold' }}>
                Purchased
              </span>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ fontSize: '24px', fontWeight: 'bold', color: '#28a745' }}>
                  ${purchasedTotal.toFixed(2)}
                </span>
                <span style={{ fontSize: '14px', color: '#666' }}>
                  {purchasedCount} {purchasedCount === 1 ? 'item' : 'items'}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <span style={{ fontSize: '14px', color: '#666', fontWeight: 'bold' }}>
                Total Category Budget
              </span>
              <span style={{ fontSize: '24px', fontWeight: 'bold', color: '#6c757d' }}>
                ${(activeTotal + purchasedTotal).toFixed(2)}
              </span>
            </div>
          </div>

          {/* Items List */}
          <div style={{ padding: '20px' }}>
            {filteredItems.length > 0 ? (
              filteredItems.map(item => (
                <CollapsibleShoppingItem
                  key={item.id}
                  item={item}
                  roommates={roommates}
                  onUpdate={onUpdateItem}
                  onDelete={onDeleteItem}
                  onPurchase={onPurchaseItem}
                />
              ))
            ) : (
              <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                <p>No items in this category</p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default CategorySection;
