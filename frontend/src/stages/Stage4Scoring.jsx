import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Button, Typography, Card, CardContent, Grid } from '@mui/material';
import '../App.css';

const ScoreCard = ({ label, score, color, description }) => (
  <Card sx={{ p: 2, backgroundColor: `${color}20`, borderLeft: `4px solid ${color}` }}>
    <CardContent>
      <Typography variant="body2" color="textSecondary" gutterBottom>
        {label}
      </Typography>
      <Typography variant="h3">{score}</Typography>
      <Typography variant="body2" sx={{ mt: 1 }}>
        {description}
      </Typography>
    </CardContent>
  </Card>
);

const Stage4Scoring = ({ onNext, clientData }) => {
  const navigate = useNavigate();

  // Mock scores
  const feasibilityScore = 78;
  const impactScore = 85;

  return (
    <div className="stage-container">
      <Typography variant="h4" gutterBottom>Stage 4: Recommendation Scoring & Decision</Typography>
      <Typography variant="body1" paragraph>
        Review the calculated scores and financial metrics for the recommendation
      </Typography>

      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6}>
          <ScoreCard
            label="Feasibility Score"
            score={feasibilityScore}
            color="#4caf50"
            description="Easy to implement"
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <ScoreCard
            label="Impact Score"
            score={impactScore}
            color="#4caf50"
            description="High impact on goals"
          />
        </Grid>
      </Grid>

      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Financial Metrics</Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
            <div>
              <Typography variant="body2" color="textSecondary">Projected Annual Return</Typography>
              <Typography variant="h5">7.2%</Typography>
            </div>
            <div>
              <Typography variant="body2" color="textSecondary">Expected Portfolio Value (3 years)</Typography>
              <Typography variant="h5">$2,340,000</Typography>
            </div>
            <div>
              <Typography variant="body2" color="textSecondary">Implementation Cost</Typography>
              <Typography variant="h5">$8,500</Typography>
            </div>
            <div>
              <Typography variant="body2" color="textSecondary">Tax Implications</Typography>
              <Typography variant="h5">-$12,000</Typography>
            </div>
          </Box>
        </CardContent>
      </Card>

      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Key Findings</Typography>
          <ul>
            <li><strong>Portfolio:</strong> Over-concentrated in tech (58%), minimal bonds</li>
            <li><strong>Risk:</strong> High correlation risk, downside exposure elevated</li>
            <li><strong>Recommendation:</strong> Rebalance to 50/30/20 stocks/bonds/alternatives</li>
          </ul>
        </CardContent>
      </Card>

      <Box sx={{ mt: 4, display: 'flex', gap: 2 }}>
        <Button variant="contained" color="success" onClick={() => navigate('/stage5')}>
          Implement Strategy
        </Button>
        <Button variant="outlined" color="error">
          Reject
        </Button>
        <Button variant="outlined" onClick={() => navigate('/stage3')}>
          Back
        </Button>
      </Box>
    </div>
  );
};

export default Stage4Scoring;
