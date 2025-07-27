import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { roommateAPI } from '../services/api';

const RoommateSelector = ({ 
  onCancel = null,
  title = "Link Your Account",
  subtitle = "Select which roommate you are to continue"
}) => {
  const { linkRoommate, user, isLoading: authLoading } = useAuth();
  const [roommates, setRoommates] = useState([]);
  const [selectedRoommate, setSelectedRoommate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [linking, setLinking] = useState(false);
  const [error, setError] = useState(null);

  // Load roommates on component mount
  useEffect(() => {
    const loadRoommates = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await roommateAPI.getAll();
        
        // Filter out roommates that are already linked to Google accounts
        const availableRoommates = response.data.filter(roommate => 
          !roommate.google_id || roommate.google_id === user?.google_id
        );
        
        setRoommates(availableRoommates);
      } catch (err) {
        setError('Failed to load roommates: ' + (err.response?.data?.error || err.message));
      } finally {
        setLoading(false);
      }
    };

    loadRoommates();
  }, [user?.google_id]);

  const handleRoommateSelect = (roommate) => {
    setSelectedRoommate(roommate);
    setError(null);
  };

  const handleLinkRoommate = async () => {
    if (!selectedRoommate) {
      setError('Please select a roommate');
      return;
    }

    try {
      setLinking(true);
      setError(null);
      
      const result = await linkRoommate(selectedRoommate.id);
      
      if (result.success) {
        // Success! The AuthContext will handle the state update
        console.log('Successfully linked to roommate:', selectedRoommate.name);
      } else {
        setError(result.error || 'Failed to link roommate');
      }
    } catch (err) {
      setError('Unexpected error during linking');
      console.error('Link roommate error:', err);
    } finally {
      setLinking(false);
    }
  };

  const handleSkip = () => {
    if (onCancel) {
      onCancel();
    }
  };

  if (loading || authLoading) {
    return (
      <div className="roommate-selector">
        <div className="loading">
          <div className="loading-spinner"></div>
          <p>Loading roommates...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="roommate-selector">
      <div className="roommate-selector-header">
        <h2>{title}</h2>
        {subtitle && <p className="subtitle">{subtitle}</p>}
      </div>

      {user && (
        <div className="user-info-preview">
          <div className="user-avatar-small">
            {user.picture ? (
              <img src={user.picture} alt={user.name} />
            ) : (
              <div className="avatar-placeholder">{user.name.charAt(0)}</div>
            )}
          </div>
          <div className="user-details">
            <strong>{user.name}</strong>
            <span className="user-email">{user.email}</span>
          </div>
        </div>
      )}

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      {roommates.length === 0 ? (
        <div className="no-roommates">
          <p>No available roommates found.</p>
          <p className="text-small">
            All roommates may already be linked to Google accounts, or there might be an issue loading the data.
          </p>
          {onCancel && (
            <button onClick={handleSkip} className="button secondary">
              Continue Without Linking
            </button>
          )}
        </div>
      ) : (
        <div className="roommate-selector-content">
          <div className="roommate-instructions">
            <p>Choose which roommate profile belongs to you:</p>
          </div>

          <div className="roommate-list">
            {roommates.map((roommate) => (
              <div
                key={roommate.id}
                className={`roommate-option ${
                  selectedRoommate?.id === roommate.id ? 'selected' : ''
                } ${roommate.google_id ? 'already-linked' : ''}`}
                onClick={() => !roommate.google_id && handleRoommateSelect(roommate)}
              >
                <div className="roommate-info">
                  <div className="roommate-name">{roommate.name}</div>
                  <div className="roommate-details">
                    <span className="points">
                      {roommate.current_cycle_points} cycle points
                    </span>
                    {roommate.google_id && roommate.google_id === user?.google_id && (
                      <span className="status-badge linked-to-you">Linked to you</span>
                    )}
                    {roommate.google_id && roommate.google_id !== user?.google_id && (
                      <span className="status-badge already-linked">Already linked</span>
                    )}
                  </div>
                </div>
                
                {selectedRoommate?.id === roommate.id && (
                  <div className="selection-indicator">✓</div>
                )}
                
                {roommate.google_id && roommate.google_id !== user?.google_id && (
                  <div className="unavailable-overlay">
                    <span>Unavailable</span>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="roommate-selector-actions">
            <button
              onClick={handleLinkRoommate}
              disabled={!selectedRoommate || linking}
              className="button primary"
            >
              {linking ? 'Linking...' : 'Link Account'}
            </button>
            
            {onCancel && (
              <button
                onClick={handleSkip}
                disabled={linking}
                className="button secondary"
              >
                Skip for Now
              </button>
            )}
          </div>

          <div className="linking-info">
            <p className="text-small">
              <strong>Note:</strong> Linking your Google account to a roommate allows you to:
            </p>
            <ul className="text-small">
              <li>See your personalized chore assignments</li>
              <li>Sync chores to your Google Calendar</li>
              <li>Track your contribution points</li>
              <li>Use all RoomieRoster features</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default RoommateSelector;