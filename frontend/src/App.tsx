import { Routes, Route } from 'react-router-dom';

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Routes>
        <Route path="/" element={<div>Welcome to VoiceCheck</div>} />
      </Routes>
    </div>
  );
}

export default App;
