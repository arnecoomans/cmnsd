// Entry point for cmnsd
// Indentation: 2 spaces. Docs in English.

import * as core from './core.js';

// Default export is the entire core (so cmnsd.init() works)
export default core;

// Also re-export all named functions for flexibility
export * from './core.js';
