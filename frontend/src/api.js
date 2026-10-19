const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/+$/, "");

async function request(path, { token, ...options } = {}) {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch (error) {
    throw new Error(
      `Unable to reach the Amani Line API at ${API_BASE_URL}. Check that the backend is running.`,
      { cause: error },
    );
  }

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).join(" ")
      : detail;
    const error = new Error(message || `Request failed (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return body;
}

export function createReport(payload) {
  return request("/api/reports", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getReportQueue(filters = {}) {
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  const encoded = query.toString();
  const suffix = encoded ? `?${encoded}` : "";
  return request(`/api/reports/queue${suffix}`, { token: getStoredToken() });
}

export function getReportEvents(reportId) {
  return request(`/api/reports/${encodeURIComponent(reportId)}/events`, {
    token: getStoredToken(),
  });
}

export function triageReport(reportId, payload) {
  return request(`/api/reports/${encodeURIComponent(reportId)}/triage`, {
    method: "PATCH",
    token: getStoredToken(),
    body: JSON.stringify(payload),
  });
}

export function getQueueReviewers() {
  return request("/api/reports/reviewers", { token: getStoredToken() });
}

export function getPiiEscalations() {
  return request("/api/admin/reports/pii-escalations", {
    token: getStoredToken(),
  });
}

export function clearReportPii(reportId, description) {
  return request(`/api/admin/reports/${encodeURIComponent(reportId)}/pii-clear`, {
    method: "POST",
    token: getStoredToken(),
    body: JSON.stringify({ description }),
  });
}

export function publishReport(reportId, payload) {
  return request(`/api/reports/${encodeURIComponent(reportId)}/publish`, {
    method: "POST",
    token: getStoredToken(),
    body: JSON.stringify(payload),
  });
}

export function getPendingUpdates() {
  return request("/api/updates/pending", { token: getStoredToken() });
}

export function approveUpdate(updateId) {
  return request(`/api/updates/${encodeURIComponent(updateId)}/approve`, {
    method: "POST",
    token: getStoredToken(),
  });
}

export function rejectUpdate(updateId, reason) {
  return request(`/api/updates/${encodeURIComponent(updateId)}/reject`, {
    method: "POST",
    token: getStoredToken(),
    body: JSON.stringify({ reason }),
  });
}

export function correctUpdate(updateId, action, reason) {
  return request(`/api/updates/${encodeURIComponent(updateId)}/correction`, {
    method: "POST",
    token: getStoredToken(),
    body: JSON.stringify({ action, reason }),
  });
}

export function getReviewers() {
  return request("/api/admin/reviewers", { token: getStoredToken() });
}

export function addReviewer(email, displayName, ward) {
  return request("/api/admin/reviewers", {
    method: "POST",
    token: getStoredToken(),
    body: JSON.stringify({ email, display_name: displayName || null, ward: ward || null }),
  });
}

export function removeReviewer(email) {
  return request(`/api/admin/reviewers/${encodeURIComponent(email)}`, {
    method: "DELETE",
    token: getStoredToken(),
  });
}

export function assignReport(reportId, email) {
  return request(
    `/api/admin/reports/${encodeURIComponent(reportId)}/assignment`,
    {
      method: "PATCH",
      token: getStoredToken(),
      body: JSON.stringify({ assigned_to_email: email || null }),
    },
  );
}

export function getUpdates(status) {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(`/api/updates${query}`);
}

function getStoredToken() {
  return window.localStorage.getItem("amani-access-token");
}

export function signUp(credentials) {
  return request("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export function signIn(credentials) {
  return request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export function getCurrentUser(token) {
  return request("/api/auth/me", { token });
}

export function createDispute(payload, token) {
  return request("/api/disputes", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export function getDisputes(status = "") {
  const suffix = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(`/api/admin/disputes${suffix}`, { token: getStoredToken() });
}

export function updateDispute(disputeId, payload) {
  return request(`/api/admin/disputes/${encodeURIComponent(disputeId)}`, {
    method: "PATCH",
    token: getStoredToken(),
    body: JSON.stringify(payload),
  });
}
