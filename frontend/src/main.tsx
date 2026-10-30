import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material'
import App from './App'

// Soft, rounded look: light grey page, white rounded surfaces, pill buttons, no ALL-CAPS labels.
const theme = createTheme({
  colorSchemes: {
    light: { palette: { primary: { main: '#4f46e5' }, background: { default: '#f4f5fb', paper: '#ffffff' } } },
    dark: { palette: { primary: { main: '#818cf8' } } },
  },
  shape: { borderRadius: 12 },
  typography: { fontFamily: 'Inter, system-ui, sans-serif', button: { textTransform: 'none', fontWeight: 600 } },
  components: {
    MuiButton: { styleOverrides: { root: { borderRadius: 999, paddingInline: 16 } }, defaultProps: { disableElevation: true } },
    MuiToggleButton: { styleOverrides: { root: { textTransform: 'none', fontWeight: 600 } } },
    MuiCard: { styleOverrides: { root: { borderRadius: 14 } } },
    MuiPaper: { styleOverrides: { outlined: { borderRadius: 16 } } },
    MuiDialog: { styleOverrides: { paper: { borderRadius: 20 } } },
    MuiMenu: { styleOverrides: { paper: { borderRadius: 12, marginTop: 4 } } },
    MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
    MuiOutlinedInput: { styleOverrides: { root: ({ theme }) => ({ borderRadius: 12, backgroundColor: theme.palette.background.paper }) } },
    MuiListItemButton: { styleOverrides: { root: { borderRadius: 10, marginInline: 8 } } },
    MuiTooltip: { styleOverrides: { tooltip: { borderRadius: 8 } } },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider theme={theme} defaultMode="system">
      <CssBaseline />
      <App />
    </ThemeProvider>
  </StrictMode>,
)
