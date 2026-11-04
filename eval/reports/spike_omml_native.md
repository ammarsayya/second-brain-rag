# SPIKE-OMML follow-up: native OMML -> LaTeX prototype (T-P3-07)

`sbr.eval.extract.omml_latex` converts OMML with the Python standard library, so DOCX and PPTX math share one path and pandoc is not needed. Every equation `count_omml_equations` counts is converted; PPTX slide positions come from `presentation.xml` (deck order), and notes are attributed to the slide they annotate.

**Evidence, not a decision.** *Valid* is syntactic plausibility (balanced braces, non-empty), not correctness. *Exact* means no OMML element fell back to plain text. Choosing the ADR-009 Office-math path and accepting any converter needs the owner's review of the sample below. Blobs the sensitivity gate rejects are not opened.

- files that could not be read from the source: 0

## DOCX

- files with native OMML: 31; equations converted: 2597 (docx_body 2597)
- syntactically valid: 2592 (99.8%); exact (no fallback): 2597 (100.0%); empty `m:oMath` placeholders (count as not valid): 5
- elements that fell back to plain text: none
- parts where converted and counted equations differ: 0; unreadable parts: 0

## PPTX

- files with native OMML: 13; equations converted: 497 (other_part 8, pptx_notes 5, pptx_slide 484)
- syntactically valid: 497 (100.0%); exact (no fallback): 497 (100.0%); empty `m:oMath` placeholders (count as not valid): 0
- elements that fell back to plain text: none
- parts where converted and counted equations differ: 0; unreadable parts: 0

## Comparison with pandoc on the T-P3-02 OMML gold candidates

Each candidate's exact OMML crop is converted and compared with the pandoc LaTeX the T-P3-02 selector paired with it **by ordinal**. A different letter/digit content means the pair is not the same equation (*mis-paired*); otherwise the two are compared after folding notation (`latex_compare_key`).

- candidates compared: 180 (crops missing: 0)
- **mis-paired** (pandoc LaTeX belongs to another equation): 42 (23.3%)
- correctly paired and equal after notation folding: 138/138 (100.0%)
- correctly paired but different: 0

Mis-paired sample ids by file: Kinematik.docx: math-029, math-030, math-031, math-066, math-067, math-068, math-069, math-070, math-071, math-072, math-116, math-149, math-152, math-153, math-154, math-155, math-156, math-157, math-158, math-286; Bestimmung der Dichte von Flüssigkeiten mit der Steighöhen.docx: math-025, math-026, math-059, math-060, math-061, math-109, math-110, math-111, math-112, math-143, math-284, math-285; Gesetz von Boyle Mariotte für wi.docx: math-005, math-099, math-100; MSR.docx: math-004, math-096; MT1_Bericht.docx: math-003, math-081, math-082; Messtechnik.docx: math-086, math-087


## PPTX review sample (50 of 497, seed 20260926)

