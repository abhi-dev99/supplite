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

async function fetchJson(url) {
  const { signal, cleanup } = createTimeoutSignal(REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal,
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error("Request timed out while fetching signal timeline");
    }
    throw error;
  } finally {
    cleanup();
  }
}

export async function fetchSignalTimelineOptions() {
  const baseUrl = resolveBaseUrl();
  const url = new URL("/api/signals/timeline/options", baseUrl);
  const payload = await fetchJson(url.toString());
  if (!payload || !Array.isArray(payload.sku_options)) {
    throw new Error("Invalid timeline options payload received from backend");
  }
  return payload;
}

export async function fetchSignalTimeline({ skuId, periodDays }) {
  const baseUrl = resolveBaseUrl();
  const url = new URL("/api/signals/timeline", baseUrl);
  if (skuId) {
    url.searchParams.set("sku_id", String(skuId));
  }
  if (periodDays) {
    url.searchParams.set("period_days", String(periodDays));
  }

  const payload = await fetchJson(url.toString());
  if (!payload || !Array.isArray(payload.points)) {
    throw new Error("Invalid timeline payload received from backend");
  }
  return payload;
}
