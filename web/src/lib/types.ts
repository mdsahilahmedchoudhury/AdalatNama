/** Shapes returned by the AdalatNama API (mirrors api/app/schemas). */

export type UserRole = "owner" | "senior" | "associate" | "clerk" | "client_readonly";

export type Me = {
  user: { id: string; name: string; role: UserRole; email: string };
  chamber: { id: string; name: string; city: string | null; timezone: string };
};

export type Health = {
  status: "ok" | "degraded";
  database: { ok: boolean; detail: string | null };
  redis: { ok: boolean; detail: string | null };
  worker: { last_heartbeat_at: string | null; stale: boolean };
  schema_revision: string | null;
};

export const ROLE_LABELS: Record<UserRole, string> = {
  owner: "Owner",
  senior: "Senior",
  associate: "Associate",
  clerk: "Clerk",
  client_readonly: "Client (read-only)",
};
