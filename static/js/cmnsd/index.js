// Public entry for cmnsd
// Indentation: 2 spaces. Docs in English.
import { api } from './core.js';
export default api;
if (typeof window !== 'undefined') window.cmnsd = api;
