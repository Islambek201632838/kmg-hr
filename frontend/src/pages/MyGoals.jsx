import React, { useState, useEffect } from 'react';
import { TextField, MenuItem, Button, Typography, Box, CircularProgress, Card, CardContent, Chip, Stack, LinearProgress, IconButton, Snackbar, Alert } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer } from 'recharts';
import api from '../api/client';
import AlertBanner from '../components/AlertBanner';

const GOAL_TYPE_LABELS = {
  activity: 'Activity / Активность',
  output: 'Output / Результат',
  impact: 'Impact / Влияние на бизнес',
};

const ALIGN_LABELS = {
  strategic: 'Strategic / Стратегическая',
  functional: 'Functional / Функциональная',
  operational: 'Operational / Операционная',
};

const CRITERION_LABELS = {
  specific: 'Specific / Конкретность',
  measurable: 'Measurable / Измеримость',
  achievable: 'Achievable / Достижимость',
  relevant: 'Relevant / Релевантность',
  time_bound: 'Time-bound / Сроки',
};

export default function MyGoals() {
  const [employees, setEmployees] = useState([]);
  const [employeeId, setEmployeeId] = useState('');
  const [quarter, setQuarter] = useState('Q1');
  const [year, setYear] = useState(2025);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [touched, setTouched] = useState({});
  const [loadingEmp, setLoadingEmp] = useState(true);
  const [snack, setSnack] = useState({ open: false, msg: '', severity: 'success' });

  useEffect(() => {
    api.get('/api/employees').then((r) => setEmployees(r.data)).catch(() => {}).finally(() => setLoadingEmp(false));
  }, []);

  const errs = {};
  if (!employeeId) errs.employeeId = 'Выберите сотрудника';
  if (year < 2020 || year > 2030) errs.year = 'Год от 2020 до 2030';

  const handleEvaluate = async () => {
    setTouched({ employeeId: true, year: true });
    if (!employeeId || year < 2020 || year > 2030) return;
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
      <Typography variant="h5" fontWeight={700} gutterBottom sx={{ fontSize: { xs: '1.2rem', md: '1.5rem' } }}>
        Мои цели — пакетная оценка
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <TextField
          select label={loadingEmp ? 'Загрузка...' : 'Сотрудник'} value={employeeId} disabled={loadingEmp}
          onChange={(e) => { setEmployeeId(e.target.value); setTouched(p => ({ ...p, employeeId: true })); }}
          sx={{ minWidth: { xs: '100%', sm: 300 } }} size="small"
          error={touched.employeeId && !!errs.employeeId}
          helperText={touched.employeeId && errs.employeeId}
          SelectProps={{ MenuProps: { PaperProps: { sx: { maxHeight: 300 } } } }}
        >
          {employees.map((emp) => (
            <MenuItem key={emp.id} value={emp.id} sx={{ whiteSpace: 'normal', fontSize: '0.85rem' }}>{emp.full_name} — {emp.position}</MenuItem>
          ))}
        </TextField>
        <TextField select label="Квартал" value={quarter} onChange={(e) => setQuarter(e.target.value)} size="small" sx={{ width: 120 }}>
          {['Q1', 'Q2', 'Q3', 'Q4'].map((q) => <MenuItem key={q} value={q}>{q}</MenuItem>)}
        </TextField>
        <TextField label="Год" type="number" value={year}
          onChange={(e) => { setYear(Number(e.target.value)); setTouched(p => ({ ...p, year: true })); }}
          size="small" sx={{ width: 100 }}
          error={touched.year && !!errs.year}
          helperText={touched.year && errs.year}
        />
        <Button variant="contained" onClick={handleEvaluate} disabled={loading}>
          {loading ? <CircularProgress size={24} color="inherit" /> : 'Оценить все цели'}
        </Button>
      </Box>

      {error && <AlertBanner warnings={[error]} />}

      {result && (
        <>
          <Card variant="outlined" sx={{ mb: 2, bgcolor: '#f5f8ff' }}>
            <CardContent>
              <Typography variant="h6" sx={{ fontSize: { xs: '0.95rem', md: '1.25rem' }, wordBreak: 'break-word' }}>
                {result.employee_name} — {result.department}
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap', gap: 0.5 }}>
                <Chip label={`Индекс: ${result.summary.avg_index}`} color={result.summary.avg_index >= 0.7 ? 'success' : 'warning'} size="small" />
                <Chip label={`Целей: ${result.summary.total_goals}`} variant="outlined" size="small" />
                <Chip label={`Вес: ${result.summary.total_weight}%`} variant="outlined" size="small" />
                <Chip label={`Слабый: ${CRITERION_LABELS[result.summary.weakest_criterion] || result.summary.weakest_criterion}`} color="error" variant="outlined" size="small" />
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
              <Card variant="outlined" sx={{ mb: 2, p: { xs: 1, md: 2 } }}>
                <Typography variant="subtitle1" fontWeight={600} sx={{ px: 1 }}>Профиль SMART (все цели)</Typography>
                <ResponsiveContainer width="100%" height={250}>
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
            <Card key={g.goal_id} variant="outlined" sx={{
              mb: 1.5,
              borderLeft: `4px solid ${g.overall_index >= 0.7 ? '#4caf50' : g.overall_index >= 0.5 ? '#ff9800' : '#f44336'}`,
              transition: 'box-shadow 0.2s',
              '&:hover': { boxShadow: 2 },
            }}>
              <CardContent>
                <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, justifyContent: 'space-between', alignItems: { xs: 'flex-start', sm: 'flex-start' }, gap: 1 }}>
                  <Typography variant="body1" sx={{ flex: 1, fontSize: { xs: '0.85rem', md: '1rem' } }}>{g.goal_text}</Typography>
                  <Stack direction="row" spacing={0.5} sx={{ flexShrink: 0, flexWrap: 'wrap', gap: 0.5, alignItems: 'center' }}>
                    <Chip label={g.overall_index.toFixed(2)} color={g.overall_index >= 0.7 ? 'success' : 'warning'} size="small" />
                    <Chip label={GOAL_TYPE_LABELS[g.goal_type] || g.goal_type} size="small" />
                    <Chip label={ALIGN_LABELS[g.alignment_level] || g.alignment_level} size="small" variant="outlined" />
                    {g.goal_id?.startsWith('manual-') && g.overall_index < 0.7 && (
                      <IconButton
                        size="small"
                        color="error"
                        title="Удалить цель с низким SMART-индексом"
                        onClick={async () => {
                          const evalId = g.goal_id.replace('manual-', '');
                          try {
                            await api.delete(`/api/evaluation/${evalId}`);
                            setResult(prev => ({
                              ...prev,
                              goals: prev.goals.filter(x => x.goal_id !== g.goal_id),
                            }));
                            setSnack({ open: true, msg: 'Цель удалена', severity: 'success' });
                          } catch (e) {
                            setSnack({ open: true, msg: 'Ошибка удаления', severity: 'error' });
                          }
                        }}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    )}
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
      <Snackbar open={snack.open} autoHideDuration={3000} onClose={() => setSnack(s => ({ ...s, open: false }))}>
        <Alert severity={snack.severity} variant="filled">{snack.msg}</Alert>
      </Snackbar>
    </Box>
  );
}
