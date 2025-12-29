import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Frame0 from './components/Frame0';
import Frame1 from './components/Frame1';
import Frame2 from './components/Frame2';
import Frame3 from './components/Frame3';
import Frame4 from './components/Frame4';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Frame0 />} />
        <Route path="/dashboard" element={<Frame1 />} />
        <Route path="/er" element={<Frame2 />} />
        <Route path="/icu" element={<Frame3 />} />
        <Route path="/patient-log" element={<Frame4 />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
