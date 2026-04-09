const DEFAULT_BASE_URL = "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 20000;

function resolveBaseUrl() {
  const configured = import.meta.env.VITE_BACKEND_BASE_URL;
  return (configured && configured.trim()) || DEFAULT_BASE_URL;
}

function createTimeoutSignal(timeoutMs) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  return { signal: controller.signal, cleanup: () => clearTimeout(timeoutId) };
}

async function fetchHeatmapJson(url) {
  const { signal, cleanup } = createTimeoutSignal(REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(url.toString(), {
      method: "GET",
      headers: { Accept: "application/json" },
      signal,
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const payload = await response.json();
    if (!payload || !Array.isArray(payload.points)) {
      throw new Error("Invalid heatmap payload received from backend");
    }
    return payload;
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error("Request timed out while fetching real estate heatmap");
    }
    throw error;
  } finally {
    cleanup();
  }
}

export async function fetchRealEstateHeatmap({ year, compareYear, limit = 30 } = {}) {
  const baseUrl = resolveBaseUrl();
  const scoredUrl = new URL("/api/signals/scored-real-estate-heatmap", baseUrl);
  const liveUrl = new URL("/api/signals/real-estate-heatmap", baseUrl);

  if (Number.isInteger(year)) {
    liveUrl.searchParams.set("year", String(year));
  }
  if (Number.isInteger(compareYear)) {
    liveUrl.searchParams.set("compare_year", String(compareYear));
  }
  if (Number.isInteger(limit)) {
    scoredUrl.searchParams.set("limit", String(limit));
    liveUrl.searchParams.set("limit", String(limit));
  }

  try {
    return await fetchHeatmapJson(scoredUrl);
  } catch (error) {
    try {
      return await fetchHeatmapJson(liveUrl);
    } catch {
      throw error;
    }
  }
}
