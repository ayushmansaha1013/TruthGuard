 import React, { useState } from 'react';

export default function App() {
  const [activeTab, setActiveTab] = useState('image');
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  // Text state
  const [textInput, setTextInput] = useState('');
  const [textResult, setTextResult] = useState(null);

  // Educator Dashboard Audit Logs
  const [auditLogs] = useState([
    { id: 1, user: 'student1@edu.com', action: 'Image Scan', result: 'Authentic', confidence: '94.2%', time: '10 mins ago' },
    { id: 2, user: 'student2@edu.com', action: 'Text Fact-Check', result: 'Fake/Misleading', confidence: '88.5%', time: '25 mins ago' },
    { id: 3, user: 'student3@edu.com', action: 'Image Scan', result: 'Deepfake Detected', confidence: '97.1%', time: '1 hour ago' },
  ]);

  const handleImageSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImage(URL.createObjectURL(file));
      setResult(null);
    }
  };

  const handleScanImage = () => {
    if (!image) return;
    setLoading(true);
    setResult(null);

    setTimeout(() => {
      setLoading(false);
      setResult({
        isFake: Math.random() > 0.5,
        confidence: (Math.random() * 20 + 78).toFixed(1),
      });
    }, 1500);
  };

  const handleFactCheck = () => {
    if (!textInput.trim()) return;
    setLoading(true);
    setTextResult(null);

    setTimeout(() => {
      setLoading(false);
      setTextResult({
        isTrue: Math.random() > 0.4,
        explanation: "Based on model cross-referencing, this statement contains simulated or unverified claims.",
      });
    }, 1200);
  };

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', maxWidth: '850px', margin: '0 auto', padding: '16px', color: '#1f2937' }}>
      
      {/* Header */}
      <header style={{ borderBottom: '2px solid #e5e7eb', paddingBottom: '12px', marginBottom: '16px' }}>
        <h1 style={{ margin: 0, fontSize: '24px', color: '#111827' }}>TruthGuard Dashboard</h1>
        <p style={{ color: '#6b7280', margin: '4px 0 12px 0', fontSize: '14px' }}>AI Deepfake & Fact-Checking Platform (MVP)</p>
        
        {/* Navigation Tabs */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            onClick={() => setActiveTab('image')}
            style={{
              padding: '8px 14px',
              fontWeight: '600',
              fontSize: '14px',
              background: activeTab === 'image' ? '#2563eb' : '#f3f4f6',
              color: activeTab === 'image' ? '#ffffff' : '#374151',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            🖼️️ Deepfake Detector
          </button>
          
          <button 
            onClick={() => setActiveTab('text')}
            style={{
              padding: '8px 14px',
              fontWeight: '600',
              fontSize: '14px',
              background: activeTab === 'text' ? '#2563eb' : '#f3f4f6',
              color: activeTab === 'text' ? '#ffffff' : '#374151',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            📝 Text Fact-Checker
          </button>

          <button 
            onClick={() => setActiveTab('dashboard')}
            style={{
              padding: '8px 14px',
              fontWeight: '600',
              fontSize: '14px',
              background: activeTab === 'dashboard' ? '#2563eb' : '#f3f4f6',
              color: activeTab === 'dashboard' ? '#ffffff' : '#374151',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            📊 Educator Dashboard
          </button>
        </div>
      </header>

      {/* Main View Area */}
      <main>
        {/* Image Detection Tab */}
        {activeTab === 'image' && (
          <div style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '16px', backgroundColor: '#ffffff', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <h2 style={{ marginTop: 0, fontSize: '18px' }}>Scan Image for Deepfake</h2>
            <p style={{ color: '#6b7280', fontSize: '13px' }}>Upload an image to check if it's real or AI-generated.</p>
            
            <input 
              type="file" 
              accept="image/*" 
              onChange={handleImageSelect} 
              style={{ margin: '8px 0 16px 0', padding: '6px', border: '1px border-dashed #d1d5db', width: '100%' }} 
            />
            
            {image && (
              <div style={{ textAlign: 'center' }}>
                <img src={image} alt="Preview" style={{ maxHeight: '150px', borderRadius: '6px', border: '1px solid #e5e7eb', display: 'block', margin: '0 auto 12px auto' }} />
                
                <button 
                  onClick={handleScanImage}
                  style={{
                    padding: '8px 20px',
                    backgroundColor: '#2563eb',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '6px',
                    fontWeight: '600',
                    fontSize: '14px',
                    cursor: 'pointer'
                  }}
                >
                  🔍 Analyze Image Now
                </button>
              </div>
            )}

            {loading && (
              <p style={{ color: '#2563eb', fontWeight: 'bold', marginTop: '12px', textAlign: 'center', fontSize: '14px' }}>
                ⌛ Analyzing image with AI Model...
              </p>
            )}

            {result && !loading && (
              <div style={{
                marginTop: '12px',
                padding: '12px',
                borderRadius: '8px',
                backgroundColor: result.isFake ? '#fef2f2' : '#f0fdf4',
                border: `1px solid ${result.isFake ? '#fca5a5' : '#86efac'}`,
                color: result.isFake ? '#991b1b' : '#166534',
                textAlign: 'center'
              }}>
                <h3 style={{ margin: 0, fontSize: '16px' }}>
                  {result.isFake ? '⚠️ Deepfake Detected' : '✅ Authentic / Real Image'}
                </h3>
                <p style={{ margin: '4px 0 0 0', fontWeight: '500', fontSize: '13px' }}>Confidence Score: {result.confidence}%</p>
              </div>
            )}
          </div>
        )}

        {/* Text Fact-Checker Tab */}
        {activeTab === 'text' && (
          <div style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '16px', backgroundColor: '#ffffff', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <h2 style={{ marginTop: 0, fontSize: '18px' }}>Fact-Check Claim</h2>
            <p style={{ color: '#6b7280', fontSize: '13px' }}>Enter headline or statement to verify with LLM reasoning engine.</p>
            
            <textarea 
              rows="3" 
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Paste claim or news text here..." 
              style={{ width: '100%', padding: '10px', boxSizing: 'border-box', borderRadius: '6px', border: '1px solid #d1d5db', fontSize: '14px' }}
            />
            
            <button 
              onClick={handleFactCheck}
              style={{ marginTop: '10px', padding: '8px 20px', backgroundColor: '#16a34a', color: '#ffffff', border: 'none', borderRadius: '6px', fontWeight: '600', fontSize: '14px', cursor: 'pointer' }}
            >
              Verify Text
            </button>

            {loading && (
              <p style={{ color: '#16a34a', fontWeight: 'bold', marginTop: '12px', fontSize: '14px' }}>
                ⌛ Checking claims against sources...
              </p>
            )}

            {textResult && !loading && (
              <div style={{
                marginTop: '12px',
                padding: '12px',
                borderRadius: '8px',
                backgroundColor: textResult.isTrue ? '#f0fdf4' : '#fef2f2',
                border: `1px solid ${textResult.isTrue ? '#86efac' : '#fca5a5'}`,
                color: textResult.isTrue ? '#166534' : '#991b1b'
              }}>
                <h3 style={{ margin: 0, fontSize: '16px' }}>
                  {textResult.isTrue ? '✅ Statement Appears Verified' : '❌ Misleading / False Claim'}
                </h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '13px' }}>{textResult.explanation}</p>
              </div>
            )}
          </div>
        )}

        {/* Educator Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '16px', backgroundColor: '#ffffff', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <h2 style={{ marginTop: 0, fontSize: '18px' }}>Educator Audit Logs & Analytics</h2>
            <p style={{ color: '#6b7280', fontSize: '13px' }}>Overview of recent student detection queries stored in Supabase Audit Logs.</p>
            
            <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
              <div style={{ flex: 1, padding: '12px', backgroundColor: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                <span style={{ fontSize: '11px', color: '#6b7280' }}>Total Scans</span>
                <h3 style={{ margin: '2px 0 0 0', fontSize: '20px' }}>128</h3>
              </div>
              <div style={{ flex: 1, padding: '12px', backgroundColor: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                <span style={{ fontSize: '11px', color: '#6b7280' }}>Flagged Deepfakes</span>
                <h3 style={{ margin: '2px 0 0 0', fontSize: '20px', color: '#dc2626' }}>34</h3>
              </div>
            </div>

            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e7eb', color: '#4b5563' }}>
                  <th style={{ padding: '6px' }}>User</th>
                  <th style={{ padding: '6px' }}>Type</th>
                  <th style={{ padding: '6px' }}>Result</th>
                  <th style={{ padding: '6px' }}>Confidence</th>
                  <th style={{ padding: '6px' }}>Time</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '8px 6px' }}>{log.user}</td>
                    <td style={{ padding: '8px 6px' }}>{log.action}</td>
                    <td style={{ padding: '8px 6px', fontWeight: 'bold' }}>{log.result}</td>
                    <td style={{ padding: '8px 6px' }}>{log.confidence}</td>
                    <td style={{ padding: '8px 6px', color: '#6b7280' }}>{log.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}