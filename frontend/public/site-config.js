/* Local static previews use Django on port 8000; production stays same-origin. */
window.ESICOM_API_BASE_URL = window.ESICOM_API_BASE_URL || (
  ['localhost', '127.0.0.1'].includes(window.location.hostname) &&
  ['4173', '4174', '5173'].includes(window.location.port)
    ? 'http://127.0.0.1:8000'
    : ''
);
