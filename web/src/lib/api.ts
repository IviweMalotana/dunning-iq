/**
 * Tiny typed fetch client for the Dunning IQ FastAPI backend.
 * Server Components call `apiGet` directly; client components use `swrFetcher`.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiGet<T>(
  path: string,
  init?: RequestInit & { revalidate?: number },
): Promise<T> {
  const { revalidate, ...rest } = init ?? {};
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: { Accept: "application/json", ...(rest.headers ?? {}) },
    // Dashboards should feel live; revalidate often by default.
    next: { revalidate: revalidate ?? 15 },
  });
  if (!res.ok) {
    throw new ApiError(res.status, `GET ${path} failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export async function apiSend<T>(
  path: string,
  method: "POST" | "PATCH" | "PUT" | "DELETE",
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    throw new ApiError(res.status, `${method} ${path} failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

/** Fetcher for SWR in client components. */
export const swrFetcher = <T>(path: string): Promise<T> => apiGet<T>(path);
