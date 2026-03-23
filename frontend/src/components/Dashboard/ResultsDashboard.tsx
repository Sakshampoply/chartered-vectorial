import React, { useEffect, useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  LinearProgress,
  Button,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Alert,
  Divider,
  Tabs,
} from "@mui/material";
import Tab from "@mui/material/Tab";
import { useAnalysis } from "../../contexts/AnalysisContext";
import { AnalysisResults } from "../../types/index";

export const ResultsDashboard: React.FC = () => {
  const { analysisResults, analysisProgress, analysisId, setCurrentPage } =
    useAnalysis();

  const [activeTab, setActiveTab] = useState("overview");
  const [isLoading, setIsLoading] = useState(!analysisResults);

  useEffect(() => {
    if (analysisResults) {
      setIsLoading(false);
    }
  }, [analysisResults]);

  if (isLoading || !analysisResults) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Box sx={{ textAlign: "center", color: "white" }}>
          <CircularProgress sx={{ color: "white", mb: 2 }} />
          <Typography variant="h6">
            {analysisProgress?.overall_progress
              ? `Analyzing... ${Math.round(
                  analysisProgress.overall_progress * 100
                )}%`
              : "Loading results..."}
          </Typography>
        </Box>
      </Box>
    );
  }

  const {
    client_info,
    portfolio_analysis,
    risk_assessment,
    recommendation,
    summaries,
    created_at,
    duration_seconds,
  } = analysisResults;

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
        <Box sx={{ mb: 4 }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 2,
            }}
          >
            <Typography
              variant="h4"
              sx={{ fontWeight: 700, color: "#333" }}
            >
              Investment Analysis Results
            </Typography>
            <Button
              variant="outlined"
              onClick={() => setCurrentPage("input")}
            >
              New Analysis
            </Button>
          </Box>
          <Typography variant="body2" color="textSecondary">
            Analysis completed on {new Date(created_at).toLocaleDateString()}{" "}
            in {duration_seconds?.toFixed(1)}s | Risk Profile:{" "}
            <Chip
              label={client_info.risk_profile.toUpperCase()}
              color="primary"
              size="small"
            />
          </Typography>
        </Box>

        {/* Tabs */}
        <Card sx={{ borderRadius: 3, boxShadow: "0 10px 40px rgba(0,0,0,0.1)", mb: 3 }}>
          <Box sx={{ borderBottom: 1, borderColor: "divider", backgroundColor: "background.default", borderRadius: "3px 3px 0 0" }}>
            <Tabs
              value={activeTab}
              onChange={(e, newValue) => setActiveTab(newValue)}
            >
              <Tab label="Overview" value="overview" />
              <Tab label="Portfolio Analysis" value="portfolio" />
              <Tab label="Risk Assessment" value="risk" />
              <Tab label="Recommendations" value="recommendations" />
              <Tab label="Explanations" value="explanations" />
            </Tabs>
          </Box>

          <Box sx={{ p: 3 }}>
            {/* OVERVIEW TAB */}
            {activeTab === "overview" && (
              <Grid container spacing={3}>
                {/* Portfolio Value */}
                <Grid item xs={12} sm={6} md={3}>
                  <Card sx={{ borderRadius: 2, background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" }}>
                    <CardContent>
                      <Typography color="textSecondary" sx={{ color: "white", opacity: 0.8 }}>
                        Portfolio Value
                      </Typography>
                      <Typography
                        variant="h5"
                        sx={{ color: "white", fontWeight: 700, mt: 1 }}
                      >
                        ${portfolio_analysis.portfolio_value?.toLocaleString()}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Risk Level */}
                <Grid item xs={12} sm={6} md={3}>
                  <Card sx={{ borderRadius: 2, background: "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)" }}>
                    <CardContent>
                      <Typography color="textSecondary" sx={{ color: "white", opacity: 0.8 }}>
                        Risk Level
                      </Typography>
                      <Typography
                        variant="h5"
                        sx={{ color: "white", fontWeight: 700, mt: 1 }}
                      >
                        {risk_assessment.risk_level}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Sharpe Ratio */}
                <Grid item xs={12} sm={6} md={3}>
                  <Card sx={{ borderRadius: 2, background: "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)" }}>
                    <CardContent>
                      <Typography color="textSecondary" sx={{ color: "white", opacity: 0.8 }}>
                        Sharpe Ratio
                      </Typography>
                      <Typography
                        variant="h5"
                        sx={{ color: "white", fontWeight: 700, mt: 1 }}
                      >
                        {risk_assessment.sharpe_ratio?.toFixed(2)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Diversification */}
                <Grid item xs={12} sm={6} md={3}>
                  <Card sx={{ borderRadius: 2, background: "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)" }}>
                    <CardContent>
                      <Typography color="textSecondary" sx={{ color: "white", opacity: 0.8 }}>
                        Diversification
                      </Typography>
                      <Typography
                        variant="h5"
                        sx={{ color: "white", fontWeight: 700, mt: 1 }}
                      >
                        {(portfolio_analysis.diversification_score * 100).toFixed(0)}%
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Key Metrics */}
                <Grid item xs={12}>
                  <Card sx={{ borderRadius: 2 }}>
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                        Key Metrics
                      </Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={12} sm={6}>
                          <Box sx={{ mb: 2 }}>
                            <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                              <Typography variant="body2">Volatility</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {(risk_assessment.volatility * 100).toFixed(1)}%
                              </Typography>
                            </Box>
                            <LinearProgress
                              variant="determinate"
                              value={Math.min(risk_assessment.volatility * 100, 100)}
                            />
                          </Box>
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <Box sx={{ mb: 2 }}>
                            <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                              <Typography variant="body2">Beta</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {risk_assessment.beta?.toFixed(2)}
                              </Typography>
                            </Box>
                            <LinearProgress
                              variant="determinate"
                              value={Math.min(risk_assessment.beta * 50, 100)}
                            />
                          </Box>
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <Box>
                            <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                              <Typography variant="body2">Max Drawdown</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {risk_assessment.max_drawdown?.toFixed(1)}%
                              </Typography>
                            </Box>
                            <LinearProgress
                              variant="determinate"
                              value={Math.min(Math.abs(risk_assessment.max_drawdown) * 2, 100)}
                              color="error"
                            />
                          </Box>
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <Box>
                            <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                              <Typography variant="body2">Concentration Risk</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {(portfolio_analysis.concentration_risk * 100).toFixed(0)}%
                              </Typography>
                            </Box>
                            <LinearProgress
                              variant="determinate"
                              value={portfolio_analysis.concentration_risk * 100}
                              color="error"
                            />
                          </Box>
                        </Grid>
                      </Grid>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            )}

            {/* PORTFOLIO TAB */}
            {activeTab === "portfolio" && (
              <Grid container spacing={3}>
                {/* Current Allocation */}
                <Grid item xs={12} md={6}>
                  <Card sx={{ borderRadius: 2 }}>
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                        Current Allocation
                      </Typography>
                      {Object.entries(portfolio_analysis.current_allocation || {}).map(
                        ([asset, value]) => (
                          <Box key={asset} sx={{ mb: 2 }}>
                            <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                              <Typography variant="body2">{asset}</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {(value as number).toFixed(1)}%
                              </Typography>
                            </Box>
                            <LinearProgress variant="determinate" value={value as number} />
                          </Box>
                        )
                      )}
                    </CardContent>
                  </Card>
                </Grid>

                {/* Sector Exposure */}
                <Grid item xs={12} md={6}>
                  <Card sx={{ borderRadius: 2 }}>
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                        Sector Exposure
                      </Typography>
                      {Object.entries(portfolio_analysis.sector_exposure || {}).map(
                        ([sector, value]) => (
                          <Box key={sector} sx={{ mb: 2 }}>
                            <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                              <Typography variant="body2">{sector}</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {(value as number).toFixed(1)}%
                              </Typography>
                            </Box>
                            <LinearProgress
                              variant="determinate"
                              value={value as number}
                              color="success"
                            />
                          </Box>
                        )
                      )}
                    </CardContent>
                  </Card>
                </Grid>

                {/* Summary */}
                <Grid item xs={12}>
                  <Card sx={{ borderRadius: 2, backgroundColor: "#f5f7fa" }}>
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                        Portfolio Analysis
                      </Typography>
                      <Typography variant="body2" color="textSecondary" sx={{ whiteSpace: "pre-wrap" }}>
                        {summaries?.metrics_explanation?.portfolio_composition}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            )}

            {/* RISK TAB */}
            {activeTab === "risk" && (
              <Card sx={{ borderRadius: 2 }}>
                <CardContent>
                  <Grid container spacing={3}>
                    {/* Risk Metrics */}
                    <Grid item xs={12} md={6}>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                        Risk Metrics
                      </Typography>
                      <Table size="small">
                        <TableBody>
                          <TableRow>
                            <TableCell>Sharpe Ratio</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600 }}>
                              {risk_assessment.sharpe_ratio?.toFixed(3)}
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Sortino Ratio</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600 }}>
                              {risk_assessment.sortino_ratio?.toFixed(3)}
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Volatility (Annual)</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600 }}>
                              {(risk_assessment.volatility * 100).toFixed(2)}%
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Beta</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600 }}>
                              {risk_assessment.beta?.toFixed(2)}
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Max Drawdown</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600 }}>
                              {risk_assessment.max_drawdown?.toFixed(2)}%
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Value at Risk (95%)</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600 }}>
                              {risk_assessment.var_95?.toFixed(3)}
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>CVaR (95%)</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600 }}>
                              {risk_assessment.cvar_95?.toFixed(3)}
                            </TableCell>
                          </TableRow>
                        </TableBody>
                      </Table>
                    </Grid>

                    {/* Risk Summary */}
                    <Grid item xs={12} md={6}>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                        Risk Assessment
                      </Typography>
                      <Typography variant="body2" color="textSecondary" sx={{ whiteSpace: "pre-wrap" }}>
                        {summaries?.metrics_explanation?.risk_profile}
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            )}

            {/* RECOMMENDATIONS TAB */}
            {activeTab === "recommendations" && (
              <Grid container spacing={3}>
                {/* Recommended Allocation */}
                <Grid item xs={12} md={6}>
                  <Card sx={{ borderRadius: 2 }}>
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                        Recommended Allocation
                      </Typography>
                      {Object.entries(recommendation.recommended_allocation || {}).map(
                        ([asset, value]) => (
                          <Box key={asset} sx={{ mb: 2 }}>
                            <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                              <Typography variant="body2">{asset}</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {(value as number).toFixed(1)}%
                              </Typography>
                            </Box>
                            <LinearProgress
                              variant="determinate"
                              value={value as number}
                              color="success"
                            />
                          </Box>
                        )
                      )}
                    </CardContent>
                  </Card>
                </Grid>

                {/* Projected Performance */}
                <Grid item xs={12} md={6}>
                  <Card sx={{ borderRadius: 2 }}>
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                        Projected Performance
                      </Typography>
                      <Table size="small">
                        <TableBody>
                          <TableRow>
                            <TableCell>Expected Return</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600 }}>
                              {(recommendation.projected_return * 100).toFixed(2)}%
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Expected Volatility</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600 }}>
                              {(recommendation.projected_volatility * 100).toFixed(2)}%
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Projected Sharpe Ratio</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600 }}>
                              {recommendation.projected_sharpe?.toFixed(3)}
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Implementation Cost</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600 }}>
                              ${recommendation.implementation_cost?.toFixed(2)}
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Tax Impact</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600 }}>
                              ${recommendation.tax_impact?.toFixed(2)}
                            </TableCell>
                          </TableRow>
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Trades */}
                <Grid item xs={12}>
                  <Card sx={{ borderRadius: 2 }}>
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                        Rebalancing Trades
                      </Typography>
                      <TableContainer>
                        <Table>
                          <TableHead>
                            <TableRow sx={{ backgroundColor: "#f5f7fa" }}>
                              <TableCell sx={{ fontWeight: 600 }}>Action</TableCell>
                              <TableCell sx={{ fontWeight: 600 }}>Ticker</TableCell>
                              <TableCell align="right" sx={{ fontWeight: 600 }}>
                                Current Qty
                              </TableCell>
                              <TableCell align="right" sx={{ fontWeight: 600 }}>
                                Target Qty
                              </TableCell>
                              <TableCell align="right" sx={{ fontWeight: 600 }}>
                                Trade Value
                              </TableCell>
                              <TableCell sx={{ fontWeight: 600 }}>Reason</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {recommendation.rebalancing_trades?.map((trade, idx) => (
                              <TableRow key={idx}>
                                <TableCell>
                                  <Chip
                                    label={trade.action.toUpperCase()}
                                    color={trade.action === "buy" ? "success" : "error"}
                                    size="small"
                                  />
                                </TableCell>
                                <TableCell sx={{ fontWeight: 600 }}>{trade.ticker}</TableCell>
                                <TableCell align="right">{trade.current_quantity?.toFixed(0)}</TableCell>
                                <TableCell align="right">{trade.target_quantity?.toFixed(0)}</TableCell>
                                <TableCell align="right">
                                  ${trade.trade_value?.toLocaleString()}
                                </TableCell>
                                <TableCell>{trade.reason}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Execution Plan */}
                <Grid item xs={12}>
                  <Card sx={{ borderRadius: 2, backgroundColor: "#f5f7fa" }}>
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                        Execution Plan
                      </Typography>
                      <Typography variant="body2" color="textSecondary" sx={{ whiteSpace: "pre-wrap" }}>
                        {recommendation.execution_plan}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            )}

            {/* EXPLANATIONS TAB */}
            {activeTab === "explanations" && (
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <Card sx={{ borderRadius: 2 }}>
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                        Overall Strategy
                      </Typography>
                      <Typography variant="body2" color="textSecondary" sx={{ whiteSpace: "pre-wrap" }}>
                        {summaries?.recommendation_rationale?.overall_strategy}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12}>
                  <Card sx={{ borderRadius: 2 }}>
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                        Key Benefits
                      </Typography>
                      <Typography variant="body2" color="textSecondary" sx={{ whiteSpace: "pre-wrap" }}>
                        {summaries?.recommendation_rationale?.benefits}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            )}
          </Box>
        </Card>
      </Box>
    </Box>
  );
};
