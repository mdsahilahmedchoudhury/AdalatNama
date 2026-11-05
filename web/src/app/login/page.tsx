import type { Metadata } from "next";

import { LogoMark, Wordmark } from "@/components/brand/logo";
import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col justify-center px-4 py-10">
      <div className="mb-8 flex items-center gap-3">
        <LogoMark size={44} />
        <div>
          <Wordmark className="text-2xl" />
          <p className="text-sm text-muted-foreground">Your chamber&apos;s case diary</p>
        </div>
      </div>
      <LoginForm />
      <p className="mt-6 text-xs leading-relaxed text-muted-foreground">
        No password needed. We email you a one-time link that signs you in on this device.
      </p>
    </main>
  );
}
