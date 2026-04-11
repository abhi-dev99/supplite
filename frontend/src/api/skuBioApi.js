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
      throw new Error("Request timed out while fetching SKU bios");
    }
    throw error;
  } finally {
    cleanup();
  }
}

export async function fetchSkuBios({ dc = "ALL", limit = 1500 } = {}) {
  const baseUrl = resolveBaseUrl();
  const url = new URL("/api/skus/bios", baseUrl);
  if (dc) {
    url.searchParams.set("dc", String(dc));
  }
  if (limit) {
    url.searchParams.set("limit", String(limit));
  }

  const payload = await fetchJson(url.toString());
  if (!payload || !Array.isArray(payload.records)) {
    throw new Error("Invalid SKU bios payload received from backend");
  }
  return payload;
}
