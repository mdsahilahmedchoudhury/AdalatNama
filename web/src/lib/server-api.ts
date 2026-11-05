import "server-only";

import { cookies } from "next/headers";

/**
 * Server Component calls to the API. Forwards the visitor's cookies so the
 * API sees the same session; never cached, because every answer is per-user.
 */
const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

export type ServerResult<T> = { ok: true; data: T } | { ok: false; status: number };

export async function serverGet<T>(path: string): Promise<ServerResult<T>> {
  const cookieHeader = (await cookies()).toString();
  try {
    const res = await fetch(`${API}${path}`, {
      headers: cookieHeader ? { cookie: cookieHeader } : {},
      cache: "no-store",
    });
    if (!res.ok) return { ok: false, status: res.status };
    return { ok: true, data: (await res.json()) as T };
  } catch {
    return { ok: false, status: 0 };
  }
}
