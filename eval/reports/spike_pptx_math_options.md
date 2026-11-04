# PPTX math extraction options: synthetic benchmark (T-P3-07, ADR-009 evidence)

Host: Linux x86_64, Python 3.12.3. Benchmark: 14 synthetic equations (1 in notes), each with a unique fallback marker. **No corpus content. Not a decision**: the ADR-009 PPTX path is the owner's choice.

## Results

| Option | Equations recovered as math | Structure kept | Notes | Time | Memory |
|---|---|---|---|---|---|
| A native OMML->LaTeX | 14/14 correct (14 found) | yes (LaTeX) | yes | 16.4 ms | 0.1 MB Python peak |
| B LibreOffice PPTX->ODP | 0/14 MathML objects; 14/14 fallback markers | no | n/a | 2.4 s (cold start) | <= 216 MB RSS |
| B LibreOffice PPTX->PDF | text only; 13/14 fallback markers | no | n/a | 1.5 s | <= 216 MB RSS |
| P pandoc | `pandoc 3.1.3` has no PPTX reader | no | no | | |
| C render + formula recognizer | not runnable: no local recognizer (SPIKE-MATH, T-P3-06) | | | | |

## Option A per equation

| case | part | LaTeX | matches reference |
|---|---|---|---|
| fraction | slide1.xml | `x=\frac{a}{b}` | True |
| subscript | slide2.xml | `{K}_{p}` | True |
| superscript | slide3.xml | `{x}^{2}` | True |
| sum_with_limits | slide4.xml | `\sum_{i=1}^{n}{{a}_{i}}` | True |
| integral | slide5.xml | `\int_{0}^{T}{u\left( t \right)dt}` | True |
| radical | slide6.xml | `\sqrt{2}` | True |
| pseudo_inverse | slide7.xml | `p={\left( {A}^{T}A \right)}^{-1}{A}^{T}{F}_{ges}` | True |
| matrix | slide8.xml | `\left( \begin{matrix} 1 & 0 \\ 0 & 1 \end{matrix} \right)` | True |
| function_in_run | slide9.xml | `f=\min \left( x \right)` | True |
| log_det_in_run | slide10.xml | `-\ln \left( \det \left( A \right) \right)` | True |
| prose_in_math | slide11.xml | `\{P\}\rightarrow\{\text{Term nach Zuweisungen}\}` | True |
| accent_dot | slide12.xml | `\dot{q}` | True |
| greek_relation | slide13.xml | `{\tau}_{i}\leq\omega` | True |
| notes_equation |  | `E=m{c}^{2}` | True |

LibreOffice: `LibreOffice 24.2.7.2 420(Build:2)`.

## How to read this

- A fallback marker in an output means that option read the picture/text fallback, not the equation. On real PowerPoint files the fallback is normally an image, so that path yields **no math**.
- Memory for B is the peak RSS of all child processes so far (an upper bound); A is traced Python allocation.
- Synthetic coverage is not corpus fidelity: the owner's review of the 50 real equations in `eval/reports/spike_omml_native.md` (re-run `tools/spike_omml.py --native-latex` on the Mac after converter changes) is the acceptance evidence.
