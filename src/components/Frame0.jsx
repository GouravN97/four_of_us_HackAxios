import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Frame0.css';

// Valid credentials
// TODO: Replace with database authentication
const VALID_CREDENTIALS = {
  hospitalId: 'H123',
  firstName: 'Harsh',
  lastName: 'Mishra',
  adminEmail: 'h123@gmail.com',
  password: 'orange@123'
};

const Frame0 = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    hospitalId: '',
    firstName: '',
    lastName: '',
    adminEmail: '',
    password: ''
  });
  const [error, setError] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    setError('');
  };

  const handleLogin = (e) => {
    e.preventDefault();
    
    // Validate credentials
    if (
      formData.hospitalId === VALID_CREDENTIALS.hospitalId &&
      formData.firstName === VALID_CREDENTIALS.firstName &&
      formData.lastName === VALID_CREDENTIALS.lastName &&
      formData.adminEmail === VALID_CREDENTIALS.adminEmail &&
      formData.password === VALID_CREDENTIALS.password
    ) {
      navigate('/dashboard');
    } else {
      setError('Invalid credentials. Please try again.');
    }
  };

  return (
    <div className="frame0">
      <div className="background-image" />
      <img src="/assets/images/logo.png" alt="Logo" className="logo" />
      
      {/* Bottom left branding */}
      <img src="/assets/images/logo.png" alt="VERIQ Logo" className="logo-bottom" />
      <span className="brand-name">VERIQ</span>
      <span className="tagline">Intelligent decisions when every minute matters</span>
      
      <div className="login-card">
        <h1 className="title">Log In</h1>
        
        {error && <div className="error-message">{error}</div>}
        
        <label className="label hospital-id-label">Hospital ID</label>
        <input 
          type="text" 
          className="input hospital-id-input" 
          name="hospitalId"
          value={formData.hospitalId}
          onChange={handleChange}
        />
        
        <label className="label first-name-label">First Name</label>
        <input 
          type="text" 
          className="input first-name-input" 
          name="firstName"
          value={formData.firstName}
          onChange={handleChange}
        />
        
        <label className="label last-name-label">Last Name</label>
        <input 
          type="text" 
          className="input last-name-input" 
          name="lastName"
          value={formData.lastName}
          onChange={handleChange}
        />
        
        <label className="label admin-email-label">Admin email</label>
        <input 
          type="email" 
          className="input admin-email-input" 
          name="adminEmail"
          value={formData.adminEmail}
          onChange={handleChange}
        />
        
        <label className="label password-label">Password</label>
        <input 
          type="password" 
          className="input password-input" 
          name="password"
          value={formData.password}
          onChange={handleChange}
        />
        
        <button className="login-button" onClick={handleLogin}>Log in</button>
      </div>
    </div>
  );
};

export default Frame0;
