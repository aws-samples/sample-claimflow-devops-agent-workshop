// Runtime configuration. This default ships in the build; the deployment
// overwrites it in S3 with the real API Gateway URL. When empty, the app falls
// back to REACT_APP_API_URL (build-time) or http://localhost:8000 (local dev).
window.__API_URL__ = "";
