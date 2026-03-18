import React, { useState, useEffect } from 'react';
import { Typography, Box, Card, CardContent, Chip, Stack, TextField, MenuItem, CircularProgress } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LineChart, Line, Legend, RadarChart, Radar, PolarGrid, PolarAngleAxis } from 'recharts';
import api from '../api/client';

function barColor(value) {
  if (value >= 0.8) return '#4caf50';
  if (value >= 0.6) return '#ff9800';
  return '#f44336';
}

function shortName(name) {
  return name
    .replace('Департамент ', '')
    .replace('по поддержке и производству прикладных систем', 'Прикладные системы')
    .replace('управления данными и аналитики', 'Данные и аналитика')
    .replace('учетных систем', 'Учётные системы')
    .replace('корпоративного менеджмента', 'Корп. менеджмент')
    .replace('цифровой трансформации и архитектуры', 'Цифр. трансформация')
    .replace('инфраструктуры и DevOps', 'Инфраструктура и DevOps')
    .replace('информационной безопасности', 'Инфобезопасность')
    .replace('сервис-деск и эксплуатации ИТ', 'Сервис-деск');
}

const CRITERION_LABELS = {
  specific: 'Конкретность',
  measurable: 'Измеримость',
  achievable: 'Достижимость',
  relevant: 'Релевантность',
  time_bound: 'Сроки',
};

