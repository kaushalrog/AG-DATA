// Runtime configuration. API_BASE can be overridden without a rebuild via
// <meta name="agri-api-base" content="/other/api/v1"> in index.html.
const meta = typeof document !== 'undefined' ? document.querySelector('meta[name="agri-api-base"]') : null;
export const API_BASE = ((meta && meta.content) || '/api/v1').replace(/\/$/, '');
export const APP_VERSION = '2.0.0';
export const LANGS = ['en', 'ta', 'te', 'ml', 'hi', 'kn'];
export const API_TIMEOUT_MS = 9000;
