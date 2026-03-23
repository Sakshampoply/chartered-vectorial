import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Button, Typography } from '@mui/material';
import '../App.css';

const Stage1ProfileGathering = ({ onNext, clientData, setClientData }) => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    age: '',
    portfolio_value: '',
    goals: '',
  });
  const [files, setFiles] = useState([]);
  const [error, setError] = useState('');

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFileUpload = (e) => {
    const newFiles = Array.from(e.target.files);
    setFiles(prev => [...prev, ...newFiles]);
  };

  const handleNext = () => {
    // Validation: at least one text field OR one file
    const hasText = formData.name || formData.goals;
    const hasFiles = files.length > 0;

    if (!hasText && !hasFiles) {
      setError('Please provide either client information or upload documents');
      return;
    }

    // Save data and proceed
    setClientData({ ...formData, files });
    navigate('/stage2');
  };

  return (
    <div className="stage-container">
      <Typography variant="h4" gutterBottom>Stage 1: Client Profile Gathering</Typography>
      <Typography variant="body1" paragraph>
        Enter client information and upload portfolio documents
      </Typography>

      {error && <div className="message error">{error}</div>}

      <div className="form-group">
        <label>Client Name</label>
        <input
          type="text"
          name="name"
          value={formData.name}
          onChange={handleInputChange}
          placeholder="Enter client name"
        />
      </div>

      <div className="form-group">
        <label>Age</label>
        <input
          type="number"
          name="age"
          value={formData.age}
          onChange={handleInputChange}
          placeholder="Client age"
        />
      </div>

      <div className="form-group">
        <label>Portfolio Value ($)</label>
        <input
          type="number"
          name="portfolio_value"
          value={formData.portfolio_value}
          onChange={handleInputChange}
          placeholder="Total portfolio value"
        />
      </div>

      <div className="form-group">
        <label>Investment Goals & Notes</label>
        <textarea
          name="goals"
          value={formData.goals}
          onChange={handleInputChange}
          placeholder="Describe client's goals, timeline, and constraints"
        />
      </div>

      <div className="form-group">
        <label>Upload Portfolio Documents (CSV, TXT, PDF)</label>
        <input
          type="file"
          multiple
          accept=".csv,.txt,.pdf"
          onChange={handleFileUpload}
        />
        {files.length > 0 && (
          <div style={{ marginTop: '10px' }}>
            <strong>Files selected: {files.length}</strong>
            <ul>
              {files.map((f, i) => <li key={i}>{f.name}</li>)}
            </ul>
          </div>
        )}
      </div>

      <Box sx={{ mt: 4, display: 'flex', gap: 2 }}>
        <Button variant="contained" color="primary" onClick={handleNext}>
          Continue to Risk Assessment
        </Button>
      </Box>
    </div>
  );
};

export default Stage1ProfileGathering;
