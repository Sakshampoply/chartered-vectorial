import React, { useState } from "react";
import {
  Box,
  Paper,
  TextField,
  IconButton,
  Typography,
  CircularProgress,
  Divider,
  Card,
  CardContent,
  Chip,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import CloseIcon from "@mui/icons-material/Close";

interface ChatMessage {
  type: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface AnalysisCopilotProps {
  analysisId: string;
  onClose: () => void;
}

export const AnalysisCopilot: React.FC<AnalysisCopilotProps> = ({
  analysisId,
  onClose,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      type: "assistant",
      content:
        "Hello! I'm your analysis copilot. Ask me any questions about your portfolio analysis, recommendations, or metrics. For example: 'What if I increased bond allocation?' or 'Why was this fund recommended?'",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messageEndRef = React.useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  React.useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [
      ...prev,
      { type: "user", content: userMessage, timestamp: new Date() },
    ]);
    setLoading(true);

    try {
      const response = await fetch(`/api/analysis/${analysisId}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: userMessage }),
      });

      if (!response.ok) {
        throw new Error("Failed to get response");
      }

      const data = await response.json();
      setMessages((prev) => [
        ...prev,
        { type: "assistant", content: data.answer, timestamp: new Date() },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          type: "assistant",
          content: `Sorry, I encountered an error: ${err instanceof Error ? err.message : "Unknown error"}. Please try again.`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "600px",
        backgroundColor: "#f9f9f9",
        borderRadius: 2,
        border: "1px solid #e0e0e0",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          p: 2,
          borderBottom: "1px solid #e0e0e0",
          bgcolor: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        }}
      >
        <Typography variant="h6" sx={{ color: "white", fontWeight: 600 }}>
          Analysis Copilot
        </Typography>
        <IconButton
          size="small"
          onClick={onClose}
          sx={{ color: "white" }}
        >
          <CloseIcon />
        </IconButton>
      </Box>

      {/* Messages */}
      <Box
        sx={{
          flex: 1,
          overflowY: "auto",
          p: 2,
          display: "flex",
          flexDirection: "column",
          gap: 1.5,
        }}
      >
        {messages.map((msg, idx) => (
          <Box
            key={idx}
            sx={{
              display: "flex",
              justifyContent: msg.type === "user" ? "flex-end" : "flex-start",
            }}
          >
            <Card
              sx={{
                maxWidth: "80%",
                backgroundColor:
                  msg.type === "user" ? "#667eea" : "white",
                boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
              }}
            >
              <CardContent
                sx={{
                  py: 1.5,
                  px: 2,
                  "&:last-child": { pb: 1.5 },
                }}
              >
                <Typography
                  variant="body2"
                  sx={{
                    color: msg.type === "user" ? "white" : "#333",
                    lineHeight: 1.6,
                  }}
                >
                  {msg.content}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{
                    display: "block",
                    mt: 0.5,
                    color: msg.type === "user" ? "rgba(255,255,255,0.7)" : "#999",
                  }}
                >
                  {msg.timestamp.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </Typography>
              </CardContent>
            </Card>
          </Box>
        ))}
        {loading && (
          <Box sx={{ display: "flex", justifyContent: "flex-start" }}>
            <Card sx={{ maxWidth: "80%", backgroundColor: "#f0f0f0" }}>
              <CardContent sx={{ py: 1.5, px: 2, "&:last-child": { pb: 1.5 } }}>
                <CircularProgress size={16} />
              </CardContent>
            </Card>
          </Box>
        )}
        <div ref={messageEndRef} />
      </Box>

      {/* Input */}
      <Box
        sx={{
          p: 2,
          borderTop: "1px solid #e0e0e0",
          backgroundColor: "white",
          display: "flex",
          gap: 1,
          alignItems: "flex-end",
        }}
      >
        <TextField
          fullWidth
          placeholder="Ask a question about your analysis..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={loading}
          multiline
          maxRows={3}
          size="small"
          sx={{
            "& .MuiOutlinedInput-root": {
              borderRadius: 2,
            },
          }}
        />
        <IconButton
          onClick={handleSend}
          disabled={!input.trim() || loading}
          sx={{
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            color: "white",
            "&:hover": {
              background: "linear-gradient(135deg, #5568d3 0%, #6a3d8c 100%)",
            },
            "&:disabled": {
              background: "#ccc",
              color: "#999",
            },
          }}
        >
          <SendIcon />
        </IconButton>
      </Box>
    </Box>
  );
};
