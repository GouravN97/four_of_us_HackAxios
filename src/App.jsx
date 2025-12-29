import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Frame0 from './components/Frame0';
import Frame1 from './components/Frame1';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Frame0 />} />
        <Route path="/dashboard" element={<Frame1 />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
