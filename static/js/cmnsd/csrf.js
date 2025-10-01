// csrf.js
// Indentation: 2 spaces. Docs in English.

/**
 * Get a cookie by name
 * @param {string} name
 * @returns {string|null}
 */
export function getCookie(name) {
  if (!document.cookie) return null;
  const cookies = document.cookie.split(';');
  for (let c of cookies) {
    const [k, v] = c.trim().split('=');
    if (k === name) return decodeURIComponent(v);
  }
  return null;
}

/**
 * Get the current CSRF token (Django default: "csrftoken")
 * @returns {string|null}
 */
export function getCsrfToken() {
  return getCookie('csrftoken');
}
