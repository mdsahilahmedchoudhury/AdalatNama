# Open questions

Raised while reading the build brief and building Phase 0. Work continues on sensible defaults (noted for each question) until you answer.

1. **Repository visibility.** `AdalatNama` is public. Can it be made private? Client data will never be committed either way, but Phase 0.5 will record public cause lists and display boards as test fixtures, and those name real litigants. *Default:* fixtures are trimmed and redacted until the repository is private.
2. **Your eCourts app export.** Please share one real export file, the only sample that can't be sourced publicly. Which app produced it (eCourts Services app, Android or iOS), and from which screen ("My Cases" export or backup)? It will be kept in the git-ignored `private/` folder and never committed or pushed. *Blocks Phase 1, task 1.*
3. **First two courts.** Which High Court (and bench) and which district court should the first two adapters target? Your chamber's busiest forums are the best choice. *Blocks Phase 0.5 prioritisation and Phase 3.*
4. **Lawyers in more than one chamber?** v1 assumes one email belongs to one chamber (D-007). Is that true for your users?
5. **Email delivery.** Which SMTP provider and sender address should sign-in links come from? *Default:* console output plus `app.cli login-link` until configured.
6. **Hosting.** Where will production run (VPS provider and region, domain name)? This decides HTTPS setup, a Telegram webhook versus long polling, backups and encryption at rest. Hosting in India may matter for client comfort and DPDP. *Default:* single VPS with Docker Compose, as the brief says.
7. **Cause-list data model.** OK to split cause-list entries (public, shared) from matches (private to a chamber), as proposed in D-014?
8. **Private notes.** The brief says clerks cannot see "private notes". Who can: only the author, or the author plus seniors and the owner?
9. **Read-only client access.** The `client_readonly` role exists. Should client-facing screens be built in v1, or wait until requested (the brief lists the client portal as optional)? *Default:* role enforced server-side; no client screens until requested.
10. **Quiet hours.** The default is 22:00–07:00 chamber time. Is that right? Display-board alerts only fire during court hours, so they don't clash.
11. **Telegram bot token.** Not needed until Phase 2. When we get there, create the bot with BotFather and share the token through the environment's secrets, not in chat or git.
