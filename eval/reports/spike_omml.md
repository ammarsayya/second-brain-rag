# SPIKE-OMML: OMML -> LaTeX Conversion Evidence (T-P3-07)

Tool: pandoc (the primary candidate docs/36 proposes for this spike).

- OMML-bearing DOCX/PPTX files found: 44
- files pandoc failed to convert: 0
- total equations extracted: 2608
- syntactically valid (balanced braces, non-empty, no pandoc error marker): 2606 (99.9% of extracted)
- files with a PDF twin candidate (T-P2-09) for future PDF<->DOCX alignment: 15

**This is syntactic well-formedness, not correctness.** The task's acceptance criterion needs a human to compare each equation against its source - that is the owner's review of the 50-sample table below, not something measured here.

## Key finding: pandoc handles DOCX well, but extracts zero equations from every PPTX

Of the 44 OMML-bearing files found, every DOCX converted with a very high (99.9%) syntax-valid equation
count matching this corpus's already-known official figures (docs/24 §64: thesis DOCX = 422 equations;
measured here across its several saved copies: 422, 425, 427, 431). But **every one of the 14 PPTX files
that genuinely contain a native `<m:oMath>` tag (confirmed directly in their raw XML) converted to exactly
zero extracted equations** — not a conversion error (pandoc exits 0 and produces normal LaTeX prose), the
equations are simply absent from its output. This is consistent across all 14 files, not a one-off fluke, so
it reads as a real limitation of pandoc's PPTX reader rather than anything corpus-specific.

**Consequence for ADR-009's conversion-path decision**: pandoc alone is not sufficient for PowerPoint-native
math; one of docs/36's own listed alternatives (docx2python + a custom OMML XSLT, or LibreOffice's own
conversion path) would need to cover the PPTX case specifically, or PPTX equations route through a different
tier entirely (e.g. treated as a scanned/rendered slide and sent through the eventual math *recognizer*,
SPIKE-MATH, rather than converted from source). This is an owner-facing decision, not one this script makes.

## Per-file results

| relpath | equations | syntactically valid | has PDF twin | error |
|---|---|---|---|---|
| BachelorArbeit\BAP\Bachelor.pptx | 0 | 0 | True |  |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit.docx | 425 | 425 | True |  |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit1.docx | 422 | 422 | True |  |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\BachelorarbeitCopy.docx | 431 | 431 | True |  |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Praesentation.pptx | 0 | 0 | False |  |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Stueckelmaier\Praesentation.pptx | 0 | 0 | False |  |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelor.pptx | 0 | 0 | True |  |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelorarbeit.docx | 427 | 427 | True |  |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Min.docx | 2 | 2 | False |  |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\MyApplikation.docx | 9 | 9 | False |  |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Praesentation.pptx | 0 | 0 | False |  |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Tabelln.docx | 5 | 5 | False |  |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\identifizierung.docx | 7 | 7 | False |  |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\tabe.docx | 5 | 5 | False |  |
| BachelorArbeit\Praxisphase\Bericht\Fourier.docx | 8 | 8 | False |  |
| BachelorArbeit\Praxisphase\Bericht\Gleichungen.docx | 64 | 63 | False |  |
| BachelorArbeit\Praxisphase\Bericht\Kinematik.docx | 100 | 100 | False |  |
| BachelorArbeit\Praxisphase\Bericht\Praxisphase.docx | 395 | 395 | False |  |
| BachelorArbeit\Praxisphase\Bericht\PraxisphaseAmmarSayyadi.pptx | 0 | 0 | False |  |
| BachelorArbeit\Praxisphase\Bericht\PraxisphaseMBI.pptx | 0 | 0 | False |  |
| BachelorArbeit\Projekt\Semester ProjektMBI.pptx | 0 | 0 | False |  |
| BachelorArbeit\Praxisphase\Bericht\Symbolverzeichnis.docx | 50 | 50 | False |  |
| BachelorArbeit\Praxisphase\Bericht\Theorie zur Schätzung.docx | 22 | 22 | False |  |
| BachelorArbeit\Praxisphase\FR.pptx | 0 | 0 | False |  |
| BachelorArbeit\Projekt\AmmarSayyadiMBIProjekt.docx | 7 | 7 | False |  |
| BachelorArbeit\Projekt\Copy\Dokumentation.docx | 1 | 1 | True |  |
| BachelorArbeit\Projekt\Dokummentation.docx | 1 | 1 | True |  |
| BachelorArbeit\Projekt\Präsentation.pptx | 0 | 0 | False |  |
| BachelorArbeit\Projekt\SemesterProjectAmmarSayyadi.pptx.docx | 7 | 7 | False |  |
| BachelorArbeit\Projekt\SemesterProjekt.docx | 7 | 7 | False |  |
| BachelorArbeit\Projekt\arbeit\AmmarSayyadiMBIProjekt.docx | 9 | 9 | False |  |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 0 | 0 | True |  |
| Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung6_lösung.pptx | 0 | 0 | True |  |
| Information\Vorlesung\WISs\Bestimmung der Dichte von Flüssigkeiten mit der Steighöhen.docx | 47 | 47 | False |  |
| Information\Vorlesung\WISs\Gesetz von Boyle Mariotte für wi.docx | 20 | 20 | False |  |
| Mechanical\messundsteuerungstechnik\MSR2\MSR2\Auto\BasisProg.docx | 1 | 1 | False |  |
| Mechanical\messundsteuerungstechnik\MSR2\MSR2\Lab\MSR2\Auf1\MSR.docx | 14 | 14 | True |  |
| Mechanical\messundsteuerungstechnik\MSR2\MSR2\Lab\MT1\MT1_Bericht.docx | 24 | 23 | True |  |
| Mechanical\messundsteuerungstechnik\MSR2\MSR2\Lab\MT1\MT5 Gruppe 1.docx | 23 | 23 | False |  |
| Mechanical\messundsteuerungstechnik\MSR2\MSR2\Lab\MT1_Bericht.docx | 26 | 26 | True |  |
| Mechanical\messundsteuerungstechnik\Mess\Messtechnik.docx | 26 | 26 | False |  |
| Mechanical\messundsteuerungstechnik\MSR2\MSR2\Lab\MT2\Bericht.docx | 14 | 14 | True |  |
| Mechanical\messundsteuerungstechnik\MSR2\MSR2\Lab\nFin\FEM1-Bericht.docx | 9 | 9 | True |  |
| Mechanical\werkstoffkunde\WK\WERK\Stiller\ergänzende Folien_Vorlesung GWK_WiSe 2021.pptx | 0 | 0 | False |  |

