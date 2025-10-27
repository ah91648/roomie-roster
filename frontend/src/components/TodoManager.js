import React, { useState, useEffect } from 'react';
import { todoAPI } from '../services/api';
import RoommateSelector from './RoommateSelector';
import { useAuth } from '../contexts/AuthContext';

const TodoManager = () => {
  // Auth context for roommate linking
  const { user } = useAuth();

  // Todos state
  const [todos, setTodos] = useState([]);
  const [filteredTodos, setFilteredTodos] = useState([]);

  // Filter state
  const [statusFilter, setStatusFilter] = useState('pending');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [showRoommateSelector, setShowRoommateSelector] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);

  // Form state
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category: 'Work',
    priority: 'medium',
    due_date: '',
  });

  // Constants
  const CATEGORIES = ['Work', 'Personal', 'Health', 'Shopping', 'Other'];
  const PRIORITIES = ['low', 'medium', 'high', 'urgent'];
  const PRIORITY_COLORS = {
    low: '#4CAF50',
    medium: '#FFC107',
    high: '#FF9800',
    urgent: '#F44336',
  };
  const PRIORITY_EMOJI = {
    low: '🟢',
    medium: '🟡',
    high: '🟠',
    urgent: '🔴',
  };

  // Load todos on mount and filter change
  useEffect(() => {
    loadTodos();
  }, [statusFilter]);

  // Apply client-side filters
  useEffect(() => {
    applyFilters();
  }, [todos, categoryFilter, priorityFilter]);

  // Watch for roommate linking completion
  useEffect(() => {
    if (showRoommateSelector && user?.roommate) {
      // User just linked to a roommate, call the success handler
      handleRoommateLinked();
    }
  }, [user?.roommate, showRoommateSelector]);

  const loadTodos = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = {};
      if (statusFilter !== 'all') params.status = statusFilter;

      const response = await todoAPI.getAll(params);
      setTodos(response.data || []);
    } catch (err) {
      // Check if this is a roommate linking error
      const errorMessage = err.response?.data?.error || err.message;
      const isRoommateError = err.response?.status === 403 &&
        (errorMessage.includes('roommate') || errorMessage.includes('link'));

      if (isRoommateError) {
        // Show the roommate selector modal instead of error message
        setShowRoommateSelector(true);
        setError(null); // Clear error since we're showing the modal
      } else {
        setError('Failed to load todos: ' + errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...todos];

    // Category filter
    if (categoryFilter !== 'all') {
      filtered = filtered.filter(todo => todo.category === categoryFilter);
    }

    // Priority filter
    if (priorityFilter !== 'all') {
      filtered = filtered.filter(todo => todo.priority === priorityFilter);
    }

    setFilteredTodos(filtered);
  };

  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      category: 'Work',
      priority: 'medium',
      due_date: '',
    });
    setShowAddForm(false);
    setEditingId(null);
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

    if (!formData.title.trim()) {
      setError('Title is required');
      return;
    }

    try {
      setError(null);

      const todoData = {
        title: formData.title.trim(),
        description: formData.description.trim() || null,
        category: formData.category,
        priority: formData.priority,
        due_date: formData.due_date || null,
      };

      if (editingId) {
        // Update existing todo
        await todoAPI.update(editingId, todoData);
      } else {
        // Create new todo
        await todoAPI.create(todoData);
      }

      await loadTodos();
      resetForm();
    } catch (err) {
      setError('Failed to save todo: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleEdit = (todo) => {
    setFormData({
      title: todo.title,
      description: todo.description || '',
      category: todo.category,
      priority: todo.priority,
      due_date: todo.due_date ? todo.due_date.split('T')[0] : '',
    });
    setEditingId(todo.id);
    setShowAddForm(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this todo?')) return;

    try {
      setError(null);
      await todoAPI.delete(id);
      await loadTodos();
    } catch (err) {
      setError('Failed to delete todo: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleComplete = async (id) => {
    try {
      setError(null);
      await todoAPI.complete(id);
      await loadTodos();
    } catch (err) {
      setError('Failed to complete todo: ' + (err.response?.data?.error || err.message));
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    if (date.toDateString() === today.toDateString()) return 'Today';
    if (date.toDateString() === tomorrow.toDateString()) return 'Tomorrow';

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const isOverdue = (dateString) => {
    if (!dateString) return false;
    const dueDate = new Date(dateString);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return dueDate < today;
  };

  const handleRoommateLinked = async () => {
    console.log('[TODO] Roommate linked successfully, closing modal...');
    setShowRoommateSelector(false);

    // Retry loading todos
    console.log('[TODO] Reloading todos...');
    setTimeout(() => {
      loadTodos();
    }, 800);
  };

  const handleRoommateSelectorCancel = () => {
    console.log('[TODO] User cancelled roommate linking');
    setShowRoommateSelector(false);
    setPendingAction(null);
    setError('You must link your account to a roommate to use productivity features');
  };

  if (loading) {
    return (
      <div className="todo-manager">
        <div className="loading">Loading todos...</div>
      </div>
    );
  }

  return (
    <div className="todo-manager">
      <div className="todo-header">
        <h2>Todo List</h2>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="button primary add-todo-btn"
        >
          {showAddForm ? 'Cancel' : '+ Add Todo'}
        </button>
      </div>

      {error && (
        <div className="error-message">
          <p>{error}</p>
          <button onClick={() => setError(null)} className="dismiss-btn">Dismiss</button>
        </div>
      )}

      {/* Add/Edit Form */}
      {showAddForm && (
        <div className="todo-form-card">
          <h3>{editingId ? 'Edit Todo' : 'New Todo'}</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="title">Title *</label>
              <input
                type="text"
                id="title"
                name="title"
                value={formData.title}
                onChange={handleInputChange}
                placeholder="What needs to be done?"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="description">Description</label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                rows="3"
                placeholder="Additional details..."
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="category">Category</label>
                <select
                  id="category"
                  name="category"
                  value={formData.category}
                  onChange={handleInputChange}
                >
                  {CATEGORIES.map(cat => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="priority">Priority</label>
                <select
                  id="priority"
                  name="priority"
                  value={formData.priority}
                  onChange={handleInputChange}
                >
                  {PRIORITIES.map(pri => (
                    <option key={pri} value={pri}>
                      {pri.charAt(0).toUpperCase() + pri.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="due_date">Due Date</label>
                <input
                  type="date"
                  id="due_date"
                  name="due_date"
                  value={formData.due_date}
                  onChange={handleInputChange}
                />
              </div>
            </div>

            <div className="form-actions">
              <button type="submit" className="button primary">
                {editingId ? 'Update' : 'Create'} Todo
              </button>
              <button type="button" onClick={resetForm} className="button secondary">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Filters */}
      <div className="todo-filters">
        <div className="filter-group">
          <label>Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="filter-select"
          >
            <option value="pending">Pending</option>
            <option value="completed">Completed</option>
            <option value="all">All</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Category:</label>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Categories</option>
            {CATEGORIES.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Priority:</label>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Priorities</option>
            {PRIORITIES.map(pri => (
              <option key={pri} value={pri}>
                {pri.charAt(0).toUpperCase() + pri.slice(1)}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-summary">
          Showing {filteredTodos.length} of {todos.length} todos
        </div>
      </div>

      {/* Todo List */}
      <div className="todos-list">
        {filteredTodos.length === 0 ? (
          <div className="empty-state">
            <p>No todos found. {statusFilter === 'pending' && 'Create one to get started!'}</p>
          </div>
        ) : (
          filteredTodos.map(todo => (
            <div key={todo.id} className={`todo-item ${todo.status === 'completed' ? 'completed' : ''}`}>
              <div className="todo-checkbox">
                {todo.status !== 'completed' && (
                  <input
                    type="checkbox"
                    checked={false}
                    onChange={() => handleComplete(todo.id)}
                    title="Mark as completed"
                  />
                )}
                {todo.status === 'completed' && (
                  <div className="completed-icon">✓</div>
                )}
              </div>

              <div className="todo-content">
                <div className="todo-title-row">
                  <h4 className="todo-title">{todo.title}</h4>
                  <div className="todo-badges">
                    <span
                      className="priority-badge"
                      style={{ backgroundColor: PRIORITY_COLORS[todo.priority] }}
                      title={`${todo.priority} priority`}
                    >
                      {PRIORITY_EMOJI[todo.priority]} {todo.priority}
                    </span>
                    <span className="category-badge">{todo.category}</span>
                    {todo.due_date && (
                      <span className={`due-date-badge ${isOverdue(todo.due_date) ? 'overdue' : ''}`}>
                        {isOverdue(todo.due_date) && '⚠️ '}
                        Due: {formatDate(todo.due_date)}
                      </span>
                    )}
                  </div>
                </div>

                {todo.description && (
                  <p className="todo-description">{todo.description}</p>
                )}

                {todo.status === 'completed' && todo.completed_at && (
                  <div className="completion-info">
                    Completed: {new Date(todo.completed_at).toLocaleDateString()}
                  </div>
                )}
              </div>

              {todo.status !== 'completed' && (
                <div className="todo-actions">
                  <button
                    onClick={() => handleEdit(todo)}
                    className="button-icon edit-btn"
                    title="Edit"
                  >
                    ✏️
                  </button>
                  <button
                    onClick={() => handleDelete(todo.id)}
                    className="button-icon delete-btn"
                    title="Delete"
                  >
                    🗑️
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Roommate Linking Modal - Shown when productivity features require roommate link */}
      {showRoommateSelector && (
        <div className="modal-overlay" onClick={(e) => {
          // Only close if clicking the overlay background, not the modal content
          if (e.target.className === 'modal-overlay') {
            handleRoommateSelectorCancel();
          }
        }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Roommate Linking Required</h2>
              <button
                className="modal-close"
                onClick={handleRoommateSelectorCancel}
                aria-label="Close modal"
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <p className="modal-info">
                Productivity features (Pomodoro, Todos, Mood Journal) require you to link your Google account to a roommate profile.
                Please select which roommate you are:
              </p>
              <RoommateSelector
                onCancel={handleRoommateSelectorCancel}
                title="Select Your Roommate Profile"
                subtitle="Choose your profile to continue using productivity features"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TodoManager;
