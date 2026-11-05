# Sources: where court data comes from, and how AdalatNama may read it

> **Status: DRAFT, Phase 0.5, desk research only (2026-11-05).**
> No court page has been fetched by this project yet. The build environment's network policy refused every court host (`ecourts.gov.in`, `*.nic.in`, `sci.gov.in`, `*.gov.in` tribunal sites), both for direct requests and for the page-fetching tool. Everything below comes from search-engine indexes and secondary sources. **Every access class is provisional** until verified against the live page with `api/tools/source_capture.py` (§6). No adapter code will be written from this draft.

## 1. How to read this document

**Access classes** (brief §2A):

| Class | Meaning |
|---|---|
| **OPEN** | Public page or file, no CAPTCHA, no login. May be fetched politely, subject to the source's terms. |
| **CAPTCHA** | A CAPTCHA guards the flow. Never bypassed; only human-in-the-loop or an equivalent OPEN channel. |
| **LOGIN** | Needs an account or credentials the chamber may or may not hold. |
| **NOT PERMITTED** | Terms, law or access rules exclude it for a private chamber. |
| **UNKNOWN** | Not enough evidence to classify. |

A `?` after a class means *provisional*.

**Evidence levels:**

- **V**: verified by fetching the live page (none yet).
- **O**: the exact URL was *observed* in a search-engine index or an official document found by search.
- **S**: described by a *secondary* source (news, blogs, aggregators, coaching sites). Weakest.

## 2. Summary matrix

Assumes the first courts are the **High Court of J&K and Ladakh (Srinagar wing)** and the **District Court, Srinagar**, matching the reference chamber. You have not confirmed this yet (OPEN_QUESTIONS Q3).

| Forum | Cause list | Case status | Orders | Display board |
|---|---|---|---|---|
| **J&K & Ladakh HC (Srinagar)** | HC website weekly PDF: **OPEN?** (O). eCourts HC Services: **CAPTCHA** (S) | eCourts HC Services: **CAPTCHA** (S) | eCourts HC Services: **CAPTCHA?** (S). HC website: UNKNOWN | `jkhc.gov.in/dis/`: **OPEN?** (O) |
| **District Court, Srinagar** | eCourts District Services: **CAPTCHA?** (S). Official email/SMS to registered advocate: **OPEN to that advocate** (S) | eCourts District Services: **CAPTCHA** (S) | eCourts District Services: **CAPTCHA?** (S) | **UNKNOWN**. Physical boards exist; an "online display board" is mentioned for e-Sewa Kendras (S) |
| **Supreme Court** | Daily PDF at `api.sci.gov.in`: **OPEN?** (O) | UNKNOWN | UNKNOWN | **UNKNOWN** |
| **Tribunals** | NCLT bench PDFs: **OPEN?** (O). NGT dated pages: **OPEN?** (O). CAT, ITAT, DRT: **UNKNOWN** | UNKNOWN | UNKNOWN | UNKNOWN |
| **Consumer commissions** | e-Jagriti by date + commission + court no.: **UNKNOWN** (S) | e-Jagriti: **UNKNOWN** (S) | UNKNOWN | UNKNOWN |
| **Official API (NJDG Open API)** | **NOT PERMITTED?**: for government institutional litigants only (S) | same | same | n/a |

## 3. Source details

### 3.1 eCourts High Court Services (`hcservices.ecourts.gov.in`): all High Courts

