import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Button, Typography, LinearProgress } from '@mui/material';
import '../App.css';

const Stage2RiskAssessment = ({ onNext, clientData }) => {
  const navigate = useNavigate();
  const [answers, setAnswers] = useState({});
  const [completion, setCompletion] = useState(0);

  const questions = [
    { id: 1, text: 'What is the client\'s investment timeline?' },
    { id: 2, text: 'What is their risk tolerance? (Conservative/Moderate/Aggressive)' },
    { id: 3, text: 'What are their income requirements?' },
    { id: 4, text: 'What liquidity needs do they have?' },
    { id: 5, text: 'Any specific tax considerations?' },
    { id: 6, text: 'Are there any restricted securities or holdings?' },
    { id: 7, text: 'What is their experience level with investments?' },
    { id: 8, text: 'Any other important considerations?' },
  ];

  const handleAnswer = (id, value) => {
    const newAnswers = { ...answers, [id]: value };
    setAnswers(newAnswers);
    
    // Calculate completion percentage
    const answered = Object.keys(newAnswers).length;
    setCompletion(Math.round((answered / questions.length) * 100));
  };

  const handleNext = () => {
    if (completion < 70) {
      alert('Please complete at least 70% of the assessment to continue.');
      return;
    }
    navigate('/stage3');
  };

  return (
    <div className="stage-container">
      <Typography variant="h4" gutterBottom>Stage 2: Risk & Goals Assessment</Typography>
      <Typography variant="body1" paragraph>
        Answer the following questions to understand the client's risk profile
      </Typography>

      <div style={{ marginBottom: '20px' }}>
        <Typography variant="body2">Completion: {completion}%</Typography>
        <LinearProgress variant="determinate" value={completion} />
      </div>

      {questions.map((q) => (
        <div key={q.id} className="form-group">
          <label>{q.text}</label>
          <input
            type="text"
            value={answers[q.id] || ''}
            onChange={(e) => handleAnswer(q.id, e.target.value)}
            placeholder="Your answer"
          />
        </div>
      ))}

      <Box sx={{ mt: 4, display: 'flex', gap: 2 }}>
        <Button variant="contained" color="primary" onClick={handleNext} disabled={completion < 70}>
          Continue to Analysis ({completion}% complete)
        </Button>
        <Button variant="outlined" onClick={() => navigate('/')}>
          Back
        </Button>
      </Box>
    </div>
  );
};

export default Stage2RiskAssessment;
