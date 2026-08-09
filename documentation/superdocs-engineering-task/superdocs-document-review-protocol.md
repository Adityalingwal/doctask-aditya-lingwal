# SuperDocs Task Document Review Protocol

## Purpose
Is document ka kaam task ke content ko store karna nahi hai. Iska kaam yeh ensure karna hai ki task document ko samajhte, notes banate aur implementation plan karte waqt koi rule, requirement, ya important detail miss na ho.

## Two-document system

| Document | Purpose | Kya store hoga | Kya store nahi hoga |
|---|---|---|---|
| `superdocs-round2-working-notes.md` | Build aur submission ke liye source of truth | Requirements, decisions, risks, evidence, submission checklist, open questions | Repeated explanations, chat history, temporary interpretation |
| `superdocs-document-review-protocol.md` | Review process ka quality-control layer | Reading rules, note-admission rule, coverage tracker, unresolved ambiguities, review checkpoints | Task requirements ki copied/duplicate list |

## Reading rules
- Document ko chhote chunks mein padhenge: ek short paragraph ya ek closely related block at a time.
- Har chunk ke baad pehle plain Hinglish meaning samjhenge, phir author ka practical intent.
- Uske baad decide hoga: `Add`, `Update existing`, `No note`, ya `Question`.
- Ek time par sirf current chunk cover hoga; future sections par assumptions nahi banengi.
- Requirement aur hamari interpretation ko clearly separate rakhenge.
- Jahan exact wording important ho, requirement ka short faithful wording/reference rakhenge; unnecessary copying nahi.

## Uncertain-note decision rule
- Kisi point ko jaldi mein `No note` declare nahi karna hai.
- Pehle Working Notes aur Review Protocol dono ke against evaluate karna hai: author ne isse explicitly evaluate/weight/require kiya hai kya; kya yeh build, submission, founder discussion, risk, ya scoring strategy change karta hai; aur kya iska canonical home already exist karta hai.
- Agar point actionable ya scoring-relevant ho aur existing notes mein explicitly captured na ho, to add/update karna hai.
- Agar add vs no-note genuinely unclear ho, to final decision se pehle user se short question poochhna hai: proposed note location aur one-line reason ke saath.
- `No note` decision ke saath one-line reason dena mandatory hai: already covered exactly where, ya why it has no future execution/submission value.

## Note-admission rule
Kisi point ko Working Notes mein tabhi add karna hai jab woh kam se kam ek purpose serve kare:
- Build scope, architecture, UX, safety, testing, ya implementation decision change karta ho.
- Submission, deadline, evidence, repository, video, write-up, ya form requirement ho.
- Evaluation, founder discussion, demo, ya live modification readiness mein help kare.
- Material risk, constraint, dependency, ambiguity, bug-report opportunity, ya verification step ho.

Agar point sirf explanation, background, repeated idea, ya current paragraph ko samajhne ki temporary help hai, to use chat mein hi rehne dena hai.

## Duplicate-control rule
- Har fact ka Working Notes mein exactly one canonical home hoga.
- Nayi information existing fact ko expand karti hai to naya section nahi banana; relevant existing section ko update karna hai.
- Same point ko alag headings mein repeat nahi karna.
- Duplicate lagne par pehle search/scan karna: kya iski canonical entry already hai?
- Agar haan, outcome `Update existing` ya `No note` hoga.
- Cross-reference tabhi use karna jab genuinely navigation help hoti ho; otherwise avoid karna hai.

## Chunk review template
Har document chunk ke liye internal output:

```md
### Chunk: [page + heading/first words]
- Plain meaning:
- Author ka practical intent:
- Classification: Add / Update existing / No note / Question
- Working Notes location: [heading] / —
- Why: [one line]
- Open question or verification: [if any]
```

## Coverage tracker → Retired
Full PDF → Working Notes audit completed manually (session 2026-08-08). Every major requirement captured in `superdocs-round2-working-notes.md` → Coverage index. Tracker table retired — no busywork needed.

## Requirement categories
Jab relevant content mile, requirements ko in categories mein route karna hai:
- Product/build behaviour
- Technical/architecture constraints
- Data, privacy, security, or safety
- Testing and evaluation
- Demo/video/evidence
- Repository, README, documentation
- Submission and deadline
- Communication and bug reporting
- Optional/extra-credit work
- Founder discussion/interview readiness

## Ambiguity handling
- Ambiguous point ko assumption bana kar notes mein final fact ki tarah nahi likhna.
- `Open questions` entry banao with: exact ambiguity, why it matters, likely interpretations, and whether email clarification is needed.
- Agar question author ko bhejna ho, pehle document dobara search/check karna hai so that already-answered question na bheje.
- Genuine blocker ya reproducible product bug ko timely, concise evidence ke saath report karna hai.

## Periodic quality checks
### After each completed PDF section
- Kya har actionable requirement Working Notes mein canonical place par hai?
- Kya same information repeat to nahi hui?
- Kya requirement aur interpretation separate hain?
- Kya unresolved question recorded hai?

### Before implementation starts
- Extracted requirements ko build plan se map karo.
- Har must-have ke liye acceptance check define karo.
- Unknowns, dependencies, and risks identify karo.

### Before submission
- PDF requirements vs Working Notes vs actual repository/deliverables ka three-way review karo.
- Har claim ke liye evidence verify karo: demo, test, screenshot, logs, link, or document reference.
- README commands fresh environment mein verify karo.
- Known limitations honestly disclosed hain ya nahi check karo.

## External AI review prompt
Kisi second AI reviewer ko review ke liye yeh artifacts dene hain:
- Original task PDF/text
- Current `superdocs-round2-working-notes.md`
- Current repository tree and README
- Submission artifacts, if available

Ask it to return only:
1. Missing explicit requirements
2. Requirements captured but not implemented/evidenced
3. Duplicate or contradictory notes
4. Unsupported assumptions
5. Submission risks ranked by severity
6. Exact suggested corrections with source location

Reviewer ke suggestions ko blindly accept nahi karna; original PDF remains the source of truth.
