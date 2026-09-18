# Project Proposal: Amani Line
### Trusted, Verified Local Information for Community Stability

**Track:** Stability & Social Cohesion
**Theme:** Civic information people can trust and act on
**Stage:** Invention sprint — proof of concept

---

## 1. The Problem

In many Kenyan neighborhoods and peri-urban areas (e.g., Mlolongo, Machakos County, and similar fast-growing settlements), residents face a recurring pattern of friction that erodes trust between neighbors, local authorities, and each other:

- **Rumor outruns fact.** A land boundary dispute, a water-rationing schedule, or a security incident spreads first through WhatsApp groups and word of mouth — often distorted — long before any official source confirms or corrects it.
- **Disputes escalate because there's no trusted, low-friction channel to resolve them early.** Boundary disagreements, landlord–tenant conflicts, and noise or resource disputes often go straight to confrontation or are ignored until they boil over, because the local chief's office, chief's baraza, or elder council is hard to reach in real time.
- **Crisis coordination is fragmented.** During floods, fuel shortages, insecurity alerts, or local unrest, residents don't know which source to believe — county government social media, a neighbor's voice note, or a radio call-in show — and duplicate or contradictory information causes panic or missed help.
- **Access is unequal.** Many residents rely on basic feature phones, have inconsistent data bundles, and are more comfortable in Kiswahili or a local language than in English — so web-first civic tools quietly exclude them.

The underlying gap isn't a lack of information. It's a lack of a **trusted, verifiable, low-bandwidth, local-language channel** that turns raw claims into something people can act on.

---

## 2. Who This Is For

| User | Need |
|---|---|
| **Residents (primary)** — especially those on feature phones or limited data | Quickly check if a rumor is true, report a local issue, or get a dispute heard, without needing a smartphone or fast internet |
| **Local leaders** — chiefs, assistant chiefs, village elders, estate/landlord associations | A structured way to receive, triage, and publicly resolve disputes and confirm/deny circulating claims, without being flooded on personal WhatsApp |
| **Community verifiers** — trusted local figures (health workers, religious leaders, teachers, NGO field staff) | A lightweight way to confirm or flag information they have first-hand knowledge of |
| **County/local government & NGOs (secondary)** | A single, structured feed of verified local issues and sentiment, instead of scattered social media noise |

---

## 3. The Solution

**Amani Line** ("amani" = peace, Kiswahili) is a multilingual, low-bandwidth civic trust layer built on three simple actions: **Report, Verify, Resolve.**

### How it works

1. **Report** — A resident sends a short report via **SMS, USSD (*XXX#), or WhatsApp** (whichever they already use): a rumor to check, a dispute to flag, or an incident to report. No app download, no login required beyond a phone number.
   - *Example:* "Kuna maji hayajaingia Estate B wiki hii, ni kweli?" (Is it true there's no water in Estate B this week?)

2. **Verify** — The claim is:
   - Matched against a small, structured database of **confirmed official sources** (county notices, water company schedules, police blotter summaries) where available.
   - Routed to a **local verifier network** (2–3 trusted community figures per area) who can confirm/deny/add context within a set time window.
   - Given a visible **trust label**: ✅ Confirmed · ⚠️ Unconfirmed · ❌ False · 🕓 Pending — never a bare "true/false," so people can see *how* something was verified, not just the verdict.

3. **Resolve** — For disputes (not just rumors), Amani Line offers a **lightweight structured mediation flow**:
   - Both parties (or one party + a leader) register the dispute in a few short prompts (what happened, who's involved, what outcome is wanted).
   - The system suggests the right local resolution path (elder baraza, chief's office, landlord association, small-claims-style community panel) and schedules it.
   - A simple written record is generated so there's a shared reference point — reducing "he said, she said" re-litigation.

A **public, read-only digest** (SMS broadcast, USSD menu, or simple web page) shows verified local updates for anyone to check without submitting anything — this is the "everyday trust" layer, separate from the dispute-resolution flow.

---

## 4. Why This Design (Real-World Conditions)

| Consideration | How Amani Line addresses it |
|---|---|
| **Trust & verification** | Every item carries a visible trust label and a named verification path (official source vs. community verifier vs. unconfirmed). Nothing is presented as fact without a source. |
| **Low bandwidth** | Core interaction is SMS/USSD, which works on any phone and costs near-zero data. WhatsApp is an optional richer channel for those who have it, not a requirement. |
| **Accessibility** | No literacy-heavy interface; USSD menus use short numbered options; voice-note support (via WhatsApp) is a planned extension for low-literacy users. |
| **Privacy** | Reports are pseudonymous by default (phone number hashed, not displayed); dispute records are visible only to the parties involved and the assigned local resolver; no report is shared onward without consent. |
| **Multilingual access** | Kiswahili and English at launch, with menu structure designed to add local languages (e.g., Kikamba, given the Machakos context) without redesigning the flow. |
| **Local relevance** | Verifier networks and resolution paths are configured per-ward/estate, not centralized — the system adapts to how each community already resolves things (baraza, association, chief) instead of replacing it. |
| **Clear next step for users** | Every interaction ends with an explicit next action: a trust label, a scheduled mediation slot, or a "still pending, check back at X" — never a dead end. |

---

## 5. Proof-of-Concept Scope for This Sprint

Given sprint constraints, the demo focuses on the **Report → Verify** loop plus a **basic dispute-intake flow**, simulating USSD/SMS behavior through a web interface:

- A simple front end (Next.js) simulating the USSD/SMS menu experience in English and Kiswahili.
- A backend (Node.js + Supabase/PostgreSQL) storing reports, verifier responses, and trust status.
- A minimal "verifier dashboard" where a demo verifier can confirm/deny a claim.
- A rule-based (not AI-dependent) trust-labeling flow, with an optional AI-assisted step (e.g., AWS-based summarization) to flag duplicate/similar reports for the verifier — kept as an assistive layer, not a decision-maker, so trust stays human-anchored.
- A read-only public digest view showing verified items.

**Out of scope for the sprint (but part of the roadmap):** live SMS/USSD gateway integration (e.g., Africa's Talking), voice-note intake, full mediation scheduling, and county-level integration.

---

## 6. Why It's Worth Developing Further

- **Addresses root cause, not symptoms:** rather than another information broadcast tool, it builds the missing *verification and resolution* layer that turns information into something actionable.
- **Fits existing behavior:** people already use SMS, USSD, and WhatsApp for exactly this kind of local coordination — Amani Line structures what's already happening instead of asking people to change habits.
- **Extensible:** the same Report–Verify–Resolve pattern generalizes to other stability use cases — market price checks, security alerts, service-delivery complaints — without a redesign.
- **Low cost to pilot:** a single ward or estate association could trial the SMS/USSD flow with a handful of verifiers before any government integration is needed.

---

## 7. Next Steps

1. Build the sprint demo (Report → Verify loop + dispute intake simulation).
2. Pilot with one ward/estate: identify 2–3 verifiers, run the SMS/USSD flow manually for two weeks to validate the trust-labeling logic.
3. Integrate a real SMS/USSD gateway (e.g., Africa's Talking) for a live pilot.
4. Explore partnership with a local administration office or community-based organization for the mediation-scheduling flow.
5. Evaluate voice-note intake for low-literacy accessibility.
