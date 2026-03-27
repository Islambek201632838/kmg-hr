import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import {
  ThemeProvider, createTheme, CssBaseline, AppBar, Toolbar, Typography, Box,
  Tabs, Tab, IconButton, Drawer, List, ListItemButton, ListItemText, useMediaQuery,
} from '@mui/material';
import AssessmentIcon from '@mui/icons-material/Assessment';
import MenuIcon from '@mui/icons-material/Menu';
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
  components: {
    MuiButton: { styleOverrides: { root: { textTransform: 'none', fontWeight: 600 } } },
    MuiTab: { styleOverrides: { root: { textTransform: 'none' } } },
  },
});

const NAV_ITEMS = [
  { label: 'Оценка цели', to: '/' },
  { label: 'Мои цели', to: '/my-goals' },
  { label: 'Генерация', to: '/generate' },
  { label: 'Дашборд', to: '/dashboard' },
  { label: 'Команда', to: '/team' },
  { label: 'Бенчмарк', to: '/benchmark' },
];

function NavTabs() {
  return (
    <Tabs
      value={false}
      textColor="inherit"
      indicatorColor="secondary"
      variant="scrollable"
      scrollButtons="auto"
      sx={{ ml: 2 }}
    >
      {NAV_ITEMS.map((t) => (
        <Tab
          key={t.to}
          label={t.label}
          component={NavLink}
          to={t.to}
          sx={{
            color: 'rgba(255,255,255,0.7)',
            '&.active': { color: '#e8a838', fontWeight: 700, borderBottom: '2px solid #e8a838' },
            fontSize: '0.85rem',
            minWidth: 'auto',
            px: 2,
            transition: 'all 0.2s',
            '&:hover': { color: '#fff' },
          }}
        />
      ))}
    </Tabs>
  );
}

function MobileDrawer({ open, onClose }) {
  return (
    <Drawer anchor="left" open={open} onClose={onClose}>
      <Box sx={{ width: 250, pt: 2 }}>
        <Typography variant="h6" fontWeight={700} sx={{ px: 2, pb: 1, color: '#1a3264' }}>
          KMG HR AI
        </Typography>
        <List>
          {NAV_ITEMS.map((t) => (
            <ListItemButton
              key={t.to}
              component={NavLink}
              to={t.to}
              onClick={onClose}
              sx={{ '&.active': { bgcolor: '#f0f4ff', color: '#1a3264', fontWeight: 700 } }}
            >
              <ListItemText primary={t.label} />
            </ListItemButton>
          ))}
        </List>
      </Box>
    </Drawer>
  );
}

export default function App() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AppBar position="static">
          <Toolbar sx={{ minHeight: { xs: 56, md: 64 } }}>
            {isMobile && (
              <IconButton color="inherit" edge="start" onClick={() => setDrawerOpen(true)} sx={{ mr: 1 }}>
                <MenuIcon />
              </IconButton>
            )}
            <AssessmentIcon sx={{ mr: 1, display: { xs: 'none', sm: 'block' } }} />
            <Typography variant="h6" sx={{ fontWeight: 700, whiteSpace: 'nowrap', fontSize: { xs: '1rem', md: '1.25rem' } }}>
              KMG HR AI
            </Typography>
            {!isMobile && <NavTabs />}
          </Toolbar>
        </AppBar>
        {isMobile && <MobileDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />}
        <Box sx={{ p: { xs: 1.5, sm: 2, md: 3 }, maxWidth: 1200, mx: 'auto' }}>
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