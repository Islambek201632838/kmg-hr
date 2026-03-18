import React from 'react';
import { Alert, Stack } from '@mui/material';

export default function AlertBanner({ warnings }) {
  if (!warnings || warnings.length === 0) return null;

  return (
    <Stack spacing={1} sx={{ mt: 2 }}>
      {warnings.map((w, i) => {
        let severity = 'info';
        if (w.includes('критически') || w.includes('требует переработки')) severity = 'error';
        else if (w.includes('Суммарный') || w.includes('меньше') || w.includes('больше') || w.includes('ниже')) severity = 'warning';

        return <Alert key={i} severity={severity} variant="outlined">{w}</Alert>;
      })}
    </Stack>
  );
}
