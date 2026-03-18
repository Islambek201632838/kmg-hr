import React from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline, AppBar, Toolbar, Typography, Box, Tabs, Tab, Divider } from '@mui/material';
import AssessmentIcon from '@mui/icons-material/Assessment';
import EvaluateGoal from './pages/EvaluateGoal';
import MyGoals from './pages/MyGoals';
import GenerateGoals from './pages/GenerateGoals';
import Dashboard from './pages/Dashboard';
import Team from './pages/Team';
import Benchmark from './pages/Benchmark';

const theme = createTheme({
  palette: {
    primary: { main: '#1a3264' },
    secondary: { main: '#e8a838' },
  },
  typography: { fontFamily: 'Roboto, sans-serif' },
});

function NavTabs() {
  const tabs = [
    { label: 'Оценка цели', to: '/' },
    { label: 'Мои цели', to: '/my-goals' },
    { label: 'Генерация', to: '/generate' },
    { label: 'Дашборд', to: '/dashboard' },
    { label: 'Команда', to: '/team' },
    { label: 'Бенчмарк', to: '/benchmark' },
  ];

  return (
    <Tabs value={false} textColor="inherit" indicatorColor="secondary" sx={{ ml: 4 }}>
      {tabs.map((t, i) => (
        <Tab
          key={t.to}
          label={t.label}
          component={NavLink}
          to={t.to}
          sx={{
            color: 'white',
            '&.active': { color: '#e8a838' },
            fontSize: '0.8rem',
            minWidth: 'auto',
            px: 1.5,
          }}
        />
      ))}
    </Tabs>
  );
}

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AppBar position="static">
          <Toolbar>
            <AssessmentIcon sx={{ mr: 1 }} />
            <Typography variant="h6" sx={{ fontWeight: 700, whiteSpace: 'nowrap' }}>KMG HR AI</Typography>
            <NavTabs />
          </Toolbar>
        </AppBar>
        <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
          <Routes>
            <Route path="/" element={<EvaluateGoal />} />
            <Route path="/my-goals" element={<MyGoals />} />
            <Route path="/generate" element={<GenerateGoals />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/team" element={<Team />} />
            <Route path="/benchmark" element={<Benchmark />} />
          </Routes>
        </Box>
      </BrowserRouter>
    </ThemeProvider>
  );
}
