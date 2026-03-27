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
  const [touched, setTouched] = useState({});
  const [loadingEmp, setLoadingEmp] = useState(true);

  useEffect(() => {
    api.get('/api/employees').then((r) => setEmployees(r.data)).catch(() => {}).finally(() => setLoadingEmp(false));
  }, []);

  const validate = () => {
    const errs = {};
    if (!employeeId) errs.employeeId = 'Выберите сотрудника';
    if (!goalText || goalText.trim().length < 5) errs.goalText = 'Минимум 5 символов';
    if (year < 2020 || year > 2030) errs.year = 'Год от 2020 до 2030';
    return errs;
  };

  const errs = validate();
  const isValid = Object.keys(errs).length === 0;

  const handleSubmit = async () => {
    setTouched({ employeeId: true, goalText: true, year: true });
    const currentErrs = validate();
    if (Object.keys(currentErrs).length > 0) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await api.post('/api/evaluate-goal', {
        goal_text: goalText.trim(),
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
      <Typography variant="h5" fontWeight={700} gutterBottom sx={{ fontSize: { xs: '1.3rem', md: '1.5rem' } }}>
        Оценка цели по SMART
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <TextField
          select
          label={loadingEmp ? 'Загрузка сотрудников...' : 'Сотрудник'}
          value={employeeId}
          disabled={loadingEmp}
          onChange={(e) => { setEmployeeId(e.target.value); setTouched(p => ({ ...p, employeeId: true })); }}
          sx={{ minWidth: { xs: '100%', sm: 300 } }}
          size="small"
          error={touched.employeeId && !!errs.employeeId}
          helperText={touched.employeeId && errs.employeeId}
          SelectProps={{ MenuProps: { PaperProps: { sx: { maxHeight: 300 } } } }}
        >
          {employees.map((emp) => (
            <MenuItem key={emp.id} value={emp.id} sx={{ whiteSpace: 'normal', fontSize: '0.85rem' }}>
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
          sx={{ width: { xs: '48%', sm: 120 } }}
        >
          {['Q1', 'Q2', 'Q3', 'Q4'].map((q) => (
            <MenuItem key={q} value={q}>{q}</MenuItem>
          ))}
        </TextField>

        <TextField
          label="Год"
          type="number"
          value={year}
          onChange={(e) => { setYear(Number(e.target.value)); setTouched(p => ({ ...p, year: true })); }}
          size="small"
          sx={{ width: { xs: '48%', sm: 100 } }}
          error={touched.year && !!errs.year}
          helperText={touched.year && errs.year}
        />
      </Box>

      <TextField
        fullWidth
        multiline
        rows={3}
        label="Формулировка цели"
        placeholder={goalText ? '' : 'Например: Увеличить выручку подразделения на 15% к концу Q3 2025'}
        value={goalText}
        onChange={(e) => { setGoalText(e.target.value); setTouched(p => ({ ...p, goalText: true })); }}
        InputLabelProps={{ shrink: true }}
        sx={{ mb: 2 }}
        error={touched.goalText && !!errs.goalText}
        helperText={touched.goalText && errs.goalText}
      />

      <Button
        variant="contained"
        onClick={handleSubmit}
        disabled={loading}
        size="large"
      >
        {loading ? <CircularProgress size={24} color="inherit" /> : 'Оценить'}
      </Button>

      {error && <AlertBanner warnings={[error]} />}
      {result && <SmartScoreCard evaluation={result} />}
    </Box>
  );
}