| relpath | slide | part | # | LaTeX | exact |
|---|---|---|---|---|---|
| BachelorArbeit\BAP\Bachelor.pptx | 9 | data3.xml | 1 | `\psi={f}_{i}-{f}_{0}` | True |
| BachelorArbeit\BAP\Bachelor.pptx | 9 | drawing3.xml | 2 | `\psi={E}_{i}-{E}_{0}` | True |
| BachelorArbeit\BAP\Bachelor.pptx | 18 | slide18.xml | 5 | `{q}_{FR}` | True |
| BachelorArbeit\BAP\Bachelor.pptx | 19 | slide19.xml | 1 | `{x}_{E,min}` | True |
| BachelorArbeit\BAP\Bachelor.pptx | 19 | slide19.xml | 11 | `{S}_{2}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelor.pptx | 14 | data3.xml | 1 | `\psi={f}_{i}-{f}_{0}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelor.pptx | 23 | slide23.xml | 1 | `q` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Praesentation.pptx | 3 | slide3.xml | 2 | `{~von~A}_{i}~` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Praesentation.pptx | 3 | slide3.xml | 4 | `p={\left( {A}^{T}A \right)}^{-1}{A}^{T}~{F}_{ges}~~` | True |
| BachelorArbeit\Praxisphase\Bericht\PraxisphaseAmmarSayyadi.pptx | 7 | slide7.xml | 4 | `{i}_{4}` | True |
| BachelorArbeit\Praxisphase\Bericht\PraxisphaseAmmarSayyadi.pptx | 7 | slide7.xml | 15 | `{q}_{1}` | True |
| BachelorArbeit\Praxisphase\Bericht\PraxisphaseAmmarSayyadi.pptx | 7 | slide7.xml | 19 | `{q}_{5}` | True |
| BachelorArbeit\Praxisphase\Bericht\PraxisphaseAmmarSayyadi.pptx | 8 | slide8.xml | 2 | `\acute{f}\left( x \right)=\frac{f\left( x \right)-f\left( x-\Delta x \right)}{\Delta x}` | True |
| BachelorArbeit\Praxisphase\Bericht\PraxisphaseAmmarSayyadi.pptx | 16 | slide16.xml | 3 | `{\tau}_{i}=A\left( q,\dot{q},\ddot{q} \right){p}_{i}` | True |
| BachelorArbeit\Praxisphase\Bericht\PraxisphaseAmmarSayyadi.pptx | 18 | slide18.xml | 2 | `f=min\left( -ln\left( det\left( {A}^{T}A \right) \right) \right)` | True |
| BachelorArbeit\Praxisphase\Bericht\PraxisphaseMBI.pptx | 7 | slide7.xml | 1 | `{i}_{1}` | True |
| BachelorArbeit\Praxisphase\Bericht\PraxisphaseMBI.pptx | 7 | slide7.xml | 5 | `{q}_{1}` | True |
| BachelorArbeit\Praxisphase\Bericht\PraxisphaseMBI.pptx | 7 | slide7.xml | 7 | `{q}_{3}` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 4 | slide4.xml | 1 | `n` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 12 | slide12.xml | 1 | `i\in{\mathbb{N}}_{+}` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 14 | slide14.xml | 2 | `{b}^{'}=b+1~~~~~~{c}_{0}^{'}=~{c}_{i}` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 36 | slide36.xml | 9 | `z~:=~z~+~1;` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 37 | slide37.xml | 1 | `\{P\}~x~\geq~0` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 37 | slide37.xml | 3 | `\left\{ I \right\}y={2}^{z}\wedge~z~\leq~x~` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 37 | slide37.xml | 18 | `y={2}^{x}\wedge x\leq x\wedge x=x` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 37 | slide37.xml | 27 | `\left\{ P \right\}\rightarrow\{Term~nach~Zuweisungen\}` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 37 | slide37.xml | 28 | `\left\{ P \right\}~~~~~x\geq0` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 38 | slide38.xml | 19 | `y={2}^{x}` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 38 | slide38.xml | 23 | `y*2={2}^{z+1}\wedge z\leq x\wedge z\neq x` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 38 | slide38.xml | 26 | `y*2={2}^{z+1}\wedge z+1\leq x` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 39 | slide39.xml | 6 | `z~:=~0;` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 39 | slide39.xml | 12 | `y={2}^{z+1}\wedge z+1\leq x` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 39 | slide39.xml | 20 | `\left\{ I\wedge B \right\}\rightarrow\{Term~nach~Zuweisungen\}` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 40 | slide40.xml | 9 | `z~:=~z~+~1;` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 40 | slide40.xml | 27 | `\left\{ P \right\}\rightarrow\{Term~nach~Zuweisungen\}` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 40 | slide40.xml | 31 | `{2}^{0}` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 41 | slide41.xml | 16 | `\left\{ I\wedge\neg B \right\}\rightarrow\{Q\}` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 41 | slide41.xml | 21 | `\left\{ I\wedge B \right\}~~~~y={2}^{z}\wedge z\leq x\wedge x\neq z` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 41 | slide41.xml | 31 | `{2}^{0}` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 42 | slide42.xml | 4 | `y={2}^{0}\wedge0\leq x` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 42 | slide42.xml | 11 | `\{Q\}~y={2}^{x}` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 42 | slide42.xml | 25 | `\leq` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 43 | slide43.xml | 3 | `\left\{ I \right\}y={2}^{z}\wedge~z~\leq~x~` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 43 | slide43.xml | 17 | `\left\{ I\wedge\neg B \right\}~y={2}^{z}\wedge z\leq x\wedge x=z` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 44 | slide44.xml | 2 | `y~:=~1;` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 44 | slide44.xml | 3 | `\left\{ I \right\}y={2}^{z}\wedge~z~\leq~x~` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 44 | slide44.xml | 6 | `z~:=~0;` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 44 | slide44.xml | 8 | `\left\{ I \right\}y={2}^{z}\wedge~z~\leq~x~` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 44 | slide44.xml | 18 | `y={2}^{x}\wedge x\leq x\wedge x=x` | True |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung6_lösung.pptx | 3 | slide3.xml | 3 | `~y=\sum_{i=1}^{3x}{(4\cdot{i}^{2})}` | True |
