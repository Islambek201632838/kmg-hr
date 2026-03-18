import React, { useState, useEffect } from 'react';
import { Typography, Box, Card, CardContent, Chip, Stack, CircularProgress, LinearProgress, TextField, MenuItem } from '@mui/material';
import api from '../api/client';

const CRITERION_LABELS = {
  'Конкретность': 'S',
  'Измеримость': 'M',
  'Достижимость': 'A',
  'Релевантность': 'R',
  'Сроки': 'T',
};

function scoreColor(val) {
  if (val >= 0.8) return 'success';
  if (val >= 0.6) return 'warning';
  return 'error';
}

export default function Team() {
  const [departments, setDepartments] = useState([]);
  const [selectedDept, setSelectedDept] = useState('');
  const [employees, setEmployees] = useState([]);
  const [maturity, setMaturity] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get('/api/dashboard/department-quality?year=2025')
      .then((r) => setDepartments(r.data.departments))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedDept) return;
    setLoading(true);
    Promise.all([
      api.get(`/api/employees?department_id=${selectedDept}`),
      api.get(`/api/dashboard/maturity?department_id=${selectedDept}`),
    ])
      .then(([empRes, matRes]) => {
        setEmployees(empRes.data);
        setMaturity(matRes.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selectedDept]);

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} gutterBottom>Команда — зрелость целеполагания</Typography>

      <TextField
        select label="Подразделение" value={selectedDept}
        onChange={(e) => setSelectedDept(e.target.value)}
        sx={{ minWidth: 400, mb: 3 }} size="small"
      >
        {departments.map((d) => (
          <MenuItem key={d.id} value={d.id}>{d.name} ({d.total_goals} целей)</MenuItem>
        ))}
      </TextField>

      {loading && <Box sx={{ textAlign: 'center', mt: 4 }}><CircularProgress /></Box>}

      {maturity && !loading && (
        <>
          {/* Maturity index card */}
          <Card variant="outlined" sx={{ mb: 3, bgcolor: '#f5f8ff' }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Box>
                  <Typography variant="h6">{maturity.department}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Оценено целей: {maturity.evaluated_goals}
                  </Typography>
                </Box>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h3" fontWeight={700} color={maturity.maturity_index >= 0.7 ? 'success.main' : maturity.maturity_index >= 0.5 ? 'warning.main' : 'error.main'}>
                    {maturity.maturity_index}
                  </Typography>
                  <Typography variant="caption">Индекс зрелости</Typography>
                </Box>
              </Box>

              {/* Breakdown */}
              <Stack spacing={1.5}>
                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Качество SMART</Typography>
                    <Typography variant="body2" fontWeight={700}>{maturity.breakdown.smart_quality}</Typography>
                  </Box>
                  <LinearProgress variant="determinate" value={maturity.breakdown.smart_quality * 100} color={scoreColor(maturity.breakdown.smart_quality)} sx={{ height: 8, borderRadius: 4 }} />
                </Box>
                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Доля стратегических целей</Typography>
                    <Typography variant="body2" fontWeight={700}>{(maturity.breakdown.strategic_ratio * 100).toFixed(0)}%</Typography>
                  </Box>
                  <LinearProgress variant="determinate" value={maturity.breakdown.strategic_ratio * 100} color={scoreColor(maturity.breakdown.strategic_ratio)} sx={{ height: 8, borderRadius: 4 }} />
                </Box>
              </Stack>

              {/* Goal type distribution */}
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" fontWeight={500} gutterBottom>Распределение по типам:</Typography>
                <Stack direction="row" spacing={1}>
                  <Chip label={`Влияние: ${(maturity.breakdown.goal_type_distribution.impact * 100).toFixed(0)}%`} color="success" size="small" />
                  <Chip label={`Результат: ${(maturity.breakdown.goal_type_distribution.output * 100).toFixed(0)}%`} color="primary" size="small" />
                  <Chip label={`Активность: ${(maturity.breakdown.goal_type_distribution.activity * 100).toFixed(0)}%`} color={maturity.breakdown.goal_type_distribution.activity > 0.3 ? 'error' : 'default'} size="small" />
                </Stack>
              </Box>

              {/* Criterion scores */}
              {maturity.breakdown.criterion_scores && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" fontWeight={500} gutterBottom>SMART по критериям:</Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap">
                    {Object.entries(maturity.breakdown.criterion_scores).map(([name, val]) => (
                      <Chip
                        key={name}
                        label={`${CRITERION_LABELS[name] || name}: ${val}`}
                        size="small"
                        color={scoreColor(val)}
                        variant="outlined"
                      />
                    ))}
                  </Stack>
                </Box>
              )}

              {/* Weakest */}
              {maturity.breakdown.weakest_criteria?.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" fontWeight={500}>
                    Слабые критерии: {maturity.breakdown.weakest_criteria.join(', ')}
                  </Typography>
                </Box>
              )}

              {/* Recommendations */}
              {maturity.recommendations?.length > 0 && (
                <Box sx={{ mt: 2, p: 1.5, bgcolor: '#fff8e1', borderRadius: 1 }}>
                  <Typography variant="subtitle2" gutterBottom>Рекомендации руководителю:</Typography>
                  {maturity.recommendations.map((r, i) => (
                    <Typography key={i} variant="body2">- {r}</Typography>
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>

          {/* Employee list */}
          <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1 }}>
            Сотрудники ({employees.length}):
          </Typography>
          {employees.map((emp) => (
            <Card key={emp.id} variant="outlined" sx={{ mb: 1 }}>
              <CardContent sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 1.5 }}>
                <Box>
                  <Typography fontWeight={500}>{emp.full_name}</Typography>
                  <Typography variant="caption" color="text.secondary">{emp.position}</Typography>
                </Box>
                <Chip label={`${emp.goals_count} целей`} variant="outlined" size="small" />
              </CardContent>
            </Card>
          ))}
        </>
      )}
    </Box>
  );
}