export default function Dashboard() {
  const [year, setYear] = useState(2025);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedDeptId, setSelectedDeptId] = useState(null);
  const [trend, setTrend] = useState(null);

  useEffect(() => {
    setLoading(true);
    api.get(`/api/dashboard/department-quality?year=${year}`)
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [year]);

  useEffect(() => {
    if (!selectedDeptId) return;
    api.get(`/api/dashboard/quarterly-trend?department_id=${selectedDeptId}&year=${year}`)
      .then((r) => setTrend(r.data))
      .catch(() => {});
  }, [selectedDeptId, year]);

  if (loading) return <Box sx={{ textAlign: 'center', mt: 4 }}><CircularProgress /></Box>;

  const chartData = data ? data.departments.map(d => ({
    ...d,
    short_name: shortName(d.name),
  })) : [];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" fontWeight={700}>Дашборд качества целей</Typography>
        <TextField
          select label="Год" value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          size="small" sx={{ width: 100 }}
        >
          {[2024, 2025, 2026].map((y) => <MenuItem key={y} value={y}>{y}</MenuItem>)}
        </TextField>
      </Box>

      {data && (
        <>
          <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
            <Card sx={{ flex: 1, bgcolor: '#f5f8ff' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h3" fontWeight={700} color="primary">{data.org_avg}</Typography>
                <Typography variant="body2" color="text.secondary">Средний SMART-индекс</Typography>
              </CardContent>
            </Card>
            <Card sx={{ flex: 1, bgcolor: '#f5f8ff' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h3" fontWeight={700} color="primary">{data.departments.length}</Typography>
                <Typography variant="body2" color="text.secondary">Подразделений</Typography>
              </CardContent>
            </Card>
            <Card sx={{ flex: 1, bgcolor: '#f5f8ff' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h3" fontWeight={700} color="primary">
                  {data.departments.reduce((s, d) => s + d.total_goals, 0)}
                </Typography>
                <Typography variant="body2" color="text.secondary">Всего целей</Typography>
              </CardContent>
            </Card>
          </Stack>

          {data.top_issues.length > 0 && (
            <Stack direction="row" spacing={1} sx={{ mb: 3 }} flexWrap="wrap">
              {data.top_issues.map((issue, i) => (
                <Chip key={i} label={issue} color="warning" variant="outlined" />
              ))}
            </Stack>
          )}

          <Card variant="outlined" sx={{ mb: 3, p: 2 }}>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>SMART-индекс по подразделениям</Typography>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 180, right: 20, top: 5, bottom: 5 }}>
                <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => v.toFixed(1)} />
                <YAxis
                  dataKey="short_name"
                  type="category"
                  width={170}
                  tick={{ fontSize: 12 }}
                  interval={0}
                />
                <Tooltip
                  formatter={(v) => v.toFixed(2)}
                  labelFormatter={(label) => label}
                />
                <Bar dataKey="avg_smart_index" radius={[0, 6, 6, 0]} barSize={28}>
                  {chartData.map((d, i) => (
                    <Cell key={i} fill={barColor(d.avg_smart_index)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          {data.departments.map((dept) => (
            <Box key={dept.id}>
              <Card
                variant="outlined"
                sx={{ mb: 1, cursor: 'pointer', border: selectedDeptId === dept.id ? '2px solid #1a3264' : undefined }}
                onClick={() => setSelectedDeptId(selectedDeptId === dept.id ? null : dept.id)}
              >
                <CardContent sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 1.5 }}>
                  <Box>
                    <Typography fontWeight={600}>{dept.name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {dept.total_goals} целей | Слабый критерий: {CRITERION_LABELS[dept.weakest_criterion] || dept.weakest_criterion}
                    </Typography>
                  </Box>
                  <Stack direction="row" spacing={1}>
                    <Chip label={dept.avg_smart_index.toFixed(2)} color={dept.avg_smart_index >= 0.7 ? 'success' : 'warning'} />
                    <Chip label={`Стратегия: ${(dept.strategic_ratio * 100).toFixed(0)}%`} variant="outlined" size="small" />
                  </Stack>
                </CardContent>
              </Card>

              {/* Тренд раскрывается сразу под выбранным подразделением */}
              {selectedDeptId === dept.id && trend && (
                <Card variant="outlined" sx={{ mb: 2, p: 2, bgcolor: '#f5f8ff' }}>
                  <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Квартальная динамика: {trend.department} ({year})
                  </Typography>
                  {trend.trend.filter(t => t.avg_smart_index !== null).length < 2 ? (
                    <Box sx={{ textAlign: 'center', py: 3 }}>
                      <Typography variant="body2" color="text.secondary">
                        Недостаточно данных для тренда — оценено {trend.trend.filter(t => t.avg_smart_index !== null).length} квартал(а)
                      </Typography>
                    </Box>
                  ) : (
                    <ResponsiveContainer width="100%" height={240}>
                      <LineChart data={trend.trend} margin={{ left: 10, right: 20 }}>
                        <XAxis dataKey="quarter" />
                        <YAxis domain={[0, 1]} tickFormatter={v => v.toFixed(1)} />
                        <Tooltip formatter={(v, name) => [v != null ? v.toFixed(2) : '—', name]} />
                        <Legend />
                        <Line type="monotone" dataKey="avg_smart_index" name="SMART-индекс" stroke="#1a3264" strokeWidth={2} dot={{ r: 5 }} connectNulls={false} />
                        {trend.trend.some(t => t.strategic_ratio > 0) && (
                          <Line type="monotone" dataKey="strategic_ratio" name="Стратег. связка" stroke="#e8a838" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 4 }} connectNulls={false} />
                        )}
                      </LineChart>
                    </ResponsiveContainer>
                  )}
                  {!trend.trend.some(t => (t.strategic_ratio ?? 0) > 0) && (
                    <Typography variant="caption" color="text.secondary">
                      Стратегических целей не выявлено — все цели на уровне functional/operational
                    </Typography>
                  )}
                  {(() => {
                    const latest = [...trend.trend].reverse().find(t => Object.keys(t.criterion_scores).length > 0);
                    if (!latest) return null;
                    const radarData = Object.entries(latest.criterion_scores).map(([k, v]) => ({ criterion: k, score: v }));
                    return (
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          SMART по критериям ({latest.quarter}) — {latest.evaluated_goals} целей
                        </Typography>
                        <ResponsiveContainer width="100%" height={200}>
                          <RadarChart data={radarData}>
                            <PolarGrid />
                            <PolarAngleAxis dataKey="criterion" tick={{ fontSize: 11 }} />
                            <Radar dataKey="score" stroke="#1a3264" fill="#1a3264" fillOpacity={0.25} />
                          </RadarChart>
                        </ResponsiveContainer>
                      </Box>
                    );
                  })()}
                </Card>
              )}
            </Box>
          ))}
        </>
      )}
    </Box>
  );
}