import React, { useState, useEffect } from 'react';
import { TextField, Button, MenuItem, Typography, Box, CircularProgress } from '@mui/material';
import api from '../api/client';
import SmartScoreCard from '../components/SmartScoreCard';
import AlertBanner from '../components/AlertBanner';

export default function EvaluateGoal() {
  const [employees, setEmployees] = useState([]);
  const [employeeId, setEmployeeId] = useState('');
  const [goalText, setGoalText] = useState('');
  const [quarter, setQuarter] = useState('Q1');
  const [year, setYear] = useState(2025);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/api/employees').then((r) => setEmployees(r.data)).catch(() => {});
  }, []);

  const handleSubmit = async () => {
    if (!goalText || !employeeId) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await api.post('/api/evaluate-goal', {
        goal_text: goalText,
        employee_id: Number(employeeId),
        quarter,
        year,
      });
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Ошибка оценки');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} gutterBottom>Оценка цели по SMART</Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <TextField
          select
          label="Сотрудник"
          value={employeeId}
          onChange={(e) => setEmployeeId(e.target.value)}
          sx={{ minWidth: 300 }}
          size="small"
        >
          {employees.map((emp) => (
            <MenuItem key={emp.id} value={emp.id}>
              {emp.full_name} — {emp.position}
            </MenuItem>
          ))}
        </TextField>

        <TextField
          select
          label="Квартал"
          value={quarter}
          onChange={(e) => setQuarter(e.target.value)}
          size="small"
          sx={{ width: 120 }}
        >
          {['Q1', 'Q2', 'Q3', 'Q4'].map((q) => (
            <MenuItem key={q} value={q}>{q}</MenuItem>
          ))}
        </TextField>

        <TextField
          label="Год"
          type="number"
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          size="small"
          sx={{ width: 100 }}
        />
      </Box>

      <TextField
        fullWidth
        multiline
        rows={3}
        label="Формулировка цели"
        placeholder="Например: Увеличить выручку подразделения на 15% к концу Q3 2025"
        value={goalText}
        onChange={(e) => setGoalText(e.target.value)}
        sx={{ mb: 2 }}
      />

      <Button
        variant="contained"
        onClick={handleSubmit}
        disabled={loading || !goalText || !employeeId}
        size="large"
      >
        {loading ? <CircularProgress size={24} color="inherit" /> : 'Оценить'}
      </Button>

      {error && <AlertBanner warnings={[error]} />}
      {result && <SmartScoreCard evaluation={result} />}
    </Box>
  );
}
