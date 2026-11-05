"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { LogOut, Menu, MonitorSmartphone, X } from "lucide-react";

import { apiPost } from "@/lib/api";
import { ROLE_LABELS, type Me } from "@/lib/types";

/** The top-left menu: account details and sign-out. Grows with later phases. */
export function AccountMenu({ me }: { me: Me }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    const onClick = (e: MouseEvent) => {
      if (panel.current && !panel.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  async function signOut(everywhere: boolean) {
    setError(null);
    try {
      await apiPost(everywhere ? "/api/auth/logout-everywhere" : "/api/auth/logout");
      router.replace("/login");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not sign out.");
    }
  }

  return (
    <div className="relative" ref={panel}>
      <button
        type="button"
        className="-ml-2 inline-flex size-10 items-center justify-center rounded-md hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        aria-label={open ? "Close menu" : "Open menu"}
        aria-expanded={open}
        aria-controls="account-menu"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <X className="size-5" /> : <Menu className="size-5" />}
      </button>
      {open && (
        <div
          id="account-menu"
          className="absolute left-0 top-12 w-72 rounded-xl border border-border bg-card p-2 text-card-foreground shadow-lg"
        >
          <div className="px-3 py-2">
            <p className="font-semibold">{me.user.name}</p>
            <p className="text-sm text-muted-foreground">{me.user.email}</p>
            <p className="text-sm text-muted-foreground">
              {ROLE_LABELS[me.user.role]} · {me.chamber.name}
            </p>
          </div>
          <hr className="my-1" />
          <button
            type="button"
            onClick={() => signOut(false)}
            className="flex w-full items-center gap-3 rounded-md px-3 py-3 text-left text-sm hover:bg-muted"
          >
            <LogOut className="size-4" aria-hidden /> Sign out
          </button>
          <button
            type="button"
            onClick={() => signOut(true)}
            className="flex w-full items-center gap-3 rounded-md px-3 py-3 text-left text-sm hover:bg-muted"
          >
            <MonitorSmartphone className="size-4" aria-hidden /> Sign out on all devices
          </button>
          {error && (
            <p role="alert" className="px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
