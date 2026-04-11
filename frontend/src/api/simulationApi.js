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
      throw new Error("Request timed out while fetching simulation data");
    }
    throw error;
  } finally {
    cleanup();
  }
}

export async function fetchSimulationOptions({ dc = "ALL" } = {}) {
  const baseUrl = resolveBaseUrl();
  const url = new URL("/api/simulations/options", baseUrl);
  if (dc) {
    url.searchParams.set("dc", String(dc));
  }
  const payload = await fetchJson(url.toString());
  if (!payload || !Array.isArray(payload.sku_options)) {
    throw new Error("Invalid simulation options payload received from backend");
  }
  return payload;
}

export async function fetchEarlyCatchSimulation({ skuId, metro, horizonDays, baselineLagDays, earlierByDays, marginRate }) {
  const baseUrl = resolveBaseUrl();
  const url = new URL("/api/simulations/early-catch", baseUrl);
  if (skuId) {
    url.searchParams.set("sku_id", String(skuId));
  }
  if (metro) {
    url.searchParams.set("metro", String(metro));
  }
  if (horizonDays) {
    url.searchParams.set("horizon_days", String(horizonDays));
  }
  if (baselineLagDays) {
    url.searchParams.set("baseline_lag_days", String(baselineLagDays));
  }
  if (earlierByDays) {
    url.searchParams.set("earlier_by_days", String(earlierByDays));
  }
  if (marginRate) {
    url.searchParams.set("margin_rate", String(marginRate));
  }

  const payload = await fetchJson(url.toString());
  if (!payload || !Array.isArray(payload.points) || !payload.summary) {
    throw new Error("Invalid simulation payload received from backend");
  }
  return payload;
}
