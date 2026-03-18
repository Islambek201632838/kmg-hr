import React, { useState, useEffect } from 'react';
import { Typography, Box, Button, CircularProgress, Card, CardContent, Chip, Stack, TextField, MenuItem } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import api from '../api/client';

const CRITERION_LABELS = {
  mae: 'Средняя ошибка (MAE)',
  spearman_correlation: 'Корреляция Спирмена',
  type_accuracy: 'Точность типа цели',
  align_accuracy: 'Точность связки',
};

function metricColor(key, value) {
  if (key === 'mae') return value <= 0.15 ? '#4caf50' : value <= 0.25 ? '#ff9800' : '#f44336';
  if (key === 'spearman_correlation') return value >= 0.8 ? '#4caf50' : value >= 0.6 ? '#ff9800' : '#f44336';
  return value >= 80 ? '#4caf50' : value >= 60 ? '#ff9800' : '#f44336';
}

export default function Benchmark() {
  const [employees, setEmployees] = useState([]);
  const [employeeId, setEmployeeId] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/api/employees').then((r) => setEmployees(r.data)).catch(() => {});
  }, []);

  const handleRun = async () => {
    if (!employeeId) return;
    setLoading(true);
    setError('');
    setData(null);
    try {
      const res = await api.get(`/api/benchmark?employee_id=${employeeId}`);
      setData(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Ошибка запуска бенчмарка');
    } finally {
      setLoading(false);
    }
  };

  const chartData = data ? data.results.filter(r => !r.error).map(r => ({
    name: r.goal_text.slice(0, 35) + '...',
    'Эксперт': r.expert_index,
    'AI': r.ai_index,
  })) : [];

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} gutterBottom>Бенчмарк: корреляция с экспертной разметкой</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        10 эталонных целей разной степени качества оцениваются AI и сравниваются с экспертной оценкой.
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
        <TextField
          select label="Сотрудник" value={employeeId}
          onChange={(e) => setEmployeeId(e.target.value)}
          sx={{ minWidth: 300 }} size="small"
        >
          {employees.map((emp) => (
            <MenuItem key={emp.id} value={emp.id}>{emp.full_name} — {emp.position}</MenuItem>
          ))}
        </TextField>
        <Button variant="contained" onClick={handleRun} disabled={loading || !employeeId} size="large">
          {loading ? <><CircularProgress size={20} color="inherit" sx={{ mr: 1 }} /> Оценка 10 целей...</> : 'Запустить бенчмарк'}
        </Button>
      </Box>

      {error && <Typography color="error" sx={{ mt: 2 }}>{error}</Typography>}

      {data && (
        <Box sx={{ mt: 3 }}>
          {/* Metric cards */}
          <Stack direction="row" spacing={2} sx={{ mb: 3 }} flexWrap="wrap">
            {Object.entries(data.metrics).map(([key, value]) => (
              <Card key={key} sx={{ flex: 1, minWidth: 200 }}>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" fontWeight={700} sx={{ color: metricColor(key, value) }}>
                    {key.includes('accuracy') ? `${value}%` : value}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">{CRITERION_LABELS[key]}</Typography>
                </CardContent>
              </Card>
            ))}
          </Stack>

          {/* Interpretation */}
          <Card variant="outlined" sx={{ mb: 3, bgcolor: '#f5f8ff' }}>
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>Интерпретация:</Typography>
              {Object.values(data.interpretation).map((text, i) => (
                <Typography key={i} variant="body2">{text}</Typography>
              ))}
            </CardContent>
          </Card>

          {/* Chart: Expert vs AI */}
          <Card variant="outlined" sx={{ mb: 3, p: 2 }}>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>Эксперт vs AI (по 10 целям)</Typography>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={chartData} margin={{ left: 10, right: 10 }}>
                <XAxis dataKey="name" tick={{ fontSize: 9 }} angle={-20} textAnchor="end" height={70} />
                <YAxis domain={[0, 1]} />
                <Tooltip />
                <Legend />
                <Bar dataKey="Эксперт" fill="#1a3264" radius={[4, 4, 0, 0]} />
                <Bar dataKey="AI" fill="#e8a838" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          {/* Results table */}
          <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1 }}>Детальные результаты:</Typography>
          {data.results.filter(r => !r.error).map((r, i) => (
            <Card key={i} variant="outlined" sx={{ mb: 1 }}>
              <CardContent sx={{ py: 1.5 }}>
                <Typography variant="body2" fontWeight={500}>{r.goal_text}</Typography>
                <Stack direction="row" spacing={1} sx={{ mt: 1 }} flexWrap="wrap">
                  <Chip
                    label={`Эксперт: ${r.expert_index}`}
                    size="small"
                    sx={{ bgcolor: '#1a3264', color: 'white' }}
                  />
                  <Chip
                    label={`AI: ${r.ai_index}`}
                    size="small"
                    sx={{ bgcolor: '#e8a838', color: 'white' }}
                  />
                  <Chip
                    label={`Разница: ${r.diff}`}
                    size="small"
                    color={r.diff <= 0.15 ? 'success' : r.diff <= 0.25 ? 'warning' : 'error'}
                    variant="outlined"
                  />
                  <Chip
                    label={`Тип: ${r.type_match ? 'совпал' : 'не совпал'}`}
                    size="small"
                    color={r.type_match ? 'success' : 'error'}
                    variant="outlined"
                  />
                  <Chip
                    label={`Связка: ${r.align_match ? 'совпала' : 'не совпала'}`}
                    size="small"
                    color={r.align_match ? 'success' : 'error'}
                    variant="outlined"
                  />
                </Stack>
                <Typography variant="caption" color="text.secondary">{r.comment}</Typography>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}
    </Box>
  );
}
