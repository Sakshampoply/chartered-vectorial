import React, { useState } from "react";
import {
  Box,
  Button,
  TextField,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Paper,
  Divider,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import { useAnalysis } from "../../contexts/AnalysisContext";
import { analysisApi } from "../../api/analysisApi";

export const InputForm: React.FC = () => {
  const { startNewAnalysis, setCurrentPage } = useAnalysis();

  const [clientName, setClientName] = useState("");
  const [portfolioFile, setPortfolioFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setPortfolioFile(file);
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (!clientName.trim()) {
        throw new Error("Please enter a client name");
      }

      if (!portfolioFile) {
        throw new Error("Please upload a portfolio file");
      }

      setUploadProgress(33);

      // Onboard client with portfolio
      const onboardRes = await analysisApi.onboardClient(clientName, portfolioFile);
      
      setUploadProgress(66);

      // Start the analysis using the returned client and portfolio IDs
      await startNewAnalysis(onboardRes.client_id, onboardRes.portfolio_id);

      setUploadProgress(100);
      setClientName("");
      setPortfolioFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      setUploadProgress(0);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        p: 2,
      }}
    >
      <Card
        sx={{
          maxWidth: 600,
          width: "100%",
          boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
          borderRadius: 3,
        }}
      >
        <CardContent sx={{ p: 4 }}>
          {/* Header */}
          <Typography
            variant="h3"
            sx={{
              fontWeight: 700,
              mb: 1,
              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
              backgroundClip: "text",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            Chartered Vectorial
          </Typography>
          <Typography
            variant="subtitle1"
            color="textSecondary"
            sx={{ mb: 4, fontWeight: 500 }}
          >
            AI-Powered Investment Analysis
          </Typography>

          <Divider sx={{ mb: 4 }} />

          {/* Form */}
          <form onSubmit={handleSubmit}>
            {error && (
              <Alert severity="error" sx={{ mb: 3 }}>
                {error}
              </Alert>
            )}

            {/* Client Name Input */}
            <Typography
              variant="subtitle2"
              sx={{ fontWeight: 600, mb: 1, color: "textPrimary" }}
            >
              Client Name
            </Typography>
            <TextField
              fullWidth
              placeholder="Enter client name"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              disabled={loading}
              sx={{
                mb: 3,
                "& .MuiOutlinedInput-root": {
                  borderRadius: 2,
                },
              }}
            />

            {/* File Upload */}
            <Typography
              variant="subtitle2"
              sx={{ fontWeight: 600, mb: 1, color: "textPrimary" }}
            >
              Portfolio Document
            </Typography>
            <Paper
              variant="outlined"
              sx={{
                p: 2.5,
                textAlign: "center",
                border: "2px dashed",
                borderColor: portfolioFile ? "primary.main" : "divider",
                borderRadius: 2,
                backgroundColor: portfolioFile
                  ? "primary.light"
                  : "background.default",
                cursor: "pointer",
                transition: "all 0.3s ease",
                mb: 3,
                minHeight: 140,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                "&:hover": {
                  borderColor: "primary.main",
                  backgroundColor: "primary.light",
                },
              }}
              component="label"
            >
              <input
                hidden
                type="file"
                accept=".csv,.xlsx,.xls,.pdf"
                onChange={handleFileChange}
                disabled={loading}
              />
              <CloudUploadIcon
                sx={{
                  fontSize: 48,
                  color: portfolioFile ? "primary.main" : "textSecondary",
                  mb: 1,
                }}
              />
              <Typography
                variant="body2"
                sx={{
                  color: portfolioFile ? "primary.main" : "textSecondary",
                  fontWeight: 500,
                }}
              >
                {portfolioFile
                  ? `✓ ${portfolioFile.name}`
                  : "Click to upload or drag and drop"}
              </Typography>
              <Typography
                variant="caption"
                color="textSecondary"
                sx={{ display: "block", mt: 1 }}
              >
                CSV, Excel, or PDF files accepted
              </Typography>
            </Paper>

            {/* Progress Bar */}
            {uploadProgress > 0 && uploadProgress < 100 && (
              <Box sx={{ mb: 3 }}>
                <Box
                  sx={{
                    height: 8,
                    backgroundColor: "background.default",
                    borderRadius: 4,
                    overflow: "hidden",
                  }}
                >
                  <Box
                    sx={{
                      height: "100%",
                      width: `${uploadProgress}%`,
                      background:
                        "linear-gradient(90deg, #667eea 0%, #764ba2 100%)",
                      transition: "width 0.3s ease",
                    }}
                  />
                </Box>
              </Box>
            )}

            {/* Submit Button */}
            <Button
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              disabled={loading || !clientName.trim() || !portfolioFile}
              sx={{
                background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                textTransform: "none",
                fontSize: 16,
                fontWeight: 600,
                borderRadius: 2,
                p: 1.5,
              }}
            >
              {loading ? (
                <>
                  <CircularProgress size={20} sx={{ mr: 1, color: "white" }} />
                  Analyzing...
                </>
              ) : (
                "Start Analysis"
              )}
            </Button>
          </form>

          {/* Info */}
          <Box sx={{ mt: 4, p: 2, backgroundColor: "background.default", borderRadius: 2 }}>
            <Typography variant="caption" color="textSecondary" display="block">
              💡 Your portfolio analysis will:
            </Typography>
            <Typography variant="caption" color="textSecondary" display="block" sx={{ mt: 1 }}>
              • Assess current allocation and risk
            </Typography>
            <Typography variant="caption" color="textSecondary" display="block">
              • Answer 7 quick questions about your goals
            </Typography>
            <Typography variant="caption" color="textSecondary" display="block">
              • Generate AI-powered recommendations
            </Typography>
          </Box>

          {/* Browse Previous Analyses */}
          <Box sx={{ mt: 4, p: 3, backgroundColor: "#f0f4ff", borderRadius: 2, border: "2px dashed #764ba2" }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, color: "#333" }}>
              View Previous Analyses
            </Typography>
            <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
              Browse all clients and their analysis history.
            </Typography>
            <Button
              fullWidth
              variant="outlined"
              onClick={() => setCurrentPage("client-browser")}
              sx={{
                color: "#764ba2",
                borderColor: "#764ba2",
                fontWeight: 600,
                "&:hover": {
                  borderColor: "#667eea",
                  backgroundColor: "rgba(118, 75, 162, 0.05)",
                },
              }}
            >
              Browse All Analyses →
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};
