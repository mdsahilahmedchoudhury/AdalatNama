import { LogoMark } from "@/components/brand/logo";
import { ROLE_LABELS, type Me } from "@/lib/types";
import { AccountMenu } from "./account-menu";

/** Chamber name, and who is signed in with what role. Sticky, safe-area aware. */
export function TopBar({ me }: { me: Me }) {
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-primary text-primary-foreground pt-[env(safe-area-inset-top)]">
      <div className="mx-auto flex h-16 w-full max-w-2xl items-center gap-3 px-4">
        <AccountMenu me={me} />
        <LogoMark size={30} className="shrink-0" />
        <div className="min-w-0 leading-tight">
          <p className="truncate text-base font-semibold" style={{ fontFamily: "var(--font-serif)" }}>
            {me.chamber.name}
          </p>
          <p className="truncate text-xs opacity-85">
            {me.user.name} · {ROLE_LABELS[me.user.role]}
          </p>
        </div>
      </div>
    </header>
  );
}
