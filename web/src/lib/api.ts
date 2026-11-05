/**
 * Browser-side calls to the API (same origin, proxied by Next.js).
 * Every state-changing request carries the CSRF header the API requires.
 */

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function readError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // fall through to the generic message
  }
  return `Something went wrong (HTTP ${res.status}). Please try again.`;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-Requested-With": "adalatnama" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Could not reach AdalatNama. Check your connection and try again.");
  }
  if (!res.ok) throw new ApiError(res.status, await readError(res));
  return (res.status === 204 ? undefined : await res.json()) as T;
}
