import { useState, useEffect } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import './App.css'; // You can keep or modify this

// Define the backend URL
const BACKEND_URL = 'http://localhost:8000';

// Component for the Auth Callback
function AuthCallback() {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const token = params.get('token');
    const error = params.get('error'); // Optional: if backend redirects with error

    if (token) {
      localStorage.setItem('authToken', token);
      // You might want to fetch user details here with the token
      // For now, just redirect to home
      navigate('/');
    } else if (error) {
      // Handle error, maybe display it to the user
      console.error('Authentication error:', error);
      alert(`Authentication failed: ${error}`);
      navigate('/'); // Or to a login error page
    } else {
      // No token or error, something unexpected
      console.error('No token or error found in callback.');
      alert('Authentication callback issue. Please try again.');
      navigate('/');
    }
  }, [navigate, location]);

  return (
    <div>
      <h2>Loading...</h2>
      <p>Processing authentication callback.</p>
    </div>
  );
}

// Main App Component / Home Page
function HomePage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  // Placeholder for user info, could be fetched after auth
  // const [user, setUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('authToken');
    if (token) {
      setIsAuthenticated(true);
      // Optionally: Fetch user details from backend using the token
      // and set them in `user` state.
    } else {
      setIsAuthenticated(false);
    }
  }, []);

  const handleCanvasLogin = () => {
    window.location.href = `${BACKEND_URL}/auth/login/canvas`;
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    setIsAuthenticated(false);
    // setUser(null);
    navigate('/'); // Navigate to home, which will show login button
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>My Canvas Integrated App</h1>
        {isAuthenticated ? (
          <div>
            <p>Welcome! You are logged in.</p>
            {/* Placeholder for user info display */}
            {/* user && <p>Email: {user.email}</p> */}
            <button onClick={handleLogout} style={{ marginLeft: '10px', padding: '10px' }}>
              Logout
            </button>
          </div>
        ) : (
          <button onClick={handleCanvasLogin} style={{ padding: '10px 20px', fontSize: '16px' }}>
            Login with Canvas
          </button>
        )}
      </header>
      <main>
        {/* Content for authenticated users can go here */}
        {isAuthenticated && (
          <div>
            <h2>Dashboard</h2>
            <p>Your personalized content here.</p>
          </div>
        )}
      </main>
    </div>
  );
}

// App component with routing
function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      {/* Add other routes here */}
    </Routes>
  );
}

export default App;
