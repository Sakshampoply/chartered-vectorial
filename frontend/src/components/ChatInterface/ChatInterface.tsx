import React, { useState, useEffect, useRef } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  TextField,
  Typography,
  CircularProgress,
  RadioGroup,
  FormControlLabel,
  Radio,
  Select,
  MenuItem,
  Slider,
  Alert,
  Paper,
  Divider,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import { useAnalysis } from "../../contexts/AnalysisContext";
import { analysisApi } from "../../api/analysisApi";
import { Question } from "../../types/index";

export const ChatInterface: React.FC = () => {
  const { analysisId, analysisInfo, saveAnalysisInfo, executeAnalysis, setCurrentPage } =
    useAnalysis();

  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [currentQuestionIndex]);

  // Load first question on mount
  useEffect(() => {
    const loadFirstQuestion = async () => {
      if (!analysisId) return;
      try {
        setLoading(true);
        const questionData = await analysisApi.getQuestions(analysisId);
        setQuestions([questionData]); // Store single question as array element
        setError(null);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load first question"
        );
      } finally {
        setLoading(false);
      }
    };

    loadFirstQuestion();
  }, [analysisId]);

  const currentQuestion = questions.length > 0 ? questions[currentQuestionIndex] : null;
  const progress = currentQuestion ? (currentQuestion.question_number || 1) / 8 * 100 : 0;
  const canSubmitQuestion = currentQuestion && answers[currentQuestion.question_type];

  const handleAnswerChange = (questionId: string, value: any) => {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: value,
    }));
  };

  const handleNext = async () => {
    if (!currentQuestion || !analysisId) return;

    setIsSubmitting(true);
    try {
      // Validate required answer
      if (currentQuestion.is_required && !answers[currentQuestion.question_type]) {
        setError(`${currentQuestion.question} is required`);
        setIsSubmitting(false);
        return;
      }

      // Submit answer to backend
      const answer = answers[currentQuestion.question_type];
      if (answer !== undefined && answer !== null) {
        const response = await analysisApi.submitAnswer(
          analysisId,
          currentQuestion.question_type,
          answer
        );
        
        // Check if analysis is complete
        if (response.status === "complete") {
          // All questions answered, ready to execute
          setCurrentPage("results");
          await executeAnalysis(analysisId);
          return;
        }
        
        // Fetch next question
        const nextQuestion = await analysisApi.getQuestions(analysisId);
        setQuestions([nextQuestion]);
        setCurrentQuestionIndex(0);
        setAnswers({});
        setError(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save answer");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleComplete = async () => {
    setIsSubmitting(true);
    try {
      // Execute analysis
      if (!analysisId) {
        setError("No analysis ID found");
        return;
      }
      await executeAnalysis(analysisId);
      setCurrentPage("results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to complete analysis");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: "100vh",
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (!currentQuestion) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography variant="h6" color="error">
          No questions available
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        p: 2,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box sx={{ maxWidth: 700, width: "100%", mx: "auto", flex: 1 }}>
        {/* Header */}
        <Box sx={{ mb: 3 }}>
          <Typography
            variant="h5"
            sx={{
              color: "white",
              fontWeight: 700,
              mb: 1,
            }}
          >
            Investment Assessment
          </Typography>
          <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.8)" }}>
            Question {currentQuestionIndex + 1} of {questions.length}
          </Typography>
        </Box>

        {/* Progress Bar */}
        <Box sx={{ mb: 3, height: 4, backgroundColor: "rgba(255,255,255,0.2)", borderRadius: 2, overflow: "hidden" }}>
          <Box
            sx={{
              height: "100%",
              width: `${progress}%`,
              backgroundColor: "white",
              transition: "width 0.3s ease",
            }}
          />
        </Box>

        {/* Messages / Chat Area */}
        <Box
          sx={{
            mb: 3,
            height: "auto",
            maxHeight: 450,
            overflowY: "auto",
          }}
        >
          {/* Question Card */}
          <Card
            sx={{
              mb: 2,
              backgroundColor: "white",
              borderRadius: 2,
            }}
          >
            <CardContent>
              <Typography
                variant="h6"
                sx={{
                  fontWeight: 600,
                  mb: 1,
                }}
              >
                {currentQuestion.question}
              </Typography>
              {currentQuestion.help_text && (
                <Typography
                  variant="body2"
                  color="textSecondary"
                  sx={{ mb: 2, fontStyle: "italic" }}
                >
                  {currentQuestion.help_text}
                </Typography>
              )}
            </CardContent>
          </Card>

          {/* Error */}
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {/* Answer Input */}
          <Card sx={{ borderRadius: 2 }}>
            <CardContent>
              <TextField
                fullWidth
                placeholder="Enter your answer"
                value={answers[currentQuestion.question_type] || ""}
                onChange={(e) =>
                  handleAnswerChange(currentQuestion.question_type, e.target.value)
                }
                autoFocus
                sx={{
                  "& .MuiOutlinedInput-root": {
                    borderRadius: 1,
                  },
                }}
              />
            </CardContent>
          </Card>

          <div ref={messagesEndRef} />
        </Box>

        {/* Divider */}
        <Divider sx={{ backgroundColor: "rgba(255,255,255,0.2)", mb: 2 }} />

        {/* Action Buttons */}
        <Box sx={{ display: "flex", gap: 1 }}>
          {currentQuestion ? (
            <Button
              variant="contained"
              fullWidth
              onClick={handleNext}
              disabled={isSubmitting || !answers[currentQuestion.question_type]}
              endIcon={<SendIcon />}
              sx={{
                backgroundColor: "white",
                color: "#667eea",
                fontWeight: 600,
                "&:hover": {
                  backgroundColor: "#f0f0f0",
                },
              }}
            >
              {isSubmitting ? "Saving..." : "Next"}
            </Button>
          ) : null}
        </Box>
      </Box>
    </Box>
  );
};
