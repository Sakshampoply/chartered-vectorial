import React, { useEffect, useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  Chip,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
} from "@mui/material";
import { useAnalysis } from "../../contexts/AnalysisContext";
import { analysisApi } from "../../api/analysisApi";
import { AnalysisResults } from "../../types/index";

export const PreviousAnalysesDashboard: React.FC = () => {
  const { previousAnalyses, clientId, setCurrentPage, fetchClientAnalyses, fetchAnalysisResults } =
    useAnalysis();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisResults | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [clientName, setClientName] = useState("");
  const [clientIdInput, setClientIdInput] = useState(clientId || "");
  const [searchMode, setSearchMode] = useState(!clientId);

  useEffect(() => {
    if (clientId) {
      loadAnalyses(clientId);
    } else {
      setLoading(false);
    }
  }, [clientId]);

  const loadAnalyses = async (id: string) => {
    try {
      setLoading(true);
      setError(null);
      await fetchClientAnalyses(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analyses");
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const idToSearch = clientIdInput || clientId;
    if (idToSearch) {
      loadAnalyses(idToSearch);
    }
  };

  const handleViewDetails = (analysis: AnalysisResults) => {
    setSelectedAnalysis(analysis);
    setShowDetails(true);
  };

  const handleOpenAnalysis = (analysis: AnalysisResults) => {
    fetchAnalysisResults(analysis.analysis_id);
    setShowDetails(false);
  };

  const handleBack = () => {
    setCurrentPage("input");
  };

  if (searchMode && !clientId) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
          p: 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Card sx={{ maxWidth: 500, width: "100%", borderRadius: 3 }}>
          <CardContent sx={{ p: 4 }}>
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
              Find Client Analyses
            </Typography>
            <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
              Enter a client ID to view their investment analyses
            </Typography>

            <form onSubmit={handleSearch}>
              <TextField
                fullWidth
                placeholder="Enter Client ID"
                value={clientIdInput}
                onChange={(e) => setClientIdInput(e.target.value)}
                sx={{ mb: 2 }}
              />
              <Button
                fullWidth
                variant="contained"
                type="submit"
                sx={{
                  background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                }}
              >
                Search
              </Button>
            </form>

            <Button
              fullWidth
              variant="outlined"
              startIcon={<ArrowBackIcon />}
              onClick={handleBack}
              sx={{ mt: 2 }}
            >
              Back
            </Button>
          </CardContent>
        </Card>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #f5f7fa 0%, #c3cfe8 100%)",
        p: 3,
      }}
    >
      <Box sx={{ maxWidth: 1400, mx: "auto" }}>
        {/* Header */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 3,
          }}
        >
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 700, color: "#333", mb: 0.5 }}>
              Analysis History
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Client ID: {clientId}
            </Typography>
          </Box>
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={() => clientId && loadAnalyses(clientId)}
              disabled={loading}
            >
              Refresh
            </Button>
            <Button
              variant="outlined"
              startIcon={<ArrowBackIcon />}
              onClick={handleBack}
            >
              Back
            </Button>
          </Box>
        </Box>

        {/* Error */}
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* Loading */}
        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress />
          </Box>
        ) : previousAnalyses.length === 0 ? (
          <Card sx={{ borderRadius: 3, p: 4, textAlign: "center" }}>
            <Typography variant="h6" color="textSecondary">
              No analyses found for this client
            </Typography>
            <Button
              variant="contained"
              onClick={handleBack}
              sx={{ mt: 2 }}
            >
              Start New Analysis
            </Button>
          </Card>
        ) : (
          <Grid container spacing={3}>
            {previousAnalyses.map((analysis) => (
              <Grid item xs={12} key={analysis.analysis_id}>
                <Card
                  sx={{
                    borderRadius: 2,
                    boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                    transition: "transform 0.2s, boxShadow 0.2s",
                    "&:hover": {
                      transform: "translateY(-4px)",
                      boxShadow: "0 8px 24px rgba(0,0,0,0.15)",
                    },
                  }}
                >
                  <CardContent>
                    <Grid container spacing={2} alignItems="center">
                      {/* Analysis Info */}
                      <Grid item xs={12} sm={6} md={3}>
                        <Box>
                          <Typography variant="caption" color="textSecondary">
                            Analysis Date
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {new Date(analysis.created_at).toLocaleDateString()}
                          </Typography>
                          <Typography variant="caption" color="textSecondary" display="block" sx={{ mt: 0.5 }}>
                            {new Date(analysis.created_at).toLocaleTimeString()}
                          </Typography>
                        </Box>
                      </Grid>

                      {/* Risk Profile */}
                      <Grid item xs={12} sm={6} md={2}>
                        <Box>
                          <Typography variant="caption" color="textSecondary">
                            Risk Profile
                          </Typography>
                          <Box sx={{ mt: 0.5 }}>
                            <Chip
                              label={analysis.client_info.risk_profile?.toUpperCase()}
                              color="primary"
                              size="small"
                            />
                          </Box>
                        </Box>
                      </Grid>

                      {/* Portfolio Value */}
                      <Grid item xs={12} sm={6} md={2}>
                        <Box>
                          <Typography variant="caption" color="textSecondary">
                            Portfolio Value
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            ${analysis.portfolio_analysis?.portfolio_value?.toLocaleString()}
                          </Typography>
                        </Box>
                      </Grid>

                      {/* Sharpe Ratio */}
                      <Grid item xs={12} sm={6} md={2}>
                        <Box>
                          <Typography variant="caption" color="textSecondary">
                            Sharpe Ratio
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {analysis.risk_assessment?.sharpe_ratio?.toFixed(2)}
                          </Typography>
                        </Box>
                      </Grid>

                      {/* Actions */}
                      <Grid item xs={12} md={3} sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
                        <Button
                          variant="outlined"
                          size="small"
                          onClick={() => handleViewDetails(analysis)}
                        >
                          View Details
                        </Button>
                        <Button
                          variant="contained"
                          size="small"
                          onClick={() => handleOpenAnalysis(analysis)}
                        >
                          Open
                        </Button>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Box>

      {/* Details Dialog */}
      {selectedAnalysis && (
        <Dialog open={showDetails} onClose={() => setShowDetails(false)} maxWidth="sm" fullWidth>
          <DialogTitle>Analysis Details</DialogTitle>
          <DialogContent dividers>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <Box>
                <Typography variant="caption" color="textSecondary">
                  Analysis ID
                </Typography>
                <Typography variant="body2">{selectedAnalysis.analysis_id}</Typography>
              </Box>

              <Box>
                <Typography variant="caption" color="textSecondary">
                  Created
                </Typography>
                <Typography variant="body2">
                  {new Date(selectedAnalysis.created_at).toLocaleString()}
                </Typography>
              </Box>

              <Box>
                <Typography variant="caption" color="textSecondary">
                  Duration
                </Typography>
                <Typography variant="body2">
                  {selectedAnalysis.duration_seconds?.toFixed(1)}s
                </Typography>
              </Box>

              <Box>
                <Typography variant="caption" color="textSecondary">
                  Risk Profile
                </Typography>
                <Typography variant="body2">
                  {selectedAnalysis.client_info.risk_profile}
                </Typography>
              </Box>

              <Box>
                <Typography variant="caption" color="textSecondary">
                  Portfolio Value
                </Typography>
                <Typography variant="body2">
                  ${selectedAnalysis.portfolio_analysis?.portfolio_value?.toLocaleString()}
                </Typography>
              </Box>

              <Box>
                <Typography variant="caption" color="textSecondary">
                  Risk Level
                </Typography>
                <Typography variant="body2">
                  {selectedAnalysis.risk_assessment?.risk_level}
                </Typography>
              </Box>

              <Box>
                <Typography variant="caption" color="textSecondary">
                  Sharpe Ratio
                </Typography>
                <Typography variant="body2">
                  {selectedAnalysis.risk_assessment?.sharpe_ratio?.toFixed(3)}
                </Typography>
              </Box>

              <Box>
                <Typography variant="caption" color="textSecondary">
                  Cash On Hand
                </Typography>
                <Typography variant="body2">
                  ${selectedAnalysis.client_info?.cash_on_hand?.toLocaleString()}
                </Typography>
              </Box>

              <Box>
                <Typography variant="caption" color="textSecondary">
                  Monthly Investable Income
                </Typography>
                <Typography variant="body2">
                  ${selectedAnalysis.client_info?.monthly_investable_income?.toLocaleString()}
                </Typography>
              </Box>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowDetails(false)}>Close</Button>
            <Button
              variant="contained"
              onClick={() => handleOpenAnalysis(selectedAnalysis)}
            >
              Open Full Analysis
            </Button>
          </DialogActions>
        </Dialog>
      )}
    </Box>
  );
};
