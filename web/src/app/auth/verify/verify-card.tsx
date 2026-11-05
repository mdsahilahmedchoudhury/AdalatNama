"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiPost } from "@/lib/api";

/** The token arrives in the URL fragment (#token=…), which never reaches any server log. */
function readToken(): string {
  return new URLSearchParams(window.location.hash.slice(1)).get("token") ?? "";
}

function subscribe(onChange: () => void) {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

export function VerifyCard() {
  const router = useRouter();
  // null while rendering on the server; the token (or "") once in the browser.
  const token = useSyncExternalStore(subscribe, readToken, () => null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // A button (not an automatic request) so email link scanners that open the
  // page cannot use up the one-time link.
  async function signIn() {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await apiPost("/api/auth/verify", { token });
      window.history.replaceState(null, "", "/auth/verify");
      router.replace("/");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign-in failed. Request a new link.");
      setBusy(false);
    }
  }

  if (token === null) {
    return <p className="text-sm text-muted-foreground">Preparing sign-in…</p>;
  }

  if (!token) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>This link is incomplete</CardTitle>
          <CardDescription>Open the full link from your email, or request a new one.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild className="w-full">
            <Link href="/login">Request a new link</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sign in to AdalatNama</CardTitle>
        <CardDescription>You will stay signed in on this device for 30 days.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <Button size="lg" onClick={signIn} disabled={busy}>
          {busy ? "Signing in…" : "Continue"}
        </Button>
        {error && (
          <Button asChild variant="outline">
            <Link href="/login">Request a new link</Link>
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
