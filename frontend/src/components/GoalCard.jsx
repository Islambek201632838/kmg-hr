import React from 'react';
import { Card, CardContent, Typography, Box, Chip, Stack, LinearProgress } from '@mui/material';

const GOAL_TYPE_LABELS = {
  activity: 'Активность',
  output: 'Результат',
  impact: 'Влияние на бизнес',
};

const ALIGN_LABELS = {
  strategic: 'Стратегическая',
  functional: 'Функциональная',
  operational: 'Операционная',
};

export default function GoalCard({ goal, onSelect, selected }) {
  return (
    <Card
      variant="outlined"
      sx={{
        mb: 2,
        cursor: onSelect ? 'pointer' : 'default',
        border: selected ? '2px solid #1a3264' : undefined,
        '&:hover': onSelect ? { boxShadow: 3 } : {},
      }}
      onClick={() => onSelect && onSelect(goal)}
    >
      <CardContent>
        <Typography variant="body1" fontWeight={500} gutterBottom>{goal.text}</Typography>

        <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
          <Chip label={GOAL_TYPE_LABELS[goal.goal_type] || goal.goal_type} size="small" color={goal.goal_type === 'impact' ? 'success' : goal.goal_type === 'output' ? 'primary' : 'default'} />
          <Chip label={ALIGN_LABELS[goal.strategic_alignment?.level] || goal.strategic_alignment?.level || 'Операционная'} size="small" variant="outlined" />
          {goal.weight && <Chip label={`Вес: ${goal.weight}%`} size="small" variant="outlined" />}
        </Stack>

        {goal.metric && (
          <Typography variant="body2" color="text.secondary">Метрика: {goal.metric}</Typography>
        )}
        {goal.deadline && (
          <Typography variant="body2" color="text.secondary">Срок: {goal.deadline}</Typography>
        )}

        {goal.smart_index != null && (
          <Box sx={{ mt: 1 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="caption">SMART-индекс</Typography>
              <Typography variant="caption" fontWeight={700}>{goal.smart_index.toFixed(2)}</Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={goal.smart_index * 100}
              color={goal.smart_index >= 0.7 ? 'success' : 'warning'}
              sx={{ height: 6, borderRadius: 3 }}
            />
          </Box>
        )}

        {goal.source_doc && (
          <Box sx={{ mt: 1, p: 1, bgcolor: '#f5f5f5', borderRadius: 1 }}>
            <Typography variant="caption" fontWeight={500}>Источник: {goal.source_doc}</Typography>
            {goal.source_quote && (
              <Typography variant="caption" display="block" fontStyle="italic" color="text.secondary">
                "{goal.source_quote}"
              </Typography>
            )}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
