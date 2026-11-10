# Sources: where court data comes from, and how AdalatNama may read it

> **Status: Phase 0.5. First verification round done on 2026-11-10** (14:53–15:10 IST, a court day).
> 33 polite requests were made with `api/tools/source_capture.py`. 23 pages and files were saved; the rest failed or were skipped (manifest in §8). Rows marked **V** were checked against the live source. Rows still marked **O** or **S** come from desk research and remain provisional.
> **J&K & Ladakh High Court and District Court Srinagar are the pilot**, not the limit. The goal is every High Court, district court, tribunal and commission; §5 explains how the design scales.

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

- **V**: verified by fetching the live source on the date given.
- **O**: the URL was observed in a search index or an official document.
- **S**: described by a secondary source.

## 2. Summary matrix

| Forum | Cause list | Case status | Orders | Display board |
|---|---|---|---|---|
| **J&K & Ladakh HC** (pilot) | HC website daily PDFs: **OPEN** (V) | eCourts HC Services: **CAPTCHA** (V) | eCourts HC Services: **CAPTCHA** (V); the HC website's "Orders/Judgements" link points there | `jkhc.gov.in/dis/`: **OPEN** (V); live behaviour still to observe (§6) |
| **District Court Srinagar** (pilot) | District website **and** eCourts District Services: **CAPTCHA** (V). eCourts email/SMS to the registered advocate: **OPEN to that advocate** (S) | eCourts District Services: **CAPTCHA** (V) | eCourts District Services: **CAPTCHA** (V: CAPTCHA on the portal; order flow not separately opened) | **UNKNOWN**: no online board found |
| **Supreme Court** | Daily PDF at `api.sci.gov.in`: **OPEN** (V) | UNKNOWN | UNKNOWN | UNKNOWN. `www.sci.gov.in` refuses automated requests (403, V) |
| **Other High Courts** | Not yet surveyed (§6, item 1) | eCourts HC Services: **CAPTCHA** (V, same portal) | eCourts HC Services: **CAPTCHA** (V) | Delhi: board exists, data loaded by script (V); others not yet surveyed |
| **Tribunals** | NGT: cause-list pages **OPEN** (V). NCLT, ITAT: certificate errors (§3.7). CAT: a JavaScript app (V); data route unknown | UNKNOWN | UNKNOWN | UNKNOWN |
| **Consumer commissions** | e-Jagriti: a JavaScript app (V); data route **UNKNOWN** | UNKNOWN | UNKNOWN | UNKNOWN |
| **Official API (NJDG Open API)** | **NOT PERMITTED?**: for government institutional litigants only (S) | same | same | n/a |

## 3. Source details

### 3.1 eCourts High Court Services (`hcservices.ecourts.gov.in`): all High Courts

- **Verified 2026-11-10:**
  - `main.php` loads the `securimage` CAPTCHA script, with a separate CAPTCHA box for every flow:
    - cause list (`captcha_box_clcauselist`);
    - CNR;
    - case number (`captcha_box_cocasenumber`);
    - party name (`captcha_box_copartyname`);
    - advocate name (`captcha_box_csadvname`);
    - court number (`captcha_box_cocourtnumber`);
    - order date (`captcha_box_coorderdate`);
    - FIR, filing number, act and caveat.
  - The Srinagar Wing page (`ecourtindiaHC/index_highcourt.php?state_cd=12&dist_cd=1&court_code=2`) links Case Status, Case Orders/Judgement, Order Date and Cause List.
  - **Every flow is CAPTCHA-gated.**
- **Terms (V, quoted):** "The documents and information displayed in this website are for reference purposes only and do not purport to a legal document." Users should "verify / check with the authorities concerned or the relevant record". **The terms say nothing about automated access.**
- **Implication:** for all 25 High Courts, the eCourts portal cannot feed cause lists or orders automatically. Use each High Court's own published lists (§3.4, §5) and, for orders, a human-in-the-loop step or an official push.

### 3.2 eCourts District & Taluka Court Services (`services.ecourts.gov.in/ecourtindia_v6/`)

- **Verified 2026-11-10:** the portal loads `securimage` with an image and an audio CAPTCHA (`captcha_cnr`, `fcaptcha_code`, `captcha_image_audio`). Case Status, Court Orders and Cause List are its menu items. **CAPTCHA**.
- **District websites** (`<district>.dcourts.gov.in`, a WordPress "S3WaaS" site with an eCourts plugin), verified on Srinagar:
  - The **Cause List / Daily Board** page has a form with fields Court Complex / Establishment (`est_code`), Court Number, Cause List Date, Civil/Criminal, and a `securimage-wp` CAPTCHA ("Please Enter the Captcha *").
  - **CAPTCHA**, so there is **no open route to district cause lists**.
