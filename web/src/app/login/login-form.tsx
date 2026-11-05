"use client";

import { useState } from "react";
import { MailCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, apiPost } from "@/lib/api";

type State =
  | { kind: "idle" }
  | { kind: "sending" }
  | { kind: "sent"; email: string }
  | { kind: "error"; message: string };

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<State>({ kind: "idle" });

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState({ kind: "sending" });
    try {
      await apiPost("/api/auth/request-link", { email: email.trim() });
      setState({ kind: "sent", email: email.trim() });
    } catch (error) {
      const message =
        error instanceof ApiError && error.status === 422
          ? "That doesn't look like an email address."
          : error instanceof Error
            ? error.message
            : "Something went wrong. Please try again.";
      setState({ kind: "error", message });
    }
  }

  if (state.kind === "sent") {
    return (
      <Card role="status">
        <CardHeader>
          <MailCheck className="size-6 text-success" aria-hidden />
          <CardTitle>Check your email</CardTitle>
          <CardDescription>
            If <strong className="text-foreground">{state.email}</strong> belongs to a chamber member, a
            sign-in link is on its way. It works once and expires in 15 minutes.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" className="w-full" onClick={() => setState({ kind: "idle" })}>
            Use a different email
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sign in</CardTitle>
        <CardDescription>Enter the email your chamber registered for you.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              inputMode="email"
              autoComplete="email"
              autoCapitalize="none"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-invalid={state.kind === "error"}
              aria-describedby={state.kind === "error" ? "email-error" : undefined}
              placeholder="you@yourchambers.in"
            />
            {state.kind === "error" && (
              <p id="email-error" role="alert" className="text-sm text-destructive">
                {state.message}
              </p>
            )}
          </div>
          <Button type="submit" size="lg" disabled={state.kind === "sending" || email.trim() === ""}>
            {state.kind === "sending" ? "Sending link…" : "Email me a sign-in link"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
