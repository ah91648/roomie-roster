import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

const UserProfile = ({ 
  compact = false,
  showRoommateInfo = true,
  showActions = true 
}) => {
  const { 
    user, 
    hasRoommate, 
    logout, 
    revokeAccess, 
    unlinkRoommate,
    isLoading,
    error,
    clearError
  } = useAuth();
  
  const [showActionMenu, setShowActionMenu] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);

  if (!user) {
    return null;
  }

  const handleLogout = async () => {
    setActionLoading('logout');
    try {
      const result = await logout();
      if (!result.success) {
        console.error('Logout failed:', result.error);
      }
    } finally {
      setActionLoading(null);
    }
  };

  const handleRevokeAccess = async () => {
    if (!window.confirm('Are you sure you want to revoke access? This will disconnect your Google account and log you out.')) {
      return;
    }
    
    setActionLoading('revoke');
    try {
      const result = await revokeAccess();
      if (!result.success) {
        console.error('Revoke access failed:', result.error);
      }
    } finally {
      setActionLoading(null);
    }
  };

  const handleUnlinkRoommate = async () => {
    if (!window.confirm('Are you sure you want to unlink from your roommate? You will need to link again to see your assignments.')) {
      return;
    }
    
    setActionLoading('unlink');
    try {
      const result = await unlinkRoommate();
      if (!result.success) {
        console.error('Unlink roommate failed:', result.error);
      }
    } finally {
      setActionLoading(null);
    }
  };

  if (compact) {
    return (
      <div className="user-profile-compact">
        <div className="user-avatar">
          {user.picture ? (
            <img 
              src={user.picture} 
              alt={user.name}
              className="avatar-image"
            />
          ) : (
            <div className="avatar-placeholder">
              {user.name.charAt(0).toUpperCase()}
            </div>
          )}
        </div>
        <div className="user-info">
          <div className="user-name">{user.name}</div>
          {showRoommateInfo && hasRoommate && (
            <div className="roommate-info">
              {user.roommate.name}
            </div>
          )}
        </div>
        {showActions && (
          <div className="user-actions-compact">
            <button 
              onClick={() => setShowActionMenu(!showActionMenu)}
              className="button small secondary"
            >
              ⚙️
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="user-profile">
      <div className="user-profile-header">
        <h3>👤 User Profile</h3>
      </div>

      {error && (
        <div className="error">
          {error}
          <button onClick={clearError} className="button small">×</button>
        </div>
      )}

      <div className="user-profile-content">
        <div className="user-basic-info">
          <div className="user-avatar-large">
            {user.picture ? (
              <img 
                src={user.picture} 
                alt={user.name}
                className="avatar-image-large"
              />
            ) : (
              <div className="avatar-placeholder-large">
                {user.name.charAt(0).toUpperCase()}
              </div>
            )}
          </div>
          
          <div className="user-details">
            <h4>{user.name}</h4>
            <p className="user-email">{user.email}</p>
            
            {user.login_time && (
              <p className="login-time">
                Logged in: {new Date(user.login_time).toLocaleDateString()}
              </p>
            )}
          </div>
        </div>

        {showRoommateInfo && (
          <div className="roommate-section">
            <h5>Roommate Linking</h5>
            {hasRoommate ? (
              <div className="roommate-linked">
                <div className="roommate-info">
                  <span className="status-indicator success">✅</span>
                  <span>Linked to: <strong>{user.roommate.name}</strong></span>
                </div>
                {showActions && (
                  <button
                    onClick={handleUnlinkRoommate}
                    disabled={actionLoading === 'unlink' || isLoading}
                    className="button small secondary"
                  >
                    {actionLoading === 'unlink' ? 'Unlinking...' : 'Unlink Roommate'}
                  </button>
                )}
              </div>
            ) : (
              <div className="roommate-not-linked">
                <div className="roommate-info">
                  <span className="status-indicator warning">⚠️</span>
                  <span>Not linked to a roommate</span>
                </div>
                <p className="text-small">
                  Link your account to a roommate to see personalized assignments and use all features.
                </p>
              </div>
            )}
          </div>
        )}

        {showActions && (
          <div className="user-actions">
            <h5>Account Actions</h5>
            
            <div className="action-buttons">
              <button
                onClick={handleLogout}
                disabled={actionLoading === 'logout' || isLoading}
                className="button secondary"
              >
                {actionLoading === 'logout' ? 'Logging out...' : 'Logout'}
              </button>
              
              <button
                onClick={handleRevokeAccess}
                disabled={actionLoading === 'revoke' || isLoading}
                className="button danger"
              >
                {actionLoading === 'revoke' ? 'Revoking...' : 'Revoke Google Access'}
              </button>
            </div>
            
            <p className="text-small">
              <strong>Logout:</strong> End your session but keep Google account connected.<br/>
              <strong>Revoke Access:</strong> Completely disconnect your Google account.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

// Variants for different use cases
export const UserProfileCompact = (props) => (
  <UserProfile compact={true} {...props} />
);

export const UserProfileHeader = (props) => (
  <UserProfile 
    compact={true} 
    showRoommateInfo={true} 
    showActions={true} 
    {...props} 
  />
);

export default UserProfile;