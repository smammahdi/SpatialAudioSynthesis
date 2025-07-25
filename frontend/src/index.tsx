import React from 'react';
import { createRoot } from 'react-dom/client';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import ProfessionalSpatialAudioApp from './ProfessionalApp.tsx';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#667eea',
    },
    secondary: {
      main: '#764ba2',
    },
    background: {
      default: 'transparent',
      paper: '#ffffff'
    },
    text: {
      primary: '#2d3748',
      secondary: '#4a5568'
    }
  },
  typography: {
    fontFamily: '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif',
    h5: {
      fontWeight: 400,
      fontSize: '2.5rem',
      color: 'white'
    },
    h6: {
      fontWeight: 600,
      color: '#4a5568',
      borderBottom: '2px solid #e2e8f0',
      paddingBottom: '10px',
      marginBottom: '20px'
    }
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 15,
          padding: '25px',
          boxShadow: '0 15px 35px rgba(0,0,0,0.1)',
          backdropFilter: 'blur(10px)'
        }
      }
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 8,
          padding: '12px 20px',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          transition: 'transform 0.2s',
          '&:hover': {
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            transform: 'translateY(-2px)'
          }
        }
      }
    }
  }
});

const container = document.getElementById('root');
const root = createRoot(container!);

root.render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <ProfessionalSpatialAudioApp />
    </ThemeProvider>
  </React.StrictMode>
);