- **Reachability:** `srinagar.dcourts.gov.in` dropped the connection once (a reset after 3 s), then answered normally. Treat it as unreliable from non-Indian networks.

### 3.3 Official push channels to advocates (eCourts CIS)

- eCourts sends automated SMS and emails on case events to advocates and litigants registered with the court: proceedings, the next date, and a reminder the day before (S: eCourts presentations and press, see Sources).
- **This is the only non-CAPTCHA route found for district courts**, and one adapter would cover *every* district court in India, because the messages come from one national system. Still unverified: the message format, and whether listing alerts carry court number and item number. **Needs one real sample** from you (your own data, so asking is permitted).

### 3.4 High Court of J&K and Ladakh: own website and display board (pilot)

- **Cause-list index pages (V):**
  - `jkhighcourt.nic.in/causelistk.php` (Srinagar);
  - `jkhighcourt.nic.in/causelistj.php` (Jammu);
  - `jkhighcourt.nic.in/causelistl.php` (Ladakh);
  - `causelistk_2022.php` holds the archive.
- **Files (V):** a weekly folder `upload/causelist/sgr/<YYYY>/<Mon>/weeklycauselist_<DDMMYYYY>/` contains:
  - `causelist_<DDMMYYYY>.pdf`, **one per day**. On Tuesday 10 Nov the lists for Wed 11, Thu 12 and Fri 13 Nov were already published, so lists appear days ahead;
  - supplementary and special supplementary lists;
  - `entirelist_sgr.pdf`, the whole week (162 pages, with an index of benches and item ranges per day);
  - `rjcourtsgr.pdf`, the Registrar Judicial list.
- **Real-world quirks (V)** the adapter must handle:
  - Links use Windows backslashes (`\upload\causelist\…`).
  - A link labelled "Supplementary Cause List - 11.11.2026" points at a file named for 21.10.2026.
  - Another supplementary link returned **404**.
  - The month folder is `Nov` in November and was `April` in April (not always three letters).
- **PDF format (V, 11 Nov list):**
  - It is a **text PDF**, not a scan (`dompdf`), so no OCR is needed.
  - Layout: "REGULAR CAUSE LIST FOR WEDNESDAY(11/11/2026)", then `BENCH NO.: DB-II`, `COURT NO.: 2`, the judges, and section headings ("ADMISSION/ORDERS", "a) BEFORE NOTICE MATTERS").
  - Each item has a serial number, case numbers with linked applications (e.g. `CM(7741/2026) IN LPA 126/2026`), "PETITIONER Vs RESPONDENT", a counsel line ("… FOR PET." / "… FOR RES."), and connected matters ("c/w i) WP(C) 1707/2021").
  - The three columns run together when extracted as plain text, so the parser must use word positions.
- **Display board (V):** `jkhc.gov.in/dis/` is **server-rendered HTML** (no API call). It has `<meta http-equiv="Refresh" content="120">`, one table per wing (Srinagar, Jammu) and a "Messages" table keyed by court number. Footer: "Court Nos. which are not listed are currently not in session" and "There may be a time gap in internet transmission. Confirm exact status at the concerned court."
  - Every snapshot from 14:53 to about 15:10 IST read **"No Cases To Display"** for both wings, with unchanged morning messages. Behaviour while items are actually being called has **not** been seen yet (§6).
- **Terms:** the HC site has no terms page at `disclaimer.php` (404). Its policy pages are not yet found.

### 3.5 Other High Courts (for the all-High-Court rollout)

- **Delhi (V):** `delhihighcourt.nic.in/app/physical-display-board` is a page whose data is loaded by script (`physical_display_board`). The data call has not yet been observed. An official circular says it shows court no., item no., judges, case no. and title.
- **Karnataka** (`display_board_bench.php`, S), **Bombay** (S) and **Gujarat** (YouTube stream, unusable, S): not yet verified.
- The other 21 High Courts have **not been surveyed yet** (§6, item 1).

### 3.6 Supreme Court of India

- **Daily cause lists (V):** `https://api.sci.gov.in/jonew/cl/<YYYY-MM-DD>/<M|F>_J_<n>.pdf`. The host serves a robots.txt (200) that allows this path.
  - It is a **text PDF** (`mPDF`).
  - Layout: court name ("CHIEF JUSTICE'S COURT"), judges, time, then columns "SNo. | Case No. | Petitioner / Respondent | Petitioner/Respondent Advocate", IA details, the date and time the list was generated, and the signing officer.
