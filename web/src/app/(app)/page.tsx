import { CheckCircle2, CircleAlert, FileUp } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { serverGet } from "@/lib/server-api";
import type { Health, Me } from "@/lib/types";

function todayHeading(timeZone: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone,
  })
    .format(new Date())
    .toUpperCase();
}

function StatusRow({ label, ok, detail }: { label: string; ok: boolean; detail: string }) {
  return (
    <li className="flex items-start gap-3 py-2">
      {ok ? (
        <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-success" aria-hidden />
      ) : (
        <CircleAlert className="mt-0.5 size-5 shrink-0 text-warning" aria-hidden />
      )}
      <div>
        <p className="text-sm font-medium">
          {label} <span className="sr-only">{ok ? "working" : "needs attention"}</span>
        </p>
        <p className="text-sm text-muted-foreground">{detail}</p>
      </div>
    </li>
  );
}

export default async function HomePage() {
  const [me, health] = await Promise.all([serverGet<Me>("/api/me"), serverGet<Health>("/api/health")]);
  const tz = me.ok ? me.data.chamber.timezone : "Asia/Kolkata";
  const firstName = me.ok ? me.data.user.name.split(" ")[0] : "";

  return (
    <div className="flex flex-col gap-5">
      <section>
        <p className="text-xs font-semibold tracking-wider text-accent">{todayHeading(tz)}</p>
        <h1 className="mt-1 text-2xl font-semibold" style={{ fontFamily: "var(--font-serif)" }}>
          Good to see you, {firstName}
        </h1>
      </section>

      <Card>
        <CardHeader>
          <FileUp className="size-6 text-primary" aria-hidden />
          <CardTitle>No cases yet</CardTitle>
          <CardDescription>
            Your chamber&apos;s cases arrive with the first import of the eCourts app export (the next build
            phase). Until then there is nothing to list, and nothing is made up.
          </CardDescription>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>System status</CardTitle>
          <CardDescription>What this AdalatNama server can reach right now.</CardDescription>
        </CardHeader>
        <CardContent>
          {health.ok ? (
            <ul className="divide-y divide-border">
              <StatusRow
                label="Database"
                ok={health.data.database.ok}
                detail={health.data.database.ok ? `Schema ${health.data.schema_revision}` : "Unreachable"}
              />
              <StatusRow
                label="Job queue"
                ok={health.data.redis.ok}
                detail={health.data.redis.ok ? "Connected" : "Unreachable"}
              />
              <StatusRow
                label="Background worker"
                ok={!health.data.worker.stale}
                detail={
                  health.data.worker.last_heartbeat_at
                    ? `Last reported ${new Intl.DateTimeFormat("en-IN", {
                        timeStyle: "medium",
                        timeZone: tz,
                      }).format(new Date(health.data.worker.last_heartbeat_at))}`
                    : "Has not reported in. Scheduled jobs will not run."
                }
              />
            </ul>
          ) : (
            <p className="text-sm text-destructive">
              Status unavailable (HTTP {health.status || "no response"}).
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
