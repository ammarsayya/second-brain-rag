# SPIKE-OMML follow-up: native OMML inventory without pandoc (T-P3-07)

Counts outermost native OMML equations (`m:oMath`, by namespace URI) in every canonical DOCX/PPTX, per XML part. `mc:Fallback` pictures are not counted, so each PPTX equation counts once. These are structural counts, not conversion results. They size what a PPTX conversion path would have to cover, since the pandoc run in `spike_omml.md` extracted zero equations from PPTX. Choosing that path (another converter, or routing PPTX math to the SPIKE-MATH recognizer) is an ADR-009 decision, not made here.

- files that could not be read from the source: 0

## DOCX

- canonical files scanned: 158 (not a zip: 3, unparseable XML parts: 0)
- files with native OMML: 31
- native OMML equations: 2597 - docx_body=2597 (934 display)
- files with native OMML and a PDF twin candidate (T-P2-09): 11

## PPTX

- canonical files scanned: 35 (not a zip: 0, unparseable XML parts: 0)
- files with native OMML: 13
- native OMML equations: 497 - other_part=8 (8 display), pptx_notes=5 (0 display), pptx_slide=484 (234 display)
- files with native OMML and a PDF twin candidate (T-P2-09): 4
- slides carrying native OMML: 53

## Per-file counts (files with native OMML)

| format | relpath | equations | display | slides with OMML / slides | has PDF twin |
|---|---|---|---|---|---|
| docx | BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\BachelorarbeitCopy.docx | 432 | 139 | - | True |
| docx | BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelorarbeit.docx | 424 | 131 | - | True |
| docx | BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit.docx | 422 | 152 | - | True |
| docx | BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit1.docx | 419 | 135 | - | True |
| docx | BachelorArbeit\Praxisphase\Bericht\Praxisphase.docx | 388 | 110 | - | False |
| docx | BachelorArbeit\Praxisphase\Bericht\Kinematik.docx | 100 | 43 | - | False |
| docx | BachelorArbeit\Praxisphase\Bericht\Gleichungen.docx | 67 | 60 | - | False |
| docx | BachelorArbeit\Praxisphase\Bericht\Symbolverzeichnis.docx | 50 | 0 | - | False |
| docx | Information\Vorlesung\WISs\Bestimmung der Dichte von Flüssigkeiten mit der Steighöhen.docx | 47 | 22 | - | False |
| docx | Mechanical\messundsteuerungstechnik\MSR2\MSR2\Lab\MT1\MT1_Bericht.docx | 27 | 21 | - | True |
| docx | Mechanical\messundsteuerungstechnik\MSR2\MSR2\Lab\MT1_Bericht.docx | 26 | 25 | - | True |
| docx | Mechanical\messundsteuerungstechnik\Mess\Messtechnik.docx | 26 | 25 | - | False |
| docx | BachelorArbeit\Praxisphase\Bericht\Theorie zur Schätzung.docx | 22 | 8 | - | False |
| docx | Information\Vorlesung\WISs\Gesetz von Boyle Mariotte für wi.docx | 20 | 14 | - | False |
| docx | Mechanical\messundsteuerungstechnik\MSR2\MSR2\Lab\MT1\MT5 Gruppe 1.docx | 17 | 5 | - | False |
| docx | Mechanical\messundsteuerungstechnik\MSR2\MSR2\Lab\MSR2\Auf1\MSR.docx | 14 | 12 | - | True |
| docx | Mechanical\messundsteuerungstechnik\MSR2\MSR2\Lab\MT2\Bericht.docx | 14 | 3 | - | True |
| docx | BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\MyApplikation.docx | 9 | 0 | - | False |
| docx | BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\tabe.docx | 9 | 8 | - | False |
| docx | BachelorArbeit\Projekt\arbeit\AmmarSayyadiMBIProjekt.docx | 9 | 0 | - | False |
| docx | Mechanical\messundsteuerungstechnik\MSR2\MSR2\Lab\nFin\FEM1-Bericht.docx | 9 | 7 | - | True |
| docx | BachelorArbeit\Praxisphase\Bericht\Fourier.docx | 8 | 8 | - | False |
| docx | BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\identifizierung.docx | 7 | 5 | - | False |
| docx | BachelorArbeit\Projekt\AmmarSayyadiMBIProjekt.docx | 7 | 0 | - | False |
| docx | BachelorArbeit\Projekt\SemesterProjectAmmarSayyadi.pptx.docx | 7 | 0 | - | False |
| docx | BachelorArbeit\Projekt\SemesterProjekt.docx | 7 | 0 | - | False |
| docx | BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Tabelln.docx | 5 | 0 | - | False |
| docx | BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Min.docx | 2 | 0 | - | False |
| docx | BachelorArbeit\Projekt\Copy\Dokumentation.docx | 1 | 0 | - | True |
| docx | BachelorArbeit\Projekt\Dokummentation.docx | 1 | 0 | - | True |
| docx | Mechanical\messundsteuerungstechnik\MSR2\MSR2\Auto\BasisProg.docx | 1 | 1 | - | False |
| pptx | Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung11_lösung.pptx | 322 | 127 | 20 / 44 | True |
| pptx | BachelorArbeit\Praxisphase\Bericht\PraxisphaseAmmarSayyadi.pptx | 43 | 38 | 8 / 41 | False |
| pptx | BachelorArbeit\BAP\Bachelor.pptx | 27 | 21 | 3 / 22 | True |
| pptx | BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelor.pptx | 27 | 21 | 3 / 27 | True |
| pptx | BachelorArbeit\Praxisphase\Bericht\PraxisphaseMBI.pptx | 24 | 22 | 2 / 12 | False |
| pptx | Information\MO\MO\Aufgabenblätter\Heimaufgaben\Musterlösungen Präsenzübungen\Übung6_lösung.pptx | 19 | 3 | 5 / 22 | True |
| pptx | BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Praesentation.pptx | 13 | 0 | 3 / 89 | False |
| pptx | BachelorArbeit\Praxisphase\FR.pptx | 6 | 6 | 1 / 1 | False |
| pptx | BachelorArbeit\Projekt\Semester ProjektMBI.pptx | 5 | 0 | 2 / 38 | False |
| pptx | BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Praesentation.pptx | 4 | 1 | 2 / 34 | False |
| pptx | BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Stueckelmaier\Praesentation.pptx | 4 | 1 | 2 / 31 | False |
| pptx | Mechanical\werkstoffkunde\WK\WERK\Stiller\ergänzende Folien_Vorlesung GWK_WiSe 2021.pptx | 2 | 2 | 1 / 9 | False |
| pptx | BachelorArbeit\Projekt\Präsentation.pptx | 1 | 0 | 1 / 31 | False |