- **Main site:** `www.sci.gov.in` returned **403** for robots.txt, so the capture tool skips the host. Website policies (reproduction with acknowledgement, S) are still unread.

### 3.7 Tribunals

- **NGT (V):** `greentribunal.gov.in/archive-principal-court-II-cause-list` is a Drupal page that loads without JavaScript and lists dated cause lists per bench. Its PDF link pattern is not yet extracted. **OPEN?**
- **NCLT (V, failed):** `nclt.gov.in` and `efiling.nclt.gov.in` fail certificate verification ("self-signed certificate in certificate chain"). We will **not** turn verification off. Next: check whether the server sends an incomplete chain (a browser fills that gap; we can add the missing intermediate certificate) or whether this network intercepts it.
- **ITAT (V, failed):** `itat.gov.in` fails with "unable to get local issuer certificate", probably a missing intermediate certificate. Same next step.
- **CAT (V):** `cgat.gov.in` is a JavaScript application ("You need to enable JavaScript to run this app"). Its data calls have not been observed yet.
- **DRT:** per-tribunal sites (O). Not yet visited.

### 3.8 Consumer commissions: e-Jagriti

- **Verified:** `e-jagriti.gov.in` is a JavaScript application (a single `main.*.js` bundle). Since 1 Jan 2025 it has replaced eDaakhil, OCMS, CMS and CONFONET (S).
- The cause-list route (date + commission + court no., S) and any CAPTCHA can only be seen by opening it in a real browser (Playwright, allowed by the brief where JavaScript is unavoidable). **UNKNOWN**.

### 3.9 Official APIs and third-party providers

- **NJDG Open API:** for Central and State Government departments, PSUs and other institutional government litigants, through NAPIX registration (S). **Not available to private chambers**, so **NOT PERMITTED?**.
- **Paid aggregators** (Surepass, eCourtsIndia, Vakeel360) are not official, and their CAPTCHA handling is unknown. Using one is the "authorised provider" route in §2A and is **your decision**. Nothing is integrated.

## 4. Terms of use, law and access rules

- **eCourts Copyright Policy (V, quoted):** "The contents on this website shall not be reproduced partially or fully, without duly & prominently acknowledging the source. The contents of this website cannot be used in any misleading or objectionable context or derogatory manner." So **every cause-list entry, board reading and order shown by AdalatNama must name its source** (court and document), as the brief already requires for dates.
- **eCourts Terms / District website policies (V):** "for reference purposes only and do not purport to a legal document". This supports the brief's "verify against the order" rule.
- **Hyperlinking policy (V):** concerns links *from* eCourts; it has no rule on linking to or fetching from eCourts.
- **No published rule on automated access** was found on any eCourts or district page (V). None of the verified hosts publishes a robots.txt (404), except `api.sci.gov.in` (200, allows the cause-list path) and `www.sci.gov.in` (403).
- **IT Act, 2000, s.43(b)** (civil liability for downloading or extracting data without the permission of the person in charge) remains the open legal question. A court publishing a PDF for public download is arguably permission to download it. Automated *form* access is not, and the CAPTCHAs show the courts do not want that automated. **Needs your legal review.**
- **DPDP Act, 2023, s.3(c)(ii)** (data made public under a legal obligation) may cover published cause lists. **Needs legal confirmation.**
- **Posture (D-020):**
  - Fetch only documents and pages a court publishes openly.
  - Fetch at human-like frequency, identified by our User-Agent, and credit the source.
  - Never bypass a CAPTCHA, login, certificate check or geofence.
  - Stop on request.

## 5. Scaling from the pilot to every court

The brief requires the first two adapters to pass on real material before any other starts (§6). The pilot exists to prove the pipeline: fetch, parse, match, consolidate, alert. The rollout then goes source family by source family:

| Source family | How many | Route | Adapter shape |
|---|---|---|---|
| **High Court cause lists** | 25 HCs (plus benches) | Each HC's own published lists (the eCourts HC portal is CAPTCHA-gated, V) | One adapter **per HC website**, sharing a common PDF/HTML parsing toolkit and the matching ladder. Each needs its own fixtures, because layouts differ (J&K and the Supreme Court already differ). |
| **High Court display boards** | 25 | Each HC's board (J&K: HTML; Delhi: data loaded by script) | One adapter per HC; polling only during court hours, only for halls with a followed case. |
| **District court cause lists** | ~700 district sites, one national system | eCourts email/SMS push (one adapter for all), or a human-solved CAPTCHA (one adapter for all S3WaaS district sites, since the form is the same), or a provider | **One adapter family covers every district**, parameterised by the codes the portal publishes (`est_code`, court number). |
| **Orders** | all forums | eCourts portals are CAPTCHA-gated; emails may carry them | Decided with the district route. |
| **Tribunals and commissions** | NCLT, NCLAT, CAT, ITAT, DRT/DRAT, NGT, consumer commissions… | Per-tribunal websites and apps | One adapter per tribunal family, in the order of your chamber's practice (Q14). |

