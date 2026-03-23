import React from "react";
import { ThemeProvider, createTheme } from "@mui/material";
import { AnalysisProvider, useAnalysis } from "./contexts/AnalysisContext";
import { InputForm } from "./components/InputForm/InputForm";
import { ChatInterface } from "./components/ChatInterface/ChatInterface";
import { ResultsDashboard } from "./components/Dashboard/ResultsDashboard";
import { ClientBrowser } from "./components/ClientBrowser/ClientBrowser";

const theme = createTheme({
  palette: {
    primary: { main: "#667eea" },
  },
});

function AppContent() {
  const { currentPage } = useAnalysis();
  
  if (currentPage === "chat") return <ChatInterface />;
  if (currentPage === "results") return <ResultsDashboard />;
  if (currentPage === "client-browser") return <ClientBrowser />;
  return <InputForm />;
}

function App() {
  return (
    <ThemeProvider theme={theme}>
      <AnalysisProvider>
        <AppContent />
      </AnalysisProvider>
    </ThemeProvider>
  );
}

export default App;

