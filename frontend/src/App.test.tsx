import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom'; // Import MemoryRouter
import App from './App'; // App contains HomePage and AuthCallback logic now
import '@testing-library/jest-dom';

// Mock window.location.href
// Store the original window.location
const originalLocation = window.location;

beforeEach(() => {
  // Restore window.location before each test
  // and delete any assigned properties
  window.location = { ...originalLocation, assign: vi.fn() } as any;
  // Clear localStorage before each test
  localStorage.clear();
  vi.clearAllMocks(); // Clear all mocks
});

// Helper to render App with MemoryRouter for a specific route
const renderApp = (initialRoute = '/') => {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <App />
      {/* App itself now contains the <Routes>. If not, wrap specific components like HomePage or AuthCallback in <Routes> here */}
    </MemoryRouter>
  );
};


describe('App Authentication Flow (within HomePage)', () => {
  describe('Unauthenticated User', () => {
    it('renders "Login with Canvas" button', () => {
      renderApp();
      expect(screen.getByRole('button', { name: /Login with Canvas/i })).toBeInTheDocument();
    });

    it('does not render "Logout" button', () => {
      renderApp();
      expect(screen.queryByRole('button', { name: /Logout/i })).not.toBeInTheDocument();
    });

    it('clicking "Login with Canvas" button redirects to backend login URL', () => {
      renderApp();
      const loginButton = screen.getByRole('button', { name: /Login with Canvas/i });
      fireEvent.click(loginButton);
      expect(window.location.href).toBe('http://localhost:8000/auth/login/canvas');
    });
  });

  describe('Authenticated User', () => {
    beforeEach(() => {
      // Simulate authenticated user
      localStorage.setItem('authToken', 'test-jwt-token');
    });

    it('renders "Logout" button', () => {
      renderApp();
      expect(screen.getByRole('button', { name: /Logout/i })).toBeInTheDocument();
    });

    it('does not render "Login with Canvas" button', () => {
      renderApp();
      expect(screen.queryByRole('button', { name: /Login with Canvas/i })).not.toBeInTheDocument();
    });

    it('renders welcome message', () => {
      renderApp();
      expect(screen.getByText(/Welcome! You are logged in./i)).toBeInTheDocument();
    });

    it('clicking "Logout" button clears token and updates UI', () => {
      renderApp();
      const logoutButton = screen.getByRole('button', { name: /Logout/i });

      act(() => {
        fireEvent.click(logoutButton);
      });

      expect(localStorage.getItem('authToken')).toBeNull();
      // UI should update to show Login button again
      expect(screen.getByRole('button', { name: /Login with Canvas/i })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Logout/i })).not.toBeInTheDocument();
    });
  });
});

// Tests for AuthCallback component specifically
// The AuthCallback component is routed via <App />, so we test its behavior by navigating
describe('AuthCallback Component Flow', () => {
  it('stores token from URL and redirects to home', async () => {
    const mockToken = 'mock-jwt-token-from-url';
    renderApp(`/auth/callback?token=${mockToken}`);

    // Check localStorage
    expect(localStorage.getItem('authToken')).toBe(mockToken);

    // Check for navigation to home (HomePage content should appear)
    // useNavigate is mocked by MemoryRouter context, check for HomePage content
    // Need to wait for useEffect and navigate to run.
    // Since navigate('/') happens, the content of HomePage should be visible.
    // We can check for an element that's unique to HomePage when user is now considered authenticated.
    await screen.findByRole('button', { name: /Logout/i }); // HomePage's logout button
    expect(screen.getByText(/Welcome! You are logged in./i)).toBeInTheDocument();
  });

  it('handles error from URL and redirects to home', async () => {
    const mockError = 'canvas_auth_failed';
    // Spy on window.alert
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    renderApp(`/auth/callback?error=${mockError}`);

    // Check alert was called (or other error display logic)
    expect(alertSpy).toHaveBeenCalledWith(`Authentication failed: ${mockError}`);

    // Check for navigation to home (HomePage content for unauthenticated user)
    await screen.findByRole('button', { name: /Login with Canvas/i }); // HomePage's login button
    expect(screen.queryByText(/Welcome! You are logged in./i)).not.toBeInTheDocument();

    alertSpy.mockRestore();
  });

   it('handles no token or error in URL and redirects to home', async () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    renderApp('/auth/callback'); // No query params

    expect(alertSpy).toHaveBeenCalledWith('Authentication callback issue. Please try again.');

    await screen.findByRole('button', { name: /Login with Canvas/i });
    expect(screen.queryByText(/Welcome! You are logged in./i)).not.toBeInTheDocument();

    alertSpy.mockRestore();
  });
});