## 6. Remaining Phase 0.5 work

1. **Survey all 25 High Courts.** For each: where cause lists are published (PDF or HTML, daily or weekly, advance publication), whether a display board is online and in what format, CAPTCHA or login status, and the terms page. About two to four polite requests per court.
2. **Observe the J&K display board while courts are calling items:** 4–6 snapshots between 10:30 and 13:00 IST on a court day. Today's afternoon snapshots only showed "No Cases To Display".
3. **Record when J&K cause lists appear:** capture the index pages in the evening and morning over a few days.
4. **Open the JavaScript apps in a browser** (e-Jagriti, CAT, the Delhi board) to see their data calls and any CAPTCHA.
5. **Certificate chains for NCLT and ITAT:** find out whether a missing intermediate certificate is the cause; if so, add the official one rather than switching verification off.
6. **Make the fixtures durable:**
   - Captured files currently live only in this session's git-ignored `private/` folder and **will be lost when the cloud container is reclaimed**.
   - They name real litigants and advocates, so they can be committed only once the repository is **private** (Q1).
   - Otherwise they must be redacted first.
7. Your decisions in §7.

## 7. Decisions needed from you

1. **District-court route** (Q12): eCourts email/SMS ingestion (recommended, scales nationally; needs one sample message), a human-solved CAPTCHA, or a paid provider.
2. **Make the repository private** (Q1), so the verified fixtures can be committed.
3. **Legal read** of §4 (s.43(b), DPDP s.3(c)(ii), the copyright acknowledgement duty).
4. **Order of rollout:** after the pilot, which High Courts and tribunals first (Q14)?

## 8. Capture manifest, 2026-11-10 (IST)

The files are in the git-ignored `private/source-captures/2026-11-10/`, each with a `.meta.json` provenance record. The User-Agent was `AdalatNama-SourceDiscovery/0.1 (+repository URL; …)`, with at least 10 s plus jitter between requests to a host.

| Capture | Outcome | HTTP | Bytes | SHA-256 (first 16) | Time |
|---|---|---|---|---|---|
| `jkhc-home` | saved | 200 | 170296 | 6e9e371a8510919b | 14:53:30 |
| `jkhc-causelist-sgr-weekly-2026-10-21` | saved | 200 | 2483298 | 0713b70743050240 | 14:53:43 |
| `jkhc-display-board-sgr` | saved | 200 | 6442 | e548cc465eeac893 | 14:53:57 |
| `hcservices-main` | saved | 200 | 578605 | 9204607fad9e4333 | 14:54:11 |
| `hcservices-terms` | saved | 200 | 46792 | a47a0b1bfc58710a | 14:54:20 |
| `hcservices-jk-srinagar` | saved | 200 | 48608 | 802375f6dbe6c9d0 | 14:54:33 |
| `ecourts-district-main` | saved | 200 | 110361 | b372164099655cdf | 14:54:47 |
| `ecourts-home` | saved | 200 | 141852 | 4164f51121b598ff | 14:55:04 |
| `srinagar-district-home` | saved | 200 | 176716 | bae855304d886dbc | 14:55:20 |
| `delhihc-display-board` | saved | 200 | 33059 | e082d024e630d254 | 14:55:32 |
| `sci-causelist-2026-10-26-M_J_2` | saved | 200 | 554983 | 9ef641808885f3aa | 14:55:50 |
| `sci-website-policies` | skipped: robots.txt 403 | — | — | — | — |
| `nclt-supplementary-2025-07-16` | unreachable: certificate | — | — | — | — |
| `nclt-efiling-causelist` | unreachable: certificate | — | — | — | — |
| `ngt-principal-court2-causelists` | saved | 200 | 43927 | 2a540b1778ca8199 | 14:56:06 |
| `ejagriti-home` | saved (JS app shell) | 200 | 888 | 0939c275fe4d2417 | 14:56:21 |
| `cat-home` | saved (JS app shell) | 200 | 1440 | 5df084960fc6e272 | 14:56:35 |
| `itat-home` | unreachable: certificate | — | — | — | — |
| `jkhc-causelist-index-sgr` | saved | 200 | 152885 | 89c28b9d002fb764 | 14:57:17 |
| `jkhc-causelist-index-jmu` | saved | 200 | 253587 | 135941f78db82eee | 14:57:32 |
| `jkhc-causelist-index-ladakh` | saved | 200 | 152429 | e67f5032a1ec1ab6 | 14:57:44 |
| `jkhc-causelist-sgr-daily-2026-11-11` | saved | 200 | 185337 | 053813e533ad767d | 14:58:13 |
| `jkhc-causelist-sgr-supplementary-2026-11-11` | 404 (dead link on the index) | 404 | 670 | — | 14:58:27 |
| `ecourts-policy-terms` | saved | 200 | 107357 | d4e76a7935cf5680 | 14:59:23 |
| `ecourts-policy-copyright` | saved | 200 | 105605 | 48d98d27412a7aea | 14:59:36 |
| `ecourts-policy-hyperlink` | saved | 200 | 106228 | ca65f7e52b510d03 | 14:59:48 |
| `ecourts-policy-disclaimer` | saved | 200 | 105881 | b1f61bda3b430f43 | 14:59:59 |
| `srinagar-district-causelist-page` | saved | 200 | 135185 | f406876eb0d691f3 | 15:00:12 |
| `srinagar-district-website-policies` | saved | 200 | 118245 | 7664b5ed7dc57d82 | 15:00:30 |
| `jkhc-website-policies-probe` | 404 (no such page) | 404 | 670 | — | 15:00:45 |
| `jkhc-display-board-sgr-t0926` … `-t09xx` | saved, identical to the first board snapshot | 200 | 6442 | e548cc465eeac893 | 14:57–15:10 |

