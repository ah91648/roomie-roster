import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import { authAPI, clearTokens } from '../services/api';

// Create the Auth Context
const AuthContext = createContext();

// Auth action types
const AUTH_ACTIONS = {
  INIT_START: 'INIT_START',
  INIT_SUCCESS: 'INIT_SUCCESS',
  INIT_ERROR: 'INIT_ERROR',
  LOGIN_START: 'LOGIN_START',
  LOGIN_SUCCESS: 'LOGIN_SUCCESS',
  LOGIN_ERROR: 'LOGIN_ERROR',
  LOGOUT_START: 'LOGOUT_START',
  LOGOUT_SUCCESS: 'LOGOUT_SUCCESS',
  LOGOUT_ERROR: 'LOGOUT_ERROR',
  LINK_ROOMMATE_START: 'LINK_ROOMMATE_START',
  LINK_ROOMMATE_SUCCESS: 'LINK_ROOMMATE_SUCCESS',
  LINK_ROOMMATE_ERROR: 'LINK_ROOMMATE_ERROR',
  SHOW_ROOMMATE_LINK: 'SHOW_ROOMMATE_LINK',
  REFRESH_USER: 'REFRESH_USER',
  CLEAR_ERROR: 'CLEAR_ERROR'
};

// Initial auth state
const initialState = {
  user: null,
  isAuthenticated: false,
  isLoading: true,
  isInitialized: false,
  needsRoommateLink: false,
  error: null,
  authStatus: null
};

// Auth reducer
function authReducer(state, action) {
  switch (action.type) {
    case AUTH_ACTIONS.INIT_START:
      return {
        ...state,
        isLoading: true,
        error: null
      };
    
    case AUTH_ACTIONS.INIT_SUCCESS:
      return {
        ...state,
        isLoading: false,
        isInitialized: true,
        authStatus: action.payload.authStatus,
        user: action.payload.user,
        isAuthenticated: !!action.payload.user,
        needsRoommateLink: action.payload.user && !action.payload.user.roommate
      };
    
    case AUTH_ACTIONS.INIT_ERROR:
      return {
        ...state,
        isLoading: false,
        isInitialized: true,
        error: action.payload,
        user: null,
        isAuthenticated: false
      };
    
    case AUTH_ACTIONS.LOGIN_START:
      return {
        ...state,
        isLoading: true,
        error: null
      };
    
    case AUTH_ACTIONS.LOGIN_SUCCESS:
      return {
        ...state,
        isLoading: false,
        user: action.payload.user,
        isAuthenticated: true,
        needsRoommateLink: action.payload.needsRoommateLink || false,
        error: null
      };
    
    case AUTH_ACTIONS.LOGIN_ERROR:
      return {
        ...state,
        isLoading: false,
        error: action.payload,
        user: null,
        isAuthenticated: false
      };
    
    case AUTH_ACTIONS.LOGOUT_START:
      return {
        ...state,
        isLoading: true,
        error: null
      };
    
    case AUTH_ACTIONS.LOGOUT_SUCCESS:
      return {
        ...state,
        isLoading: false,
        user: null,
        isAuthenticated: false,
        needsRoommateLink: false,
        error: null
      };
    
    case AUTH_ACTIONS.LOGOUT_ERROR:
      return {
        ...state,
        isLoading: false,
        error: action.payload
      };
    
    case AUTH_ACTIONS.LINK_ROOMMATE_START:
      return {
        ...state,
        isLoading: true,
        error: null
      };
    
    case AUTH_ACTIONS.LINK_ROOMMATE_SUCCESS:
      return {
        ...state,
        isLoading: false,
        user: action.payload.user,
        needsRoommateLink: false,
        error: null
      };
    
    case AUTH_ACTIONS.LINK_ROOMMATE_ERROR:
      return {
        ...state,
        isLoading: false,
        error: action.payload
      };
    
    case AUTH_ACTIONS.SHOW_ROOMMATE_LINK:
      return {
        ...state,
        needsRoommateLink: true
      };

    case AUTH_ACTIONS.REFRESH_USER:
      return {
        ...state,
        user: action.payload.user,
        isAuthenticated: !!action.payload.user,
        needsRoommateLink: action.payload.user && !action.payload.user.roommate
      };

    case AUTH_ACTIONS.CLEAR_ERROR:
      return {
        ...state,
        error: null
      };

    default:
      return state;
  }
}

