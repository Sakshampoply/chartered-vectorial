// Client & Portfolio
export interface Client {
  id: string;
  name: string;
  created_at: string;
}

export interface Portfolio {
  id: string;
  client_id: string;
  total_value: number;
  holdings: Holding[];
  created_at: string;
}

export interface Holding {
  id: string;
  portfolio_id: string;
  ticker: string;
  quantity: number;
  price: number;
  current_price?: number;
  value: number;
  asset_class: "Equity" | "Fixed Income" | "Cash" | "Alternatives";
  sector?: string;
  industry?: string;
  acquisition_date?: string;
}

// Analysis Flow
export interface AnalysisInfo {
  risk_profile: "conservative" | "moderate" | "aggressive";
  household_income: number;
  cash_on_hand: number;
  monthly_investable_income: number;
  tax_status?: string;
  investment_horizon_months?: number;
  liquidity_needs_pct: number;
  primary_goal?: string;
}

export interface Question {
  id: string;
  order: number;
  text: string;
  help_text?: string;
  required: boolean;
  type: "text" | "number" | "select" | "radio" | "slider";
  options?: { value: string; label: string }[];
  unit?: string;
  placeholder?: string;
}

// Analysis Results
export interface AnalysisResults {
  analysis_id: string;
  created_at: string;
  duration_seconds: number;
  source: "memory" | "database";

  client_info: AnalysisInfo;

  portfolio_analysis: {
    current_allocation: Record<string, number>;
    portfolio_value: number;
    diversification_score: number;
    concentration_risk: number;
    sector_exposure: Record<string, number>;
    asset_class_exposure?: Record<string, number>;
  };

  risk_assessment: {
    sharpe_ratio: number;
    sortino_ratio: number;
    volatility: number;
    beta: number;
    max_drawdown: number;
    var_95: number;
    cvar_95: number;
    risk_level: string;
  };

  recommendation: {
    recommended_allocation: Record<string, number>;
    projected_return: number;
    projected_volatility: number;
    projected_sharpe: number;
    rebalancing_trades: Trade[];
    implementation_cost: number;
    tax_impact: number;
    execution_plan: string;
  };

  summaries: {
    metrics_explanation: Record<string, string>;
    recommendation_rationale: {
      overall_strategy: string;
      trade_rationales: Array<{
        action: string;
        ticker: string;
        shares?: number;
        rationale: string;
      }>;
      benefits: string;
      key_risks?: string;
    };
  };
}

export interface Trade {
  action: "buy" | "sell";
  ticker: string;
  current_quantity: number;
  target_quantity: number;
  quantity_change: number;
  trade_value: number;
  reason: string;
  current_price: number;
}

// Progress Tracking
export interface AnalysisProgress {
  analysis_id: string;
  stage: string;
  overall_progress: number;
  agent_progress: Record<string, number>;
  agent_status: Record<string, string>;
  is_complete: boolean;
  source: "memory" | "database";
  errors?: string[];
}

// Context State
export interface AnalysisContextType {
  // IDs
  clientId: string | null;
  portfolioId: string | null;
  analysisId: string | null;

  // State tracking
  currentPage: "input" | "chat" | "results" | "client-browser";
  clientName: string | null;

  // Analysis data
  analysisInfo: Partial<AnalysisInfo> | null;
  analysisResults: AnalysisResults | null;
  analysisProgress: AnalysisProgress | null;
  previousAnalyses: AnalysisResults[];

  // Actions
  startNewAnalysis: (clientName: string, portfolioId: string) => Promise<void>;
  saveAnalysisInfo: (info: Partial<AnalysisInfo>) => Promise<void>;
  executeAnalysis: () => Promise<void>;
  fetchAnalysisResults: (analysisId: string) => Promise<void>;
  fetchAnalysisProgress: (analysisId: string) => Promise<void>;
  fetchClientAnalyses: (clientId: string) => Promise<void>;
  setCurrentPage: (page: "input" | "chat" | "results" | "client-browser") => void;
  reset: () => void;
}
