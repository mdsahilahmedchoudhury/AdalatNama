import type { Metadata } from "next";

import { LogoMark, Wordmark } from "@/components/brand/logo";
import { VerifyCard } from "./verify-card";

export const metadata: Metadata = { title: "Signing in" };

export default function VerifyPage() {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col justify-center px-4 py-10">
      <div className="mb-8 flex items-center gap-3">
        <LogoMark size={44} />
        <Wordmark className="text-2xl" />
      </div>
      <VerifyCard />
    </main>
  );
}
