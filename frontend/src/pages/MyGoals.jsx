import React, { useState, useEffect } from 'react';
import { TextField, MenuItem, Button, Typography, Box, CircularProgress, Card, CardContent, Chip, Stack, LinearProgress } from '@mui/material';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer } from 'recharts';
import api from '../api/client';
import AlertBanner from '../components/AlertBanner';

const GOAL_TYPE_LABELS = {
  activity: 'Активность',
  output: 'Результат',
  impact: 'Влияние на бизнес',
};

const ALIGN_LABELS = {
  strategic: 'Стратегическая',
  functional: 'Функциональная',
  operational: 'Операционная',
};

const CRITERION_LABELS = {
  specific: 'Конкретность',
  measurable: 'Измеримость',
  achievable: 'Достижимость',
  relevant: 'Релевантность',
  time_bound: 'Сроки',
};

export default function MyGoals() {
  const [employees, setEmployees] = useState([]);
  const [employeeId, setEmployeeId] = useState('');
  const [quarter, setQuarter] = useState('Q1');
  const [year, setYear] = useState(2025);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/api/employees').then((r) => setEmployees(r.data)).catch(() => {});
  }, []);

  const handleEvaluate = async () => {
    if (!employeeId) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await api.post('/api/evaluate-batch', {
        employee_id: Number(employeeId),
        quarter,
        year,
      });
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Ошибка пакетной оценки');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} gutterBottom>Мои цели — пакетная оценка</Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <TextField
          select label="Сотрудник" value={employeeId}
          onChange={(e) => setEmployeeId(e.target.value)}
          sx={{ minWidth: 300 }} size="small"
        >
          {employees.map((emp) => (
            <MenuItem key={emp.id} value={emp.id}>{emp.full_name} — {emp.position}</MenuItem>
          ))}
        </TextField>
        <TextField select label="Квартал" value={quarter} onChange={(e) => setQuarter(e.target.value)} size="small" sx={{ width: 120 }}>
          {['Q1', 'Q2', 'Q3', 'Q4'].map((q) => <MenuItem key={q} value={q}>{q}</MenuItem>)}
        </TextField>
        <TextField label="Год" type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} size="small" sx={{ width: 100 }} />
        <Button variant="contained" onClick={handleEvaluate} disabled={loading || !employeeId}>
          {loading ? <CircularProgress size={24} color="inherit" /> : 'Оценить все цели'}
        </Button>
      </Box>

      {error && <AlertBanner warnings={[error]} />}

      {result && (
        <>
          <Card variant="outlined" sx={{ mb: 2, bgcolor: '#f5f8ff' }}>
            <CardContent>
              <Typography variant="h6">{result.employee_name} — {result.department}</Typography>
              <Stack direction="row" spacing={2} sx={{ mt: 1 }} flexWrap="wrap">
                <Chip label={`Средний индекс: ${result.summary.avg_index}`} color={result.summary.avg_index >= 0.7 ? 'success' : 'warning'} />
                <Chip label={`Целей: ${result.summary.total_goals}`} variant="outlined" />
                <Chip label={`Вес: ${result.summary.total_weight}%`} variant="outlined" />
                <Chip label={`Слабый критерий: ${CRITERION_LABELS[result.summary.weakest_criterion] || result.summary.weakest_criterion}`} color="error" variant="outlined" />
              </Stack>
              <AlertBanner warnings={result.summary.warnings} />
            </CardContent>
          </Card>

          {/* Radar chart: avg SMART per criterion across all goals */}
          {result.goals.length > 0 && (() => {
            const avgScores = Object.keys(CRITERION_LABELS).map(k => {
              const evals = result.goals.filter(g => g.smart_scores).map(g => g.smart_scores?.[k] ?? 0);
              return { criterion: CRITERION_LABELS[k], score: evals.length ? +(evals.reduce((a,b)=>a+b,0)/evals.length).toFixed(2) : 0 };
            });
            return (
              <Card variant="outlined" sx={{ mb: 2, p: 1 }}>
                <Typography variant="subtitle2" sx={{ px: 1, pt: 0.5 }}>Профиль SMART (все цели)</Typography>
                <ResponsiveContainer width="100%" height={200}>
                  <RadarChart data={avgScores}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="criterion" tick={{ fontSize: 11 }} />
                    <Radar dataKey="score" stroke="#1a3264" fill="#1a3264" fillOpacity={0.25} />
                  </RadarChart>
                </ResponsiveContainer>
              </Card>
            );
          })()}

          {result.goals.map((g) => (
            <Card key={g.goal_id} variant="outlined" sx={{ mb: 1 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Typography variant="body1" sx={{ flex: 1 }}>{g.goal_text}</Typography>
                  <Stack direction="row" spacing={1} sx={{ ml: 2, flexShrink: 0 }}>
                    <Chip label={g.overall_index.toFixed(2)} color={g.overall_index >= 0.7 ? 'success' : 'warning'} size="small" />
                    <Chip label={GOAL_TYPE_LABELS[g.goal_type] || g.goal_type} size="small" />
                    <Chip label={ALIGN_LABELS[g.alignment_level] || g.alignment_level} size="small" variant="outlined" />
                  </Stack>
                </Box>
                {g.smart_scores && (
                  <Box sx={{ mt: 1 }}>
                    {Object.entries(CRITERION_LABELS).map(([k, label]) => (
                      <Box key={k} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.4 }}>
                        <Typography variant="caption" sx={{ minWidth: 100 }}>{label}</Typography>
                        <LinearProgress
                          variant="determinate"
                          value={(g.smart_scores[k] ?? 0) * 100}
                          color={g.smart_scores[k] >= 0.7 ? 'success' : g.smart_scores[k] >= 0.5 ? 'warning' : 'error'}
                          sx={{ flex: 1, height: 5, borderRadius: 3 }}
                        />
                        <Typography variant="caption" sx={{ minWidth: 28 }}>{(g.smart_scores[k] ?? 0).toFixed(2)}</Typography>
                      </Box>
                    ))}
                  </Box>
                )}
              </CardContent>
            </Card>
          ))}
        </>
      )}
    </Box>
  );
}
