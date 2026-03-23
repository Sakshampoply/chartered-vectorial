import React, { useEffect, useState } from "react";
import {
  Box,
  Button,
  CircularProgress,
  Container,
  Grid,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Paper,
  Typography,
  Alert,
  Card,
  CardContent,
  Divider,
} from "@mui/material";
import { useContext } from "react";
import { AnalysisContext } from "../../contexts/AnalysisContext";

interface ClientData {
  client_id: string;
  name: string;
  created_at: string | null;
}

interface AnalysisData {
  analysis_id: string;
  created_at: string | null;
  portfolio_value: number | null;
  risk_profile: string | null;
}

interface ClientAnalysesResponse {
  client_id: string;
  client_name: string;
  analyses_count: number;
  analyses: AnalysisData[];
}

export const ClientBrowser: React.FC = () => {
  const { setCurrentPage, fetchAnalysisResults } = useContext(AnalysisContext)!;

  const [clients, setClients] = useState<ClientData[]>([]);
  const [selectedClient, setSelectedClient] = useState<ClientData | null>(null);
  const [analyses, setAnalyses] = useState<AnalysisData[]>([]);
  const [loadingClients, setLoadingClients] = useState(true);
  const [loadingAnalyses, setLoadingAnalyses] = useState(false);
  const [error, setError] = useState("");

  // Fetch all clients on mount
  useEffect(() => {
    const fetchClients = async () => {
      try {
        setLoadingClients(true);
        const response = await fetch("/api/clients");
        if (!response.ok) throw new Error("Failed to fetch clients");
        const data = await response.json();
        setClients(data);
        setError("");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load clients");
        setClients([]);
      } finally {
        setLoadingClients(false);
      }
    };

    fetchClients();
  }, []);

  // Fetch analyses when client is selected
  const handleSelectClient = async (client: ClientData) => {
    try {
      setSelectedClient(client);
      setLoadingAnalyses(true);
      const response = await fetch(`/api/clients/${client.client_id}/analyses`);
      if (!response.ok) throw new Error("Failed to fetch analyses");
      const data: ClientAnalysesResponse = await response.json();
      setAnalyses(data.analyses);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analyses");
      setAnalyses([]);
    } finally {
      setLoadingAnalyses(false);
    }
  };

  // Navigate to analysis results
  const handleViewAnalysis = async (analysisId: string) => {
    try {
      await fetchAnalysisResults(analysisId);
      setCurrentPage("results");
    } catch (err) {
      setError("Failed to load analysis");
    }
  };

  // Format date for display
  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Unknown date";
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Button
          variant="outlined"
          onClick={() => setCurrentPage("input")}
          sx={{ mb: 2 }}
        >
          ← Back to New Analysis
        </Button>
        <Typography variant="h4" sx={{ fontWeight: 600, color: "#1a1a1a" }}>
          Previous Analyses
        </Typography>
        <Typography variant="body2" sx={{ color: "#666", mt: 1 }}>
          Select a client to view their analysis history
        </Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      <Grid container spacing={3}>
        {/* Clients List */}
        <Grid item xs={12} md={4}>
          <Paper elevation={0} sx={{ border: "1px solid #e0e0e0", height: "100%" }}>
            <Box sx={{ p: 2, borderBottom: "1px solid #e0e0e0", bgcolor: "#f5f5f5" }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Clients ({clients.length})
              </Typography>
            </Box>

            {loadingClients ? (
              <Box sx={{ display: "flex", justifyContent: "center", p: 3 }}>
                <CircularProgress size={24} />
              </Box>
            ) : clients.length === 0 ? (
              <Box sx={{ p: 3, textAlign: "center" }}>
                <Typography variant="body2" sx={{ color: "#999" }}>
                  No clients found
                </Typography>
              </Box>
            ) : (
              <List sx={{ maxHeight: 600, overflow: "auto" }}>
                {clients.map((client) => (
                  <ListItem key={client.client_id} disablePadding>
                    <ListItemButton
                      selected={selectedClient?.client_id === client.client_id}
                      onClick={() => handleSelectClient(client)}
                      sx={{
                        py: 2,
                        "&.Mui-selected": {
                          bgcolor: "#f3e5f5",
                        },
                      }}
                    >
                      <ListItemText
                        primary={client.name}
                        secondary={client.created_at ? formatDate(client.created_at) : ""}
                        primaryTypographyProps={{ variant: "body2", sx: { fontWeight: 500 } }}
                        secondaryTypographyProps={{ variant: "caption" }}
                      />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>

        {/* Analyses List */}
        <Grid item xs={12} md={8}>
          {selectedClient ? (
            <Paper elevation={0} sx={{ border: "1px solid #e0e0e0" }}>
              <Box sx={{ p: 2, borderBottom: "1px solid #e0e0e0", bgcolor: "#f5f5f5" }}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  {selectedClient.name} - Analyses ({analyses.length})
                </Typography>
              </Box>

              {loadingAnalyses ? (
                <Box sx={{ display: "flex", justifyContent: "center", p: 3 }}>
                  <CircularProgress size={24} />
                </Box>
              ) : analyses.length === 0 ? (
                <Box sx={{ p: 3, textAlign: "center" }}>
                  <Typography variant="body2" sx={{ color: "#999" }}>
                    No analyses found for this client
                  </Typography>
                </Box>
              ) : (
                <Box sx={{ p: 2 }}>
                  {analyses.map((analysis, index) => (
                    <React.Fragment key={analysis.analysis_id}>
                      <Card
                        sx={{
                          mb: 2,
                          "&:hover": {
                            boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                            transform: "translateY(-2px)",
                          },
                          transition: "all 0.2s ease",
                          cursor: "pointer",
                        }}
                        onClick={() => handleViewAnalysis(analysis.analysis_id)}
                      >
                        <CardContent>
                          <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                            <Typography variant="body2" sx={{ fontWeight: 600, color: "#1a1a1a" }}>
                              Analysis #{analyses.length - index}
                            </Typography>
                            <Typography variant="caption" sx={{ color: "#999" }}>
                              {analysis.created_at ? formatDate(analysis.created_at) : "Unknown date"}
                            </Typography>
                          </Box>

                          <Divider sx={{ my: 1 }} />

                          <Grid container spacing={2} sx={{ mt: 0.5 }}>
                            <Grid item xs={6}>
                              <Typography variant="caption" sx={{ color: "#666", display: "block" }}>
                                Portfolio Value
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 500, color: "#1a1a1a" }}>
                                {analysis.portfolio_value !== null
                                  ? `£${analysis.portfolio_value.toLocaleString()}`
                                  : "N/A"}
                              </Typography>
                            </Grid>
                            <Grid item xs={6}>
                              <Typography variant="caption" sx={{ color: "#666", display: "block" }}>
                                Risk Profile
                              </Typography>
                              <Typography
                                variant="body2"
                                sx={{
                                  fontWeight: 500,
                                  color:
                                    analysis.risk_profile === "Low"
                                      ? "#4caf50"
                                      : analysis.risk_profile === "Medium"
                                        ? "#ff9800"
                                        : "#f44336",
                                }}
                              >
                                {analysis.risk_profile || "N/A"}
                              </Typography>
                            </Grid>
                          </Grid>

                          <Button
                            variant="text"
                            size="small"
                            sx={{
                              mt: 1.5,
                              color: "#7c3aed",
                              "&:hover": { bgcolor: "#f3e5f5" },
                            }}
                          >
                            View Details →
                          </Button>
                        </CardContent>
                      </Card>
                    </React.Fragment>
                  ))}
                </Box>
              )}
            </Paper>
          ) : (
            <Paper
              elevation={0}
              sx={{
                border: "1px solid #e0e0e0",
                p: 4,
                textAlign: "center",
                bgcolor: "#f9f9f9",
              }}
            >
              <Typography variant="body2" sx={{ color: "#999" }}>
                Select a client from the list to view their analyses
              </Typography>
            </Paper>
          )}
        </Grid>
      </Grid>
    </Container>
  );
};
