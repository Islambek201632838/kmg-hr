import React from 'react';
import { Card, CardContent, Typography, Box, LinearProgress, Chip, Stack, Divider, Alert } from '@mui/material';

const CRITERIA_LABELS = {
  specific: 'Specific / Конкретность',
  measurable: 'Measurable / Измеримость',
  achievable: 'Achievable / Достижимость',
  relevant: 'Relevant / Релевантность',
  time_bound: 'Time-bound / Ограниченность во времени',
};

function scoreColor(score) {
  if (score >= 0.8) return 'success';
  if (score >= 0.6) return 'warning';
  return 'error';
}

export default function SmartScoreCard({ evaluation }) {
  if (!evaluation) return null;

  const { goal_text, smart_scores, smart_index, recommendations, improved_goal, alerts } = evaluation;

  return (
    <Card variant="outlined" sx={{ mt: 2, borderLeft: `5px solid ${smart_index >= 0.7 ? '#4caf50' : smart_index >= 0.5 ? '#ff9800' : '#f44336'}` }}>
      <CardContent>
        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, justifyContent: 'space-between', alignItems: { xs: 'flex-start', sm: 'center' }, gap: 1, mb: 2 }}>
          <Typography variant="h6" fontWeight={700} sx={{ fontSize: { xs: '1rem', md: '1.25rem' } }}>SMART-оценка</Typography>
          <Chip
            label={`Индекс: ${smart_index?.toFixed(2)}`}
            sx={{
              fontWeight: 700, fontSize: { xs: '0.9rem', md: '1.1rem' }, px: 2, py: 0.5,
              bgcolor: smart_index >= 0.7 ? '#e8f5e9' : smart_index >= 0.5 ? '#fff8e1' : '#fbe9e7',
              color: smart_index >= 0.7 ? '#2e7d32' : smart_index >= 0.5 ? '#e65100' : '#c62828',
            }}
          />
        </Box>

        {/* SMART scores */}
        {smart_scores && Object.entries(CRITERIA_LABELS).map(([key, label]) => {
          const score = smart_scores[key] ?? 0;
          return (
            <Box key={key} sx={{ mb: 1.5 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="body2" fontWeight={500}>{label}</Typography>
                <Typography variant="body2" fontWeight={700}>{score.toFixed(2)}</Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={score * 100}
                color={scoreColor(score)}
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>
          );
        })}

        <Divider sx={{ my: 2 }} />

        <Typography fontWeight={700} sx={{ fontSize: { xs: '1.3rem', md: '1.5rem' } }}>
          Итоговый SMART-индекс: {smart_index?.toFixed(2)}
        </Typography>

        {/* Recommendations */}
        {recommendations?.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>Рекомендации:</Typography>
            {recommendations.map((r, i) => (
              <Typography key={i} variant="body2" sx={{ ml: 1 }}>• {r}</Typography>
            ))}
          </Box>
        )}

        {/* Improved goal */}
        {improved_goal && (
          <Box sx={{ mt: 2, p: 2, bgcolor: '#fff8e1', borderRadius: 1, borderLeft: '4px solid #e8a838' }}>
            <Typography variant="subtitle2" fontWeight={700} color="#e65100" gutterBottom>
              Предложенная переформулировка:
            </Typography>
            <Typography variant="body1" fontStyle="italic">{improved_goal}</Typography>
          </Box>
        )}

        {/* Alerts */}
        {alerts?.length > 0 && (
          <Stack spacing={1} sx={{ mt: 2 }}>
            {alerts.map((a, i) => (
              <Alert
                key={i}
                severity={a.level === 'critical' ? 'error' : a.level === 'warning' ? 'warning' : 'info'}
                variant="outlined"
              >
                {a.message}
              </Alert>
            ))}
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}