## Sources consulted

Live pages (V) are listed in §8. Desk research (2026-11-05, via web search):

- [eCommittee: High Court Services](https://ecommitteesci.gov.in/project/high-court-services/), [eCommittee: Digital Display Board](https://ecommitteesci.gov.in/division/digital-display-board/)
- [Vikaspedia: eCourts case status guide](https://en.vikaspedia.in/viewcontent/e-governance/online-legal-services/how-to-check-court-case-status-online-in-india-a-complete-guide-to-ecourts-cnr-number-case-number-and-case-history?lgn=en), [India Education Diary: accessible CAPTCHAs on High Court sites](https://indiaeducationdiary.in/?p=163530)
- [Delhi HC display-board circular](https://delhihighcourt.nic.in/files/2025-09/announcements/1131-it_cell-sd-updated.pdf), [Bar & Bench on Bombay HC](https://www.barandbench.com/amp/story/columns/three-hours-of-silence-the-human-cost-of-a-court-website-that-wont-load), [Bar & Bench on Gujarat HC](https://www.barandbench.com/news/gujarat-high-court-display-board-youtube-channel)
- [NCLT cause list example](https://nclt.gov.in/sites/default/files/pdf_cause_list/Supple%2016.07.2025%20Court%201.pdf), [DRT-2 Chennai](https://drt2chennai.tn.nic.in/)
- [Vikaspedia: e-Jagriti](https://en.vikaspedia.in/viewcontent/social-welfare/social-awareness/consumer-education/e-jagriti-portal-for-consumer-grievance-redressal), [Kashmir Life: e-Jagriti in J&K](https://kashmirlife.net/jammu-kashmir-consumer-commissions-handle-761-cases-through-e-jagriti-since-january-2025-446598/)
- [DAE circular on the NJDG Open API](https://cdnbbsr.s3waas.gov.in/s35b8e4fd39d9786228649a8a8bec4e008/uploads/2023/08/2023081622.pdf), [NIC eCourts presentation](https://nja.gov.in/Concluded_Programmes/2022-23/P-1300_PPTs/1.eCourts.pdf)
- [eCourts automated email/SMS presentation](https://cdnbbsr.s3waas.gov.in/s3ec04621fbd17da27241c58015eabe416/uploads/2023/11/2023112049.pdf), [HT: litigants to get email alerts](https://www.pressreader.com/india/hindustan-times-lucknow/20171127/281569471041806)
- [law.asia on data scraping](https://law.asia/india-data-scraping-regulation/), [S.S. Rana on data scraping](https://ssrana.in/articles/data-scraping-issues-india/), [ThePrint on Rajya Sabha geoblocking](https://theprint.in/india/rajya-sabha-site-blocked-outside-india-for-security-reasons-lok-sabha-site-still-accessible/510649)
- Third-party providers (not official): [Surepass](https://surepass.io/ecourt-cnr-search-api/), [eCourtsIndia](https://ecourtsindia.com/api), [Vakeel360](https://vakeel360.com/api)
