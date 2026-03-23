const API_BASE = "http://localhost:8000/api";

export const analysisApi = {
  // Onboard client with portfolio in one call
  async onboardClient(clientName: string, file: File, supplementalFiles: File[] = []) {
    const formData = new FormData();
    formData.append("name", clientName);
    formData.append("file", file);
    
    supplementalFiles.forEach((file) => {
      formData.append("supplemental_files", file);
    });

    const res = await fetch(`${API_BASE}/clients/onboarding`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) throw new Error("Failed to onboard client");
    return await res.json();
  },

  // Start a new analysis
  async startAnalysis(clientId: string, portfolioId: string) {
    const res = await fetch(`${API_BASE}/analysis/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        client_id: clientId,
        portfolio_id: portfolioId,
      }),
    });

    if (!res.ok) throw new Error("Failed to start analysis");
    return await res.json();
  },

  // Get question metadata
  async getQuestions(analysisId: string) {
    const res = await fetch(`${API_BASE}/analysis/${analysisId}/info`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!res.ok) throw new Error("Failed to fetch questions");
    return await res.json();
  },

  // Submit answer to a question
  async submitAnswer(analysisId: string, questionId: string, answer: any) {
    const res = await fetch(`${API_BASE}/analysis/${analysisId}/info`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        answer: answer,
      }),
    });
    if (!res.ok) throw new Error("Failed to submit answer");
    return await res.json();
  },

  // Execute analysis
  async executeAnalysis(analysisId: string) {
    const res = await fetch(`${API_BASE}/analysis/${analysisId}/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) throw new Error("Failed to execute analysis");
    return await res.json();
  },

  // Get progress
  async getProgress(analysisId: string) {
    const res = await fetch(`${API_BASE}/analysis/${analysisId}/progress`);
    if (!res.ok) throw new Error("Failed to fetch progress");
    return await res.json();
  },

  // Get results
  async getResults(analysisId: string) {
    const res = await fetch(`${API_BASE}/analysis/${analysisId}/results`);
    if (!res.ok) throw new Error("Failed to fetch results");
    return await res.json();
  },

  // Get all portfolios for file upload
  async uploadPortfolio(clientId: string, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("client_id", clientId);

    const res = await fetch(`${API_BASE}/portfolio/upload`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Failed to upload portfolio");
    return await res.json();
  },

  // Get client portfolios
  async getClientPortfolios(clientId: string) {
    const res = await fetch(`${API_BASE}/clients/${clientId}/portfolios`);
    if (!res.ok) throw new Error("Failed to fetch portfolios");
    return await res.json();
  },

  // Get all analyses for a client
  async getClientAnalyses(clientId: string) {
    const res = await fetch(`${API_BASE}/clients/${clientId}/analyses`);
    if (!res.ok) {
      // If endpoint doesn't exist, return empty array
      // We'll need to implement this on backend if needed
      return [];
    }
    return await res.json();
  },
};
