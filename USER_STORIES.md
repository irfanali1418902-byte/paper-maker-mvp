# User Stories — AII Smart Paper Maker

User stories for Pakistani school teachers (and the school staff around
them) using the app. Each story follows the form:

> As a **[role]**, I want to **[action]**, so that **[benefit]**.

The app is built for KPK-board schools (e.g. in Swat), so the stories
assume bilingual (Urdu + English) papers, a 33% pass threshold, and
competition-style ranking.

## Roles

- **Teacher** — the primary user. Creates question banks, generates papers,
  uploads results, reads analytics, exports papers.
- **School Admin** — sets up the school (letterhead, logo, settings) and
  oversees paper/result activity across teachers.
- **Student** — an *indirect* beneficiary. Never logs in, but the quality,
  fairness, and difficulty balance of every paper affects them.

---

## Syllabus upload

1. As a **Teacher**, I want to upload my subject's syllabus PDF, so that
   the app can auto-extract topics and I don't have to type them by hand.

2. As a **Teacher**, I want to upload a ZIP of multiple syllabus files at
   once, so that I can set up a whole class's subjects in one step at the
   start of the term.

3. As a **Teacher**, I want to see the distinct (subject, grade) pairs the
   system already knows, so that I can confirm my syllabus imported
   correctly before generating any paper.

4. As a **Teacher**, I want to browse the extracted topics for a given
   subject and grade, so that I can pick exactly which topics a paper
   should cover.

5. As a **School Admin**, I want syllabus data to be shared across teachers
   of the same subject, so that two teachers of Grade 9 Physics don't have
   to import the same syllabus twice.

## Paper generation

6. As a **Teacher**, I want to generate AI-written, Bloom-tagged questions
   for a topic, so that I get fresh questions without writing each one
   myself.

7. As a **Teacher**, I want questions produced in both Urdu and English, so
   that my paper matches how I actually teach and test in class.

8. As a **Teacher**, I want to choose the Bloom distribution and difficulty
   of a generated paper, so that the paper matches my class's level and the
   board's expectations.

9. As a **Teacher**, I want the app to assemble a *balanced* paper from the
   question bank, so that my paper isn't accidentally all easy recall
   questions or all hard analysis questions.

10. As a **Teacher**, I want to see an expected-difficulty and balance
    summary before I finalize a paper, so that I know how hard the paper
    will be for my students before they ever sit it.

11. As a **Teacher**, I want to replace a single question in a generated
    paper, so that I can swap out one question I don't like without
    regenerating the whole paper.

12. As a **Teacher**, I want to generate an *adaptive* paper based on my
    class's weak Bloom levels, so that the next test targets exactly what
    my students struggled with.

13. As a **Teacher**, I want to keep building a reusable question bank, so
    that each paper I make gets faster to assemble as the bank grows.

14. As a **Student** (indirectly), I want papers to be difficulty-balanced
    and fair, so that my grade reflects my understanding rather than the
    luck of an unusually hard or easy paper.

## Result upload

15. As a **Teacher**, I want to download an empty results template for a
    paper, so that I can fill in my students' marks in the exact format the
    app expects.

16. As a **Teacher**, I want to upload the filled results CSV and have it
    validated, so that I catch typos or missing marks before they corrupt
    my analytics.

17. As a **Teacher**, I want to upload results multiple times for the same
    paper, so that I can correct a mistake by re-uploading rather than
    starting over.

18. As a **School Admin**, I want each result upload to be recorded as a
    distinct upload, so that we keep an audit trail of when marks were
    entered or corrected.

## Analytics viewing

19. As a **Teacher**, I want a dashboard summarizing my class's
    performance, so that I can see pass/fail counts and averages at a
    glance without a spreadsheet.

20. As a **Teacher**, I want students ranked competition-style (ties share
    a rank: 1, 1, 3), so that the ranking matches how our school reports
    positions.

21. As a **Teacher**, I want per-question difficulty (P-value) and
    discrimination (D-index), so that I know which questions were too easy,
    too hard, or failed to separate strong from weak students.

22. As a **Teacher**, I want bad questions flagged automatically
    (too easy/hard, negative discrimination, likely mis-keyed), so that I
    fix or drop them before reusing them.

23. As a **Teacher**, I want to be warned that discrimination stats are
    unreliable for classes under 10 students, so that I don't over-trust a
    D-index computed from too few results.

24. As a **Teacher**, I want to view the dashboard for a specific past
    upload, so that I can compare an earlier attempt against the latest
    results.

25. As a **School Admin**, I want quick top-level stats across papers, so
    that I can monitor activity in the school without opening each paper.

## Export (Word / PDF)

26. As a **Teacher**, I want to export a paper as a Word (.docx) file, so
    that I can make final manual edits before printing.

27. As a **Teacher**, I want the Urdu text exported in the Jameel Noori
    Nastaleeq font, so that the printed paper is readable and looks
    professional to students and parents.

28. As a **Teacher**, I want to export a paper directly as PDF, so that I
    can print or share a fixed-layout copy that won't reflow on another
    computer.

29. As a **School Admin**, I want exported papers to carry the school
    letterhead and logo, so that every paper looks official regardless of
    which teacher created it.

30. As a **School Admin**, I want to configure the school's letterhead and
    logo once, so that all teachers' exports use consistent branding
    without each teacher setting it up.
