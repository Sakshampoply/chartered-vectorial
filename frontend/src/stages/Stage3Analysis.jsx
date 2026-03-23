import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Button, Typography, LinearProgress, Card, CardContent } from '@mui/material';
import '../App.css';

const AgentCard = ({ agent, progress }) => (
  <Card sx={{ mb: 2 }}>
    <CardContent>
      <Typography variant="h6">{agent}</Typography>
      <LinearProgress variant="determinate" value={progress} />
      <Typography variant="body2" sx={{ mt: 1 }}>
        Progress: {progress}%
      </Typography>
    </CardContent>
  </Card>
);

const Stage3Analysis = ({ onNext, clientData }) => {
  const navigate = useNavigate();
  const [agentProgress, setAgentProgress] = useState({
    portfolio: 0,
    risk: 0,
    recommendation: 0,
  });
  const [overallProgress, setOverallProgress] = useState(0);
  const [analysisComplete, setAnalysisComplete] = useState(false);

  useEffect(() => {
    // Simulate agent analysis over ~15 seconds
    const interval = setInterval(() => {
      setAgentProgress(prev => {
        const newProgress = { ...prev };
        
        if (newProgress.portfolio < 100) {
          newProgress.portfolio = Math.min(100, newProgress.portfolio + Math.random() * 20);
        }
        if (newProgress.portfolio >= 100 && newProgress.risk < 100) {
          newProgress.risk = Math.min(100, newProgress.risk + Math.random() * 20);
        }
        if (newProgress.risk >= 100 && newProgress.recommendation < 100) {
          newProgress.recommendation = Math.min(100, newProgress.recommendation + Math.random() * 25);
        }

        // Calculate weighted overall progress
        const overall = (
          0.25 * (newProgress.portfolio / 100) +
          0.25 * (newProgress.risk / 100) +
          0.5 * (newProgress.recommendation / 100)
        ) * 100;
        setOverallProgress(overall);

        // Check if all complete
        if (newProgress.portfolio === 100 && newProgress.risk === 100 && newProgress.recommendation === 100) {
          setAnalysisComplete(true);
          return newProgress;
        }

        return newProgress;
      });
    }, 500);

    return () => clearInterval(interval);
  }, []);

  const handleNext = () => {
    if (!analysisComplete) {
      alert('Analysis is still in progress. Please wait.');
      return;
    }
    navigate('/stage4');
  };

  return (
    <div className="stage-container">
      <Typography variant="h4" gutterBottom>Stage 3: AI-Powered Analysis</Typography>
      <Typography variant="body1" paragraph>
        Three specialized agents analyzing your client's portfolio...
      </Typography>

      <div style={{ marginBottom: '20px' }}>
        <Typography variant="body2">Overall Progress: {Math.round(overallProgress)}%</Typography>
        <LinearProgress variant="determinate" value={overallProgress} />
      </div>

      <AgentCard agent="Portfolio Analysis Agent" progress={Math.round(agentProgress.portfolio)} />
      <AgentCard agent="Risk Assessment Agent" progress={Math.round(agentProgress.risk)} />
      <AgentCard agent="Recommendation Agent" progress={Math.round(agentProgress.recommendation)} />

      <Box sx={{ mt: 4, display: 'flex', gap: 2 }}>
        <Button
          variant="contained"
          color="primary"
          onClick={handleNext}
          disabled={!analysisComplete}
        >
          {analysisComplete ? 'Continue to Recommendations' : 'Analyzing...'}
        </Button>
        <Button variant="outlined" onClick={() => navigate('/stage2')}>
          Back
        </Button>
      </Box>
    </div>
  );
};

export default Stage3Analysis;