// Auth Provider Component
export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Initialize authentication state
  useEffect(() => {
    const initializeAuth = async () => {
      dispatch({ type: AUTH_ACTIONS.INIT_START });
      
      try {
        // Check if we have OAuth callback parameters in the URL
        const urlParams = new URLSearchParams(window.location.search);
        const authStatus = urlParams.get('auth');
        const needsLinking = urlParams.get('needs_linking');
        const errorMessage = urlParams.get('message');
        
        if (authStatus === 'success') {
          // Handle successful OAuth callback
          try {
            const profileResponse = await authAPI.getProfile();
            const user = profileResponse.data.user;
            
            dispatch({
              type: AUTH_ACTIONS.LOGIN_SUCCESS,
              payload: { 
                user, 
                needsRoommateLink: needsLinking === 'true' 
              }
            });
            
            // Clean up URL parameters
            const cleanUrl = window.location.pathname;
            window.history.replaceState({}, document.title, cleanUrl);
            return;
          } catch (profileError) {
            console.error('Failed to get user profile after OAuth:', profileError);
            dispatch({
              type: AUTH_ACTIONS.LOGIN_ERROR,
              payload: 'Failed to get user profile after authentication'
            });
            return;
          }
        } else if (authStatus === 'error') {
          // Handle OAuth error callback
          dispatch({
            type: AUTH_ACTIONS.LOGIN_ERROR,
            payload: errorMessage || 'Authentication failed'
          });
          
          // Clean up URL parameters
          const cleanUrl = window.location.pathname;
          window.history.replaceState({}, document.title, cleanUrl);
          return;
        }
        
        // Normal initialization (no OAuth callback)
        // Get auth service status
        const statusResponse = await authAPI.getStatus();
        const authServiceStatus = statusResponse.data;
        
        // Try to get current user profile
        let user = null;
        try {
          const profileResponse = await authAPI.getProfile();
          user = profileResponse.data.user;
        } catch (profileError) {
          // User not authenticated, which is fine
          console.log('User not authenticated:', profileError.response?.data?.error);
        }
        
        dispatch({
          type: AUTH_ACTIONS.INIT_SUCCESS,
          payload: { authStatus: authServiceStatus, user }
        });
      } catch (error) {
        console.error('Failed to initialize auth:', error);
        dispatch({
          type: AUTH_ACTIONS.INIT_ERROR,
          payload: error.response?.data?.error || 'Failed to initialize authentication'
        });
      }
    };

    initializeAuth();
  }, []);

  // Login with Google
  const loginWithGoogle = useCallback(async () => {
    dispatch({ type: AUTH_ACTIONS.LOGIN_START });
    
    try {
      // Construct the redirect URI based on current host
      const redirectUri = `${window.location.protocol}//${window.location.host.replace(':3000', ':5002')}/api/auth/callback`;
      
      // Get the OAuth URL
      const response = await authAPI.initiateGoogleLogin(redirectUri);
      const { auth_url } = response.data;
      
      // Redirect to Google OAuth
      window.location.href = auth_url;
      
    } catch (error) {
      console.error('Login failed:', error);
      dispatch({
        type: AUTH_ACTIONS.LOGIN_ERROR,
        payload: error.response?.data?.error || 'Login failed'
      });
    }
  }, []);

  // Handle OAuth callback (called when user returns from Google)
  const handleOAuthCallback = useCallback(async (user, needsRoommateLink) => {
    dispatch({
      type: AUTH_ACTIONS.LOGIN_SUCCESS,
      payload: { user, needsRoommateLink }
    });
  }, []);

  // Link user to roommate
  const linkRoommate = useCallback(async (roommateId) => {
    dispatch({ type: AUTH_ACTIONS.LINK_ROOMMATE_START });

    try {
      console.log('[LINK] Step 1: Calling linkRoommate API...');
      const response = await authAPI.linkRoommate(roommateId);
      const user = response.data.user;
      console.log('[LINK] Step 2: Link API succeeded, user:', user?.email);

      // CRITICAL FIX: Wait for session cookie to propagate through browser
      // Increased from 300ms to 800ms for better reliability in production
      console.log('[LINK] Step 3: Waiting 800ms for session cookie propagation...');
      await new Promise(resolve => setTimeout(resolve, 800));

      // Verify session using SAFE endpoint that doesn't clear session on failure
      // This replaces the dangerous refreshSession() call that could wipe out the session
      console.log('[LINK] Step 4: Verifying roommate link (safe check)...');
      try {
        const verifyResponse = await authAPI.verifyRoommateLink();
        const verifiedUser = verifyResponse.data.user;
        const hasRoommate = verifyResponse.data.has_roommate;

        console.log('[LINK] Step 5: Verification result:', {
          hasRoommate,
          userEmail: verifiedUser?.email,
          roommateId: verifiedUser?.roommate?.id
        });

        // Clear CSRF token BEFORE dispatch to ensure fresh token on retry
        console.log('[LINK] Step 6: Clearing CSRF token for fresh token on next request...');
        clearTokens();

        // Dispatch success to trigger retry
        dispatch({
          type: AUTH_ACTIONS.LINK_ROOMMATE_SUCCESS,
          payload: { user: verifiedUser }
        });

        console.log('[LINK] Step 7: Roommate linking complete. Auto-retry should trigger now.');
        return { success: true, user: verifiedUser };
      } catch (verifyError) {
        console.error('[LINK ERROR] Verification failed:', verifyError);
        console.log('[LINK] Falling back to original user data...');

        // Clear CSRF token before dispatch even on error
        clearTokens();

        // Still dispatch success with original user data
        dispatch({
          type: AUTH_ACTIONS.LINK_ROOMMATE_SUCCESS,
          payload: { user }
        });
        return { success: true, user };
      }
    } catch (error) {
      console.error('[LINK ERROR] Failed to link roommate:', error);
      const errorMessage = error.response?.data?.error || 'Failed to link roommate';
      dispatch({
        type: AUTH_ACTIONS.LINK_ROOMMATE_ERROR,
        payload: errorMessage
      });
      return { success: false, error: errorMessage };
    }
  }, []);

  // Unlink roommate
  const unlinkRoommate = useCallback(async () => {
    try {
      const response = await authAPI.unlinkRoommate();
      const user = response.data.user;
      
      dispatch({
        type: AUTH_ACTIONS.REFRESH_USER,
        payload: { user }
      });
      
      return { success: true, user };
    } catch (error) {
      console.error('Failed to unlink roommate:', error);
      return { success: false, error: error.response?.data?.error || 'Failed to unlink roommate' };
    }
  }, []);

  // Refresh user session
  const refreshUser = useCallback(async () => {
    try {
      const response = await authAPI.refreshSession();
      const user = response.data.user;
      
      dispatch({
        type: AUTH_ACTIONS.REFRESH_USER,
        payload: { user }
      });
      
      return { success: true, user };
    } catch (error) {
      console.error('Failed to refresh user:', error);
      // If refresh fails, user might need to re-authenticate
      dispatch({ type: AUTH_ACTIONS.LOGOUT_SUCCESS });
      return { success: false, error: error.response?.data?.error || 'Session expired' };
    }
  }, []);

  // Logout
  const logout = useCallback(async () => {
    dispatch({ type: AUTH_ACTIONS.LOGOUT_START });
    
    try {
      await authAPI.logout();
      clearTokens(); // Clear CSRF tokens
      dispatch({ type: AUTH_ACTIONS.LOGOUT_SUCCESS });
      return { success: true };
    } catch (error) {
      console.error('Logout failed:', error);
      clearTokens(); // Clear tokens even on error
      dispatch({
        type: AUTH_ACTIONS.LOGOUT_ERROR,
        payload: error.response?.data?.error || 'Logout failed'
      });
      return { success: false, error: error.response?.data?.error || 'Logout failed' };
    }
  }, []);

  // Revoke access and logout
  const revokeAccess = useCallback(async () => {
    dispatch({ type: AUTH_ACTIONS.LOGOUT_START });
    
    try {
      await authAPI.revokeAccess();
      dispatch({ type: AUTH_ACTIONS.LOGOUT_SUCCESS });
      return { success: true };
    } catch (error) {
      console.error('Revoke access failed:', error);
      dispatch({
        type: AUTH_ACTIONS.LOGOUT_ERROR,
        payload: error.response?.data?.error || 'Failed to revoke access'
      });
      return { success: false, error: error.response?.data?.error || 'Failed to revoke access' };
    }
  }, []);

  // Clear error
  const clearError = useCallback(() => {
    dispatch({ type: AUTH_ACTIONS.CLEAR_ERROR });
  }, []);

  // Trigger roommate linking modal
  const showRoommateLink = useCallback(() => {
    dispatch({ type: AUTH_ACTIONS.SHOW_ROOMMATE_LINK });
  }, []);

  // Context value
  const value = {
    // State
    ...state,

    // Actions
    loginWithGoogle,
    handleOAuthCallback,
    linkRoommate,
    unlinkRoommate,
    refreshUser,
    logout,
    revokeAccess,
    clearError,
    showRoommateLink,

    // Computed values
    hasRoommate: state.user && state.user.roommate,
    isConfigured: state.authStatus && state.authStatus.credentials_configured
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// Custom hook to use auth context
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// HOC to wrap components that require authentication
export function withAuth(Component) {
  return function AuthenticatedComponent(props) {
    const { isAuthenticated, isLoading } = useAuth();
    
    if (isLoading) {
      return <div className="loading">Loading...</div>;
    }
    
    if (!isAuthenticated) {
      return <div className="error">Authentication required</div>;
    }
    
    return <Component {...props} />;
  };
}

// HOC to wrap components that require roommate linking
export function withRoommate(Component) {
  return function RoommateLinkedComponent(props) {
    const { isAuthenticated, hasRoommate, isLoading } = useAuth();
    
    if (isLoading) {
      return <div className="loading">Loading...</div>;
    }
    
    if (!isAuthenticated) {
      return <div className="error">Authentication required</div>;
    }
    
    if (!hasRoommate) {
      return <div className="error">Roommate linking required</div>;
    }
    
    return <Component {...props} />;
  };
}