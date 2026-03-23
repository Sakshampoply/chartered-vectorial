import React, { createContext, useState, useCallback } from "react";
import {
  AnalysisContextType,
  AnalysisResults,
  AnalysisProgress,
  AnalysisInfo,
} from "../types/index";
import { analysisApi } from "../api/analysisApi";

export const AnalysisContext = createContext<AnalysisContextType | undefined>(
  undefined
);

export const AnalysisProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  // IDs and metadata
  const [clientId, setClientId] = useState<string | null>(null);
  const [portfolioId, setPortfolioId] = useState<string | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [clientName, setClientName] = useState<string | null>(null);

  // UI State
  const [currentPage, setCurrentPage] = useState<
    "input" | "chat" | "results" | "client-browser"
  >("input");

  // Analysis Data
  const [analysisInfo, setAnalysisInfo] = useState<Partial<AnalysisInfo> | null>(
    null
  );
  const [analysisResults, setAnalysisResults] = useState<AnalysisResults | null>(
    null
  );
  const [analysisProgress, setAnalysisProgress] =
    useState<AnalysisProgress | null>(null);
  const [previousAnalyses, setPreviousAnalyses] = useState<AnalysisResults[]>([]);

  // Start new analysis
  const startNewAnalysis = useCallback(
    async (clientId: string, portfolioId: string) => {
      try {
        const startRes = await analysisApi.startAnalysis(clientId, portfolioId);

        setClientId(clientId);
        setPortfolioId(portfolioId);
        setAnalysisId(startRes.analysis_id);
        setCurrentPage("chat");
        setAnalysisInfo({});
        setAnalysisResults(null);
      } catch (error) {
        console.error("Failed to start analysis:", error);
        throw error;
      }
    },
    []
  );

  // Save analysis info
  const saveAnalysisInfo = useCallback(
    async (info: Partial<AnalysisInfo>) => {
      if (!analysisId) throw new Error("No analysis ID");
      try {
        const questions = await analysisApi.getQuestions(analysisId);
        const nextQuestion = questions.find(
          (q: any) =>
            !info[q.id as keyof AnalysisInfo] && q.required
        );

        setAnalysisInfo((prev) => ({ ...prev, ...info }));

        if (!nextQuestion) {
          // All required questions answered, ready to execute
          return true;
        }
        return false;
      } catch (error) {
        console.error("Failed to save analysis info:", error);
        throw error;
      }
    },
    [analysisId]
  );

  // Execute analysis
  const executeAnalysis = useCallback(async () => {
    if (!analysisId) throw new Error("No analysis ID");
    try {
      await analysisApi.executeAnalysis(analysisId);
      setCurrentPage("results");

      // Start polling for progress
      const pollProgress = async () => {
        const progress = await analysisApi.getProgress(analysisId);
        setAnalysisProgress(progress);

        if (progress.is_complete) {
          const results = await analysisApi.getResults(analysisId);
          setAnalysisResults(results);
        } else {
          setTimeout(pollProgress, 2000); // Poll every 2 seconds
        }
      };

      pollProgress();
    } catch (error) {
      console.error("Failed to execute analysis:", error);
      throw error;
    }
  }, [analysisId]);

  // Fetch analysis results
  const fetchAnalysisResults = useCallback(async (analysisId: string) => {
    try {
      const results = await analysisApi.getResults(analysisId);
      setAnalysisResults(results);
      setAnalysisId(analysisId);
      setCurrentPage("results");
    } catch (error) {
      console.error("Failed to fetch results:", error);
      throw error;
    }
  }, []);

  // Fetch analysis progress
  const fetchAnalysisProgress = useCallback(async (analysisId: string) => {
    try {
      const progress = await analysisApi.getProgress(analysisId);
      setAnalysisProgress(progress);
    } catch (error) {
      console.error("Failed to fetch progress:", error);
      throw error;
    }
  }, []);

  // Fetch client's previous analyses
  const fetchClientAnalyses = useCallback(async (clientId: string) => {
    try {
      const analyses = await analysisApi.getClientAnalyses(clientId);
      setPreviousAnalyses(analyses);
    } catch (error) {
      console.error("Failed to fetch client analyses:", error);
      throw error;
    }
  }, []);

  // Reset context
  const reset = useCallback(() => {
    setClientId(null);
    setPortfolioId(null);
    setAnalysisId(null);
    setClientName(null);
    setCurrentPage("input");
    setAnalysisInfo(null);
    setAnalysisResults(null);
    setAnalysisProgress(null);
    setPreviousAnalyses([]);
  }, []);

  const value: AnalysisContextType = {
    clientId,
    portfolioId,
    analysisId,
    currentPage,
    clientName,
    analysisInfo,
    analysisResults,
    analysisProgress,
    previousAnalyses,
    startNewAnalysis,
    saveAnalysisInfo,
    executeAnalysis,
    fetchAnalysisResults,
    fetchAnalysisProgress,
    fetchClientAnalyses,
    setCurrentPage,
    reset,
  };

  return (
    <AnalysisContext.Provider value={value}>{children}</AnalysisContext.Provider>
  );
};

// Hook to use the context
export const useAnalysis = () => {
  const context = React.useContext(AnalysisContext);
  if (!context) {
    throw new Error("useAnalysis must be used within AnalysisProvider");
  }
  return context;
};