- **What it is:** a central portal for every High Court and bench, offering CNR search, case status, court orders, cause list and caveat search (O: homepage via search; [eCommittee description](https://ecommitteesci.gov.in/project/high-court-services/)).
- **Per-court entry point** (O): `https://hcservices.ecourts.gov.in/ecourtindiaHC/index_highcourt.php?state_cd=12&dist_cd=1&court_code=2&stateNm=Jammu+and+Kashmir` is the Srinagar Wing page. Madras is `state_cd=10&court_code=1`. The parameters are the portal's own state and bench codes, which is what §2A asks adapters to use.
- **CAPTCHA:** lookups need a typed CAPTCHA (S: [Vikaspedia guide](https://en.vikaspedia.in/viewcontent/e-governance/online-legal-services/how-to-check-court-case-status-online-in-india-a-complete-guide-to-ecourts-cnr-number-case-number-and-case-history?lgn=en)). The brief states the cause-list flow is CAPTCHA-gated. An accessible (audio) CAPTCHA was added across High Court sites (S: [India Education Diary](https://indiaeducationdiary.in/?p=163530)).
- **Terms:** a Terms and Conditions page exists (O: `hcservices.ecourts.gov.in/hcservices/static_pages_for_HC/static/terms.php`), but its **text has not been read**.
- **Classification:** cause list **CAPTCHA**, case status **CAPTCHA**, orders **CAPTCHA?**.
- **Do not:** OCR the CAPTCHA, reuse solved sessions, or call the portal's background endpoints directly to skip the form.

### 3.2 eCourts District & Taluka Court Services (`services.ecourts.gov.in`)

- **What it is:** CNR search, case status, orders and cause lists for district and subordinate courts. The current path is `/ecourtindia_v6/`; older district sites still link `ecourtindia_v4_bilingual` / `v5.1` `dailyboard.php` pages with state and district codes in the query string (S: [Parbhani district page](https://parbhani.gov.in/service/e-court-services)).
- **CAPTCHA:** CNR lookups need a visual CAPTCHA per request (S). That cause lists and orders are also gated is likely but **unverified**.
- **District websites:** `<district>.dcourts.gov.in` (S3WaaS platform). The [Srinagar site](https://srinagar.dcourts.gov.in/document-category/notification) has Case Status, Holiday List and Judges on Leave menus (O). Where its cause-list link points is unverified.
- **Classification:** case status **CAPTCHA**, cause list **CAPTCHA?**, orders **CAPTCHA?**.

### 3.3 Official push channels to advocates (eCourts CIS)

- eCourts sends **automated SMS and emails on case events** to advocates and litigants whose mobile number or email is registered with the court. That covers same-day proceedings, the next date and a reminder the day before (S: eCourts presentations hosted on [s3waas](https://cdnbbsr.s3waas.gov.in/s3ec04621fbd17da27241c58015eabe416/uploads/2023/11/2023112049.pdf), [Hindustan Times via PressReader](https://www.pressreader.com/india/hindustan-times-lucknow/20171127/281569471041806)). Court training schedules list "automatic receipt of SMS and e-Mail on Court listing" as an advocate tool (S).
- **Why it matters:** this is an official channel the advocate is already entitled to. Ingesting the advocate's *own* notifications (forwarded to a chamber mailbox, with consent) needs no scraping and no CAPTCHA. **Treat as the preferred route for district courts**, if the chamber's advocates receive these messages.
- **Classification:** **OPEN to the registered advocate** (S). Needs one real sample email from you. That is your own data, so asking is permitted (§2.1).

### 3.4 High Court of J&K and Ladakh: own website and display board

- **Cause lists (O):** weekly Srinagar lists are published as PDFs at
  `https://jkhighcourt.nic.in/upload/causelist/sgr/<YYYY>/<Mon>/weeklycauselist_<DDMMYYYY>/entirelist_sgr.pdf`.
  Observed for 27 Jan, 9 Mar, 27 Apr and 21 Oct 2026 ([example](https://jkhighcourt.nic.in/upload/causelist/sgr/2026/Oct/weeklycauselist_21102026/entirelist_sgr.pdf)). According to search snippets, the lists order matters by advocate and party. Unverified: whether daily or supplementary lists also exist, the Jammu-wing path (probably `/jmu/`), and the publication time.
- **Display board (O):** `https://jkhc.gov.in/dis/`, titled "Digital Display Board", described as showing court numbers, coram and serial numbers. LED screens in and outside courtrooms run on the same system (S). Format (HTML or JSON), refresh rate and access rules are unverified.
- **Classification:** cause list **OPEN?**, display board **OPEN?**, orders **UNKNOWN**.

### 3.5 Comparison High Courts (for adapter design, not first targets)

- **Delhi HC display board (O, official circular):** `delhihighcourt.nic.in/app/physical-display-board` shows court no., item no., judges, case no. and title ([circular](https://delhihighcourt.nic.in/files/2025-09/announcements/1131-it_cell-sd-updated.pdf)).
- **Karnataka HC:** a bench-wise display board at `display_board_bench.php` (S, coaching site).
- **Bombay HC:** an online display board is heavily relied on (S: [Bar & Bench](https://www.barandbench.com/amp/story/columns/three-hours-of-silence-the-human-cost-of-a-court-website-that-wont-load)).
- **Gujarat HC:** display board livestreamed on YouTube. Not machine-readable, so unsuitable (S: [Bar & Bench](https://www.barandbench.com/news/gujarat-high-court-display-board-youtube-channel)).
- **Lesson:** display boards differ per court. Expect one adapter per court, as the brief predicts.

### 3.6 Supreme Court of India

- **Daily cause lists (O):** `https://api.sci.gov.in/jonew/cl/<YYYY-MM-DD>/<M|F>_J_<n>.pdf` (Miscellaneous or Final list, part *n*). Older lists are on `main.sci.gov.in` ([example](https://api.sci.gov.in/jonew/cl/2026-10-26/M_J_2.pdf)). According to snippets, each list is grouped by "COURT NO.", then the judges, then items with serial no., case type and number, diary no., parties and advocates.
- **Policy (S):** contents may not be reproduced "without duly & prominently acknowledging the source" ([website policies](https://www.sci.gov.in/website-policies/)).
- **Display board:** not found.

### 3.7 Tribunals

- **NCLT (O):** per-bench PDF cause lists under `nclt.gov.in/sites/default/files/pdf_cause_list/…`. File names are hand-typed (e.g. `Supple 16.07.2025 Court 1.pdf`), so an index page is needed. A "customised cause list" exists at `efiling.nclt.gov.in/nclt/mis/causelist.php`; its access class is unknown.
- **NGT (O):** dated cause-list pages per bench (Chairperson Bench, Court II, Court III, RG Court, zonal benches), e.g. `greentribunal.gov.in/archive-principal-court-II-cause-list`. The archive runs to April 2026.
- **CAT (S):** daily cause lists per bench on `cgat.gov.in`. An aggregator says Delhi lists appear by 6 PM the previous working day and that the site format changed in April 2026. The Jammu bench handles J&K matters.
- **DRT (O):** individual tribunal sites (e.g. `drt2chennai.tn.nic.in`) have "Cause Lists" menus. Whether a national `drt.gov.in` list exists is unverified.
- **ITAT:** nothing found.
- **Classification:** NCLT and NGT **OPEN?**; CAT, DRT, ITAT **UNKNOWN**.

### 3.8 Consumer commissions: e-Jagriti

- Since **1 January 2025**, e-Jagriti (`e-jagriti.gov.in`) has replaced eDaakhil, OCMS, CMS and CONFONET for the district, state and national commissions (S: [Vikaspedia](https://en.vikaspedia.in/viewcontent/social-welfare/social-awareness/consumer-education/e-jagriti-portal-for-consumer-grievance-redressal), [Kashmir Life](https://kashmirlife.net/jammu-kashmir-consumer-commissions-handle-761-cases-through-e-jagriti-since-january-2025-446598/)).
- **Cause list:** choose hearing date, commission and court number, then "Get Causelist" (S).
- **Case status:** cases filed before 2025 use an "old case format" (S).
- **Classification:** **UNKNOWN** for every capability until the page is read.

### 3.9 Official APIs and third-party providers

- **NJDG Open API:** provided to Central and State Government departments, PSUs and other *institutional government litigants*, using a department ID and access key, after registering on NAPIX (S: [DAE circular](https://cdnbbsr.s3waas.gov.in/s35b8e4fd39d9786228649a8a8bec4e008/uploads/2023/08/2023081622.pdf), [NIC eCourts presentation](https://nja.gov.in/Concluded_Programmes/2022-23/P-1300_PPTs/1.eCourts.pdf)). **Not available to a private chamber** on this evidence, so **NOT PERMITTED?**.
- **Paid aggregators** ([Surepass](https://surepass.io/ecourt-cnr-search-api/), [eCourtsIndia](https://ecourtsindia.com/api), [Vakeel360](https://vakeel360.com/api)) sell case-status, cause-list and order APIs built on the public portals. They are **not official**, and how they handle CAPTCHAs is unknown. Using one is the "authorised provider" route in §2A and **your decision**. Nothing is integrated.

## 4. Terms of use, law and access rules

- **Terms not yet read.** `hcservices` has Terms and Conditions; `ecourts.gov.in` lists a Disclaimer, Terms, a Copyright Policy and a Hyperlinking Policy. None could be opened. They must be read before any adapter is built.
- **robots.txt is not permission.** The capture tool obeys robots.txt and treats an unreadable one as "skip", but the terms decide.
- **IT Act, 2000, s.43(b)** creates civil liability for downloading, copying or extracting data from a computer system *without the permission of its owner or person in charge*. It becomes an offence under s.66 if done dishonestly or fraudulently. Commentary says it has not been settled for public pages, and the government has reportedly said scraping publicly available data *may* breach s.43 (S: [law.asia](https://law.asia/india-data-scraping-regulation/), [S.S. Rana](https://ssrana.in/articles/data-scraping-issues-india/)). **Needs legal review.**
- **Proposed posture:**
  - Fetch only documents a court itself publishes for public download (PDF cause lists, display boards).
  - Fetch at human-like frequency, identified by our User-Agent.
  - Never circumvent a CAPTCHA, login or geofence.
  - Credit the source in the UI.
  - Stop if a court asks.
- **DPDP Act, 2023, s.3(c)(ii)** excludes personal data made publicly available under a legal obligation. Court-published cause lists *may* fall within it. AdalatNama will still treat everything it stores as confidential. **Needs legal confirmation.**
- **Geofencing:** some Indian government sites have blocked foreign IPs (Election Commission, Rajya Sabha; S: [ThePrint](https://theprint.in/india/rajya-sabha-site-blocked-outside-india-for-security-reasons-lok-sabha-site-still-accessible/510649)). Whether eCourts does is unverified. Production should be hosted in India anyway, and AdalatNama will **never** use VPNs or IP rotation to get around a block.

## 5. Recommended adapter plan (provisional, needs your decisions)

Order of preference for every capability:

1. an official push to the chamber;
2. a document the court publishes (OPEN);
3. a human-in-the-loop CAPTCHA step;
4. an authorised provider.

Never a bypass.

| # | Adapter | Source | Class | Phase | Blocked on |
|---|---|---|---|---|---|
| 1 | `hc_jk_site` CauseListSource | J&K HC weekly (and any daily or supplementary) PDF lists | OPEN? | 3 | Network access; verification; terms; Q3 |
| 2 | District court cause list | **(a)** eCourts automated emails to the advocate (email ingestion), **or (b)** human-solved CAPTCHA, **or (c)** paid provider | OPEN to advocate / CAPTCHA / provider | 3 | **Your decision**, plus one sample court email if (a) |
| 3 | `hc_jk_display` DisplayBoardSource | `jkhc.gov.in/dis/` | OPEN? | 4 | Verification during court hours; refresh rate; terms |
| 4 | HC and district orders | eCourts portals (CAPTCHA) or court websites; emails if they carry orders | CAPTCHA? / UNKNOWN | 5 | Verification; decision as in row 2 |
| 5 | Tribunals and consumer commissions | NCLT PDFs, NGT pages, e-Jagriti, CAT, ITAT | mixed | after 1–4 pass on real material | Your list of tribunals actually used |
| — | Case-status lookups | eCourts portals | CAPTCHA | not in v1 (F1 decision) | — |

No further adapter starts until the first two pass their fixture tests on real material (brief §6).

## 6. Verification checklist (runs as soon as the hosts are reachable)

```bash
cd api && uv run python -m tools.source_capture --targets tools/capture_targets.toml
```

The tool gets robots.txt first, waits at least 10 s (plus jitter) between requests to a host, retries politely, and captures display boards only in court hours. Results go to the git-ignored `private/source-captures/<date>/`, each with a `.meta.json` provenance record (URL, time in UTC and IST, SHA-256, headers, User-Agent).

For each row in §2:

1. Capture the page and confirm the class (any CAPTCHA, login or geofence?).
2. Read the terms, disclaimer and copyright pages and quote the relevant sentences here.
3. **Cause lists:** capture the index on 3–5 days, evening and morning, to learn when lists appear, the file-naming pattern, and how supplementary lists are marked.
4. **Display boards:** take 3–5 captures about 2 minutes apart in court hours. Record format, refresh behaviour, and how items are skipped or called out of order.
5. Record rate behaviour (response times, any 429s or blocks).
6. Update the class and evidence level to **V** and add the fixtures to the repository, once it is private or after redaction (D-019).

## 7. What I need from you

1. **Network access**, so this environment can reach the court hosts (environment settings → Network access → Allowed domains). If the sites turn out to block non-Indian IPs, the capture command in §6 has to run from an Indian machine or the future production server.
2. **Which High Court and district court come first** (Q3).
3. **The district-court route** (row 2 of §5): email ingestion, human-solved CAPTCHA, or a paid provider. If email: does your chamber receive eCourts SMS or emails for its cases? One sample message would show the format.
4. **Repository privacy** before fixtures are committed (Q1).
5. **A legal read of the eCourts and High Court terms** once they can be opened, and of the s.43 / DPDP points in §4. You are better placed to judge Indian law than I am.

## Sources consulted (2026-11-05, via web search)

- eCourts High Court Services, [home](https://hcservices.ecourts.gov.in/), [High Courts list](https://hcservices.ecourts.gov.in/hcservices/static_pages_for_HC/static/highcourts.php), [Srinagar Wing page](https://hcservices.ecourts.gov.in/ecourtindiaHC/index_highcourt.php?state_cd=12&dist_cd=1&court_code=2&stateNm=Jammu+and+Kashmir), [terms link](https://hcservices.ecourts.gov.in/hcservices/static_pages_for_HC/static/terms.php)
- [eCommittee: High Court Services](https://ecommitteesci.gov.in/project/high-court-services/), [eCommittee: Digital Display Board](https://ecommitteesci.gov.in/division/digital-display-board/)
- [J&K HC home](https://jkhighcourt.nic.in/), [weekly list 21 Oct 2026](https://jkhighcourt.nic.in/upload/causelist/sgr/2026/Oct/weeklycauselist_21102026/entirelist_sgr.pdf), [weekly list 27 Apr 2026](https://jkhighcourt.nic.in/upload/causelist/sgr/2026/April/weeklycauselist_27042026/entirelist_sgr.pdf), [display board](https://jkhc.gov.in/dis/)
- [District Court Srinagar](https://srinagar.dcourts.gov.in/document-category/notification), [Parbhani e-court services page](https://parbhani.gov.in/service/e-court-services)
- [Supreme Court cause list example](https://api.sci.gov.in/jonew/cl/2026-10-26/M_J_2.pdf), [SCI website policies](https://www.sci.gov.in/website-policies/)
- [Delhi HC display-board circular](https://delhihighcourt.nic.in/files/2025-09/announcements/1131-it_cell-sd-updated.pdf)
- [NCLT supplementary list example](https://nclt.gov.in/sites/default/files/pdf_cause_list/Supple%2016.07.2025%20Court%201.pdf), [NGT Court II cause lists](https://www.greentribunal.gov.in/archive-principal-court-II-cause-list), [DRT-2 Chennai](https://drt2chennai.tn.nic.in/)
- [Vikaspedia: e-Jagriti](https://en.vikaspedia.in/viewcontent/social-welfare/social-awareness/consumer-education/e-jagriti-portal-for-consumer-grievance-redressal), [Kashmir Life: e-Jagriti in J&K](https://kashmirlife.net/jammu-kashmir-consumer-commissions-handle-761-cases-through-e-jagriti-since-january-2025-446598/)
- [DAE circular on the NJDG Open API](https://cdnbbsr.s3waas.gov.in/s35b8e4fd39d9786228649a8a8bec4e008/uploads/2023/08/2023081622.pdf), [NIC eCourts presentation](https://nja.gov.in/Concluded_Programmes/2022-23/P-1300_PPTs/1.eCourts.pdf)
- [eCourts automated email/SMS presentation](https://cdnbbsr.s3waas.gov.in/s3ec04621fbd17da27241c58015eabe416/uploads/2023/11/2023112049.pdf), [HT: litigants to get email alerts](https://www.pressreader.com/india/hindustan-times-lucknow/20171127/281569471041806)
- [law.asia on data scraping](https://law.asia/india-data-scraping-regulation/), [S.S. Rana on data scraping](https://ssrana.in/articles/data-scraping-issues-india/)
- [ThePrint on Rajya Sabha geoblocking](https://theprint.in/india/rajya-sabha-site-blocked-outside-india-for-security-reasons-lok-sabha-site-still-accessible/510649), [Bar & Bench on Bombay HC](https://www.barandbench.com/amp/story/columns/three-hours-of-silence-the-human-cost-of-a-court-website-that-wont-load), [Bar & Bench on Gujarat HC](https://www.barandbench.com/news/gujarat-high-court-display-board-youtube-channel)
- Third-party providers (not official): [Surepass](https://surepass.io/ecourt-cnr-search-api/), [eCourtsIndia](https://ecourtsindia.com/api), [Vakeel360](https://vakeel360.com/api)
