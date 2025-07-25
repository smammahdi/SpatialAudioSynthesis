import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Box,
  IconButton,
  Chip,
  List,
  ListItem,
  ListItemText,
  Button,
  Menu,
  MenuItem,
  FormControlLabel,
  Switch,
  Divider,
  TextField,
  InputAdornment
} from '@mui/material';
import {
  Clear,
  FilterList,
  Download,
  Pause,
  PlayArrow,
  Search,
  Info,
  Warning,
  Error,
  CheckCircle,
  ExpandMore,
  ExpandLess
} from '@mui/icons-material';

interface LogEntry {
  timestamp: string;
  message: string;
  type: 'info' | 'success' | 'error' | 'warning';
  source?: string;
}

interface LogPanelProps {
  logs: LogEntry[];
}

const LogPanel: React.FC<LogPanelProps> = ({ logs }) => {
  const getLogColor = (type: string) => {
    switch (type) {
      case 'error': return 'error';
      case 'warning': return 'warning';
      case 'success': return 'success';
      case 'debug': return 'default';
      default: return 'primary';
    }
  };

  return (
    <Card sx={{ mt: 3 }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">
            📋 Activity Log
          </Typography>
          <Chip 
            label={`${logs.length} entries`} 
            size="small" 
            variant="outlined" 
          />
        </Box>
        
        <Box 
          sx={{ 
            maxHeight: 300, 
            overflow: 'auto',
            backgroundColor: '#f5f5f5',
            p: 2,
            borderRadius: 1,
            fontFamily: 'monospace'
          }}
        >
          {logs.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No log entries yet...
            </Typography>
          ) : (
            logs.slice(-50).map((log, index) => (
              <Box key={index} sx={{ mb: 0.5, fontSize: '0.875rem' }}>
                <Box component="span" sx={{ color: 'text.secondary' }}>
                  [{log.timestamp}]
                </Box>
                {' '}
                <Chip 
                  label={log.type.toUpperCase()} 
                  size="small" 
                  color={getLogColor(log.type)}
                  sx={{ mx: 1, height: 20, fontSize: '0.75rem' }}
                />
                {' '}
                <Box component="span">
                  {log.message}
                </Box>
              </Box>
            ))
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default LogPanel;
