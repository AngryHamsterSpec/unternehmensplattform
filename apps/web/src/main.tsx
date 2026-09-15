import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import './design-tokens.css';
import './styles.css';
import './workspace.css';
try {
  document.documentElement.dataset.density =
    localStorage.getItem('kompass-density') === 'compact' ? 'compact' : 'comfortable';
} catch {
  /* Systemstandard bei gesperrtem Speicher. */
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
