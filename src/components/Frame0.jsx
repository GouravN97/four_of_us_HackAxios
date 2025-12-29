import { useNavigate } from 'react-router-dom';
import './Frame0.css';

const Frame0 = () => {
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    navigate('/dashboard');
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
        
        <label className="label hospital-id-label">Hospital ID</label>
        <input type="text" className="input hospital-id-input" />
        
        <label className="label first-name-label">First Name</label>
        <input type="text" className="input first-name-input" />
        
        <label className="label last-name-label">Last Name</label>
        <input type="text" className="input last-name-input" />
        
        <label className="label admin-email-label">Admin email</label>
        <input type="email" className="input admin-email-input" />
        
        <label className="label password-label">Password</label>
        <input type="password" className="input password-input" />
        
        <button className="login-button" onClick={handleLogin}>Log in</button>
      </div>
    </div>
  );
};

export default Frame0;
