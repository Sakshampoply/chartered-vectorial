import React, { useState } from 'react';
import { Box, Button, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper } from '@mui/material';
import '../App.css';

const Stage5Dashboard = ({ clientData }) => {
  const [filterDecision, setFilterDecision] = useState('all');

  // Mock portfolio data
  const portfolioData = [
    {
      id: 1,
      clientName: 'John Doe',
      strategy: 'Retirement Rebalancing',
      decision: 'Implemented',
      feasibility: 78,
      impact: 85,
      return: 7.2,
      cost: 8500,
    },
    {
      id: 2,
      clientName: 'Jane Smith',
      strategy: 'Growth Strategy',
      decision: 'Pending',
      feasibility: 65,
      impact: 72,
      return: 9.1,
      cost: 12000,
    },
    {
      id: 3,
      clientName: 'Bob Johnson',
      strategy: 'Conservative Shift',
      decision: 'Rejected',
      feasibility: 42,
      impact: 55,
      return: 4.5,
      cost: 6000,
    },
  ];

  const getDecisionBadgeColor = (decision) => {
    switch (decision) {
      case 'Implemented':
        return '#4caf50';
      case 'Pending':
        return '#ff9800';
      case 'Rejected':
        return '#f44336';
      default:
        return '#757575';
    }
  };

  const filteredData = filterDecision === 'all'
    ? portfolioData
    : portfolioData.filter(r => r.decision === filterDecision);

  return (
    <div className="stage-container">
      <Typography variant="h4" gutterBottom>Stage 5: Portfolio Dashboard</Typography>
      <Typography variant="body1" paragraph>
        View all client recommendations and portfolio analysis
      </Typography>

      <Box sx={{ mb: 4, display: 'flex', gap: 2 }}>
        <Button
          variant={filterDecision === 'all' ? 'contained' : 'outlined'}
          onClick={() => setFilterDecision('all')}
        >
          All
        </Button>
        <Button
          variant={filterDecision === 'Implemented' ? 'contained' : 'outlined'}
          onClick={() => setFilterDecision('Implemented')}
        >
          Implemented
        </Button>
        <Button
          variant={filterDecision === 'Pending' ? 'contained' : 'outlined'}
          onClick={() => setFilterDecision('Pending')}
        >
          Pending
        </Button>
        <Button
          variant={filterDecision === 'Rejected' ? 'contained' : 'outlined'}
          onClick={() => setFilterDecision('Rejected')}
        >
          Rejected
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell><strong>Client</strong></TableCell>
              <TableCell><strong>Strategy</strong></TableCell>
              <TableCell><strong>Decision</strong></TableCell>
              <TableCell align="right"><strong>Feasibility</strong></TableCell>
              <TableCell align="right"><strong>Impact</strong></TableCell>
              <TableCell align="right"><strong>Proj. Return</strong></TableCell>
              <TableCell align="right"><strong>Cost</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredData.map((row) => (
              <TableRow key={row.id}>
                <TableCell>{row.clientName}</TableCell>
                <TableCell>{row.strategy}</TableCell>
                <TableCell>
                  <span
                    style={{
                      display: 'inline-block',
                      padding: '4px 12px',
                      borderRadius: '4px',
                      backgroundColor: getDecisionBadgeColor(row.decision) + '20',
                      color: getDecisionBadgeColor(row.decision),
                      fontWeight: 'bold',
                    }}
                  >
                    {row.decision}
                  </span>
                </TableCell>
                <TableCell align="right">
                  <span style={{ color: row.feasibility >= 75 ? '#4caf50' : row.feasibility >= 50 ? '#ff9800' : '#f44336' }}>
                    {row.feasibility}
                  </span>
                </TableCell>
                <TableCell align="right">
                  <span style={{ color: row.impact >= 75 ? '#4caf50' : row.impact >= 50 ? '#ff9800' : '#f44336' }}>
                    {row.impact}
                  </span>
                </TableCell>
                <TableCell align="right">{row.return}%</TableCell>
                <TableCell align="right">${row.cost.toLocaleString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Box sx={{ mt: 4, display: 'flex', gap: 2 }}>
        <Button variant="contained" color="primary">
          Export PDF Report
        </Button>
        <Button variant="outlined">
          Export Excel
        </Button>
      </Box>
    </div>
  );
};

export default Stage5Dashboard;
