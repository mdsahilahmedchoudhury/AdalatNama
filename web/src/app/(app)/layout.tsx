import { redirect } from "next/navigation";

import { BottomNav } from "@/components/shell/bottom-nav";
import { TopBar } from "@/components/shell/top-bar";
import { serverGet } from "@/lib/server-api";
import type { Me } from "@/lib/types";

/** Every signed-in screen: checks the session on the server, then draws the app shell. */
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const me = await serverGet<Me>("/api/me");
  if (!me.ok && me.status === 401) redirect("/login");
  if (!me.ok) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-4">
        <h1 className="text-lg font-semibold">AdalatNama is unavailable</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          The server could not be reached (status {me.status || "no response"}). Your data is safe. Try again
          in a minute; if it persists, tell your chamber&apos;s administrator.
        </p>
      </main>
    );
  }
  return (
    <>
      <TopBar me={me.data} />
      <div className="mx-auto w-full max-w-2xl px-4 pb-28 pt-5">{children}</div>
      <BottomNav />
    </>
  );
}
