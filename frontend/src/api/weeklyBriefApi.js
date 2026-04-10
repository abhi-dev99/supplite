const DEFAULT_BASE_URL = "http://localhost:8000";
const PREVIEW_TIMEOUT_MS = 15000;
const GENERATE_TIMEOUT_MS = 90000;

function resolveBaseUrl() {
  const configured = import.meta.env.VITE_BACKEND_BASE_URL;
  return (configured && configured.trim()) || DEFAULT_BASE_URL;
}

function createTimeoutSignal(timeoutMs) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  return { signal: controller.signal, cleanup: () => clearTimeout(timeoutId) };
}

export async function fetchWeeklyBrief({ metro = "Dallas", forceRefresh = false, generateBrief = false } = {}) {
  const baseUrl = resolveBaseUrl();
  const url = new URL("/api/briefs/weekly", baseUrl);
  if (metro && String(metro).trim()) {
    url.searchParams.set("metro", String(metro).trim());
  }
  if (generateBrief) {
    url.searchParams.set("generate_brief", "true");
  }
  if (forceRefresh) {
    url.searchParams.set("force_refresh", "true");
  }

  const timeoutMs = generateBrief ? GENERATE_TIMEOUT_MS : PREVIEW_TIMEOUT_MS;
  const { signal, cleanup } = createTimeoutSignal(timeoutMs);
  try {
    const response = await fetch(url.toString(), {
      method: "GET",
      headers: {
        "Accept": "application/json",
      },
      signal,
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const payload = await response.json();
    if (!payload || typeof payload !== "object" || typeof payload.brief_text !== "string") {
      throw new Error("Invalid brief payload received from backend");
    }
    return payload;
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error("Request timed out while fetching weekly brief");
    }
    throw error;
  } finally {
    cleanup();
  }
}
