import React, { useState, useEffect } from 'react';
import { TextField, MenuItem, Button, Typography, Box, CircularProgress, Chip, Stack, LinearProgress, Collapse, IconButton } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import api from '../api/client';
import GoalCard from '../components/GoalCard';
import AlertBanner from '../components/AlertBanner';

export default function GenerateGoals() {
  const [employees, setEmployees] = useState([]);
  const [employeeId, setEmployeeId] = useState('');
  const [quarter, setQuarter] = useState('Q1');
  const [year, setYear] = useState(2025);
  const [focusArea, setFocusArea] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [selected, setSelected] = useState([]);
  const [error, setError] = useState('');
  const [ragExpanded, setRagExpanded] = useState(false);

  useEffect(() => {
    api.get('/api/employees').then((r) => setEmployees(r.data)).catch(() => {});
  }, []);

  const handleGenerate = async () => {
    if (!employeeId) return;
    setLoading(true);
    setError('');
    setResult(null);
    setSelected([]);
    try {
      const res = await api.post('/api/generate-goals', {
        employee_id: Number(employeeId),
        quarter,
        year,
        focus_area: focusArea || null,
      });
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Ошибка генерации');
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (goal) => {
    setSelected((prev) =>
      prev.includes(goal.text) ? prev.filter((t) => t !== goal.text) : [...prev, goal.text]
    );
  };

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} gutterBottom>AI-генерация целей</Typography>

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
        <TextField
          label="Фокус (опционально)"
          placeholder="цифровизация, снижение затрат..."
          value={focusArea}
          onChange={(e) => setFocusArea(e.target.value)}
          size="small"
          sx={{ minWidth: 250 }}
        />
      </Box>

      <Button variant="contained" onClick={handleGenerate} disabled={loading || !employeeId} size="large">
        {loading ? <CircularProgress size={24} color="inherit" /> : 'Сгенерировать цели'}
      </Button>

      {error && <AlertBanner warnings={[error]} />}

      {result && (
        <Box sx={{ mt: 3 }}>
          <Stack direction="row" spacing={2} sx={{ mb: 2 }} flexWrap="wrap">
            <Chip label={`ВНД документов: ${result.context.vnd_docs_used}`} variant="outlined" color="primary" />
            {result.context.avg_rag_score > 0 && (
              <Chip
                label={`Релевантность: ${(result.context.avg_rag_score * 100).toFixed(0)}%`}
                color={result.context.avg_rag_score >= 0.6 ? 'success' : result.context.avg_rag_score >= 0.4 ? 'warning' : 'error'}
                size="small"
              />
            )}
            <Chip label={`KPI: ${result.context.kpis_used.join(', ') || 'нет'}`} variant="outlined" />
            {result.context.manager_goals_used && <Chip label="Цели руководителя учтены" color="success" size="small" />}
          </Stack>

          {/* RAG chunks detail */}
          {result.context.rag_chunks?.length > 0 && (
            <Box sx={{ mb: 2, border: '1px solid #e0e0e0', borderRadius: 1 }}>
              <Box
                sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', px: 2, py: 1, cursor: 'pointer', bgcolor: '#f5f8ff', borderRadius: 1 }}
                onClick={() => setRagExpanded(!ragExpanded)}
              >
                <Typography variant="subtitle2">
                  Извлечённые фрагменты ВНД ({result.context.rag_chunks.length})
                </Typography>
                <IconButton size="small">
                  <ExpandMoreIcon sx={{ transform: ragExpanded ? 'rotate(180deg)' : 'rotate(0deg)', transition: '0.2s' }} />
                </IconButton>
              </Box>
              <Collapse in={ragExpanded}>
                <Box sx={{ px: 2, pb: 1.5 }}>
                  {result.context.rag_chunks.map((ch, i) => (
                    <Box key={i} sx={{ mb: 1.5 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                        <Typography variant="body2" fontWeight={500}>
                          {ch.doc_title || 'Без названия'}
                          {ch.doc_type && <Chip label={ch.doc_type} size="small" sx={{ ml: 1 }} variant="outlined" />}
                        </Typography>
                        <Typography variant="caption" fontWeight={700} color={ch.score >= 0.6 ? 'success.main' : ch.score >= 0.4 ? 'warning.main' : 'error.main'}>
                          {(ch.score * 100).toFixed(0)}%
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={ch.score * 100}
                        color={ch.score >= 0.6 ? 'success' : ch.score >= 0.4 ? 'warning' : 'error'}
                        sx={{ height: 5, borderRadius: 3, mb: 0.5 }}
                      />
                      <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                        {ch.text_preview}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </Collapse>
            </Box>
          )}

          <AlertBanner warnings={result.warnings} />

          <Typography variant="subtitle1" sx={{ mt: 2, mb: 1 }}>
            Выберите цели для принятия ({selected.length} выбрано):
          </Typography>

          {result.goals.map((goal, i) => (
            <GoalCard
              key={i}
              goal={goal}
              selected={selected.includes(goal.text)}
              onSelect={toggleSelect}
            />
          ))}

          {selected.length > 0 && (
            <Button
              variant="contained"
              color="secondary"
              sx={{ mt: 2 }}
              size="large"
              onClick={async () => {
                const chosen = result.goals.filter((g) => selected.includes(g.text));
                await api.post('/api/accept-goals', {
                  employee_id: Number(employeeId),
                  quarter,
                  year,
                  goals: chosen,
                });
                alert(`Принято ${chosen.length} целей`);
                setSelected([]);
              }}
            >
              Принять выбранные ({selected.length})
            </Button>
          )}
        </Box>
      )}
    </Box>
  );
}