## 50-equation sample for owner manual review

| relpath | LaTeX | syntactically valid |
|---|---|---|
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit.docx | `\mathcal{E}_{ges} = \mathcal{E}_{dy} - \mathcal{E}_{st}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit.docx | `\mathbf{J}_{T_{i}}^{} = \frac{\partial\mathbf{v}_{i}}{\partial\dot{\mathbf{q}}}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit.docx | `_{}^{0}\mathbf{T}_{B}^{}` | True |
| BachelorArbeit\Projekt\arbeit\AmmarSayyadiMBIProjekt.docx | `= 0.1Hz` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\BachelorarbeitCopy.docx | `_{}^{(0)}\mathbf{R}_{(e)}^{} =_{}^{(0)}\mathbf{R}_{(1)}^{}._{}^{(0)}\mathbf{R}_{(2)}^{}.\ \ldots.\ _{}^{(n - 1)}\mathbf{R}_{(e)}^{}` | True |
| BachelorArbeit\Praxisphase\Bericht\Praxisphase.docx | `\mathbf{M}\left( \overrightarrow{\mathbf{q}}(t) \right)` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit1.docx | `\mathbf{J}_{\mathbf{yy}}` | True |
| Mechanical\messundsteuerungstechnik\Mess\Messtechnik.docx | `u_{Mu1} = \ \frac{0,05*10^{- 2}*15,99\ bar}{\sqrt{3}} = 4,616*10^{- 3}\ bar` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit.docx | `i` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit1.docx | `_{}^{0}\mathbf{T}_{B}^{}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelorarbeit.docx | `q_{2} + \frac{\pi}{2}` | True |
| BachelorArbeit\Praxisphase\Bericht\Praxisphase.docx | `{\dot{\overrightarrow{\mathbf{x}}}}_{E} = \frac{\partial f(\overrightarrow{\mathbf{q}})}{\partial t} = J_{A}(\overrightarrow{\mathbf{q}})\dot{\overrightarrow{\mathbf{q}}}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\BachelorarbeitCopy.docx | `\ddot{\mathbf{q}}(t)` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\BachelorarbeitCopy.docx | `{(KS)}_{B}\` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit1.docx | `\ \mathbf{q =}\left\lbrack q_{1},\ q_{2},\ldots,\ q_{n}\  \right\rbrack^{T}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelorarbeit.docx | `\mathbf{x}_{\mathbf{E,max}}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit.docx | `k` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\BachelorarbeitCopy.docx | `s_{z5} + s_{z6}` | True |
| BachelorArbeit\Praxisphase\Bericht\Praxisphase.docx | `{Rb}_{31}` | True |
| Mechanical\messundsteuerungstechnik\MSR2\MSR2\Lab\MT1\MT1_Bericht.docx | `u_{Hyst}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit1.docx | `J_{xy3}` | True |
| BachelorArbeit\Projekt\AmmarSayyadiMBIProjekt.docx | `{{(X}^{T} \times X)}^{- 1}` | True |
| Information\Vorlesung\WISs\Gesetz von Boyle Mariotte für wi.docx | `h_{k}a` | True |
| BachelorArbeit\Praxisphase\Bericht\Kinematik.docx | `{}_{(A)}x_{(B)} = \left\lbrack \ \binom{{}_{(A)}r_{(B)}}{1} \right\rbrack` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit1.docx | `q_{5} + l_{4}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit1.docx | `J_{xx3} - J_{yy3 + J_{yy4}}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit1.docx | `ɸ` | True |
| BachelorArbeit\Praxisphase\Bericht\Praxisphase.docx | `\left\| \mathbf{A}^{T}\mathbf{A} \right\|` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelorarbeit.docx | `0` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelorarbeit.docx | `i - 1\` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\BachelorarbeitCopy.docx | `\ \ \ \  = \left\lbrack \mathbf{A}_{s,1},\ldots,\mathbf{A}_{s,N} \right\rbrack\ \ \left\lbrack {\mathbf{p}_{s,1}}^{T},\ldots,{\mathbf{p}_{s,N}}^{T} \right\rbrack^{T}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\BachelorarbeitCopy.docx | `\ _{}^{0}\mathbf{T}_{B}^{}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelorarbeit.docx | `\mathbf{x} = f\left( \mathbf{q} \right)` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit.docx | `_{0}^{}\mathbf{\omega}` | True |
| BachelorArbeit\Praxisphase\Bericht\Fourier.docx | `f(x) = \frac{a_{0}}{2} + \sum_{n = 1}^{\infty}\left( a_{n}\cos{(nx)} + b_{n}\sin{(nx)} \right)` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelorarbeit.docx | `\mathbf{y} = {\lbrack y_{1}\ y_{2}\ y_{3}\rbrack}^{T}` | True |
| BachelorArbeit\Praxisphase\Bericht\Praxisphase.docx | `{Rb}_{22}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\BachelorarbeitCopy.docx | `\mathbf{\tau} = \ \sum_{i = 1}^{N}\underset{A_{i}(\mathbf{q,}\dot{\mathbf{q}}\mathbf{,}\ddot{\mathbf{q}}\mathbf{)}}{\overset{\lbrack\mathbf{J}_{T_{i}}^{T}\mathbf{J}_{R_{i}}^{T}\rbrack\begin{bmatrix}
\mathbf{0} & {\dot{\widetilde{\mathbf{\omega}}}}_{i} + {\widetilde{\mathbf{\omega}}}_{i}{\widetilde{\mathbf{\omega}}}_{i} & \mathbf{a}_{i} \\
{\dot{\mathbf{\omega}}}_{i}^{*} + {\widetilde{\mathbf{\omega}}}_{i}{\mathbf{\omega}_{i}}^{*} & {\widetilde{\mathbf{a}}}_{i} & \mathbf{0}
\end{bmatrix}}{︸}}\underset{p_{i}}{\overset{\begin{bmatrix}
{\mathbf{I}_{i}}^{{^\circ}} \\
\mathbf{s}_{i} \\
m_{i}
\end{bmatrix}}{︸}}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit.docx | `_{(0)}^{}\mathbf{r}_{P}^{} =_{}^{(0)}\mathbf{R}_{(1)}^{}\ ._{}^{(1)}\mathbf{R}_{(2)}^{}.\ _{(2)}^{}\mathbf{r}_{P}^{} =_{}^{(0)}\mathbf{R}_{(2)}^{}.\ _{(2)}^{}\mathbf{r}_{P}^{}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit.docx | `J_{yz2}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit1.docx | `\mathbf{q}_{\mathbf{4}}` | True |
| BachelorArbeit\Praxisphase\Bericht\Praxisphase.docx | `\mathbf{q}_{\mathbf{4}}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelorarbeit.docx | `\left( m_{2} + m_{3} + m_{4} \right)l_{1}^{2} + J_{zz1}` | True |
| BachelorArbeit\Praxisphase\Bericht\Praxisphase.docx | `{(KS)}_{B}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit1.docx | `FR - Trajektorie` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelorarbeit.docx | `m\ Masse\ in\ \lbrack kg\rbrack` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit1.docx | `t` | True |
| BachelorArbeit\Praxisphase\Bericht\Praxisphase.docx | `J_{xy6}` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit1.docx | `k` | True |
| BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelorarbeit.docx | `q,\dot{q},\ddot{q}` | True |
