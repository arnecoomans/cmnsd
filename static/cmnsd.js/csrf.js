// CSRF token for cmnsd.js POSTs.
// Indentation: 2 spaces. Docs in English.

// From <meta name="csrf-token"> (the project's base template), falling
// back to Django's csrftoken cookie.
export function csrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta && meta.content) return meta.content;
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : '';
}
