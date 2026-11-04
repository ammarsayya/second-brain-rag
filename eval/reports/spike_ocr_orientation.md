# SPIKE-OCR follow-up: page-orientation census on scanned pages (T-P3-08)

Tesseract 5 orientation and script detection (`--psm 0`) on **every** scanned-page candidate (the same discovery as the sampled run in `spike_ocr.md`), not a sample. Pages OSD says need rotating are then OCR'd twice with `-l deu`: default page segmentation (`--psm 3`, what `spike_ocr.md` measured) and Tesseract's own OSD-corrected segmentation (`--psm 1`). A seeded control sample of upright pages gets the same comparison.

**Evidence, not a decision.** OSD confidence is Tesseract's unbounded score. The table gives the raw distribution and the distribution at a reported cut-off of 2.0, so the effect of the cut-off is visible. Mean word confidence is not CER: correctness still needs gold transcriptions (T-P3-03). Choosing an orientation step and threshold for the real pipeline belongs to ADR-010/T-P4.

- scanned-page candidates: 764
- pages with no embedded image: 119
- pages with another read or OSD error: 3
- pages OSD declined (too few characters): 73
- OSD rotate distribution, any confidence: 0=314, 90=54, 180=169, 270=32
- OSD rotate distribution, confidence >= 2.0: 0=236, 90=40, 180=82, 270=18, below cut-off=193
- mean word-confidence change psm1 - psm3, rotated pages: +6.2 over 243 pages
- mean word-confidence change psm1 - psm3, upright control: -0.9 over 14 pages

> **Redaction note (2026-11-04).** One row below is redacted. Its file is a personal legal document, not course material; it was classified `normal` only because rules version 1 had no court/legal-aid rule. Rules version 2 classifies it `restricted` (docs/22 §3: counts-only reporting), and the spike tools now skip such blobs. The row stays in every count above, so the statistics are unchanged; a re-run would see 763 candidates.

## Pages OSD says need rotating

| relpath | page | OSD rotate | OSD confidence | words psm3 | mean conf psm3 | words psm1 | mean conf psm1 | delta conf | error |
|---|---|---|---|---|---|---|---|---|---|
| Mechanical\Mathematik\Mathe\Math3\Vorlesung\uebungen_komb_loes.pdf | 1 | 270 | 26.63 | 291 | 84.9 | 291 | 84.9 | 0.0 |  |
| books\Studium\lernen\pdf\Numerik\Numerik Aufgabenblaetter\20180319190742706.pdf | 3 | 270 | 23.28 | 155 | 58.5 | 155 | 58.5 | 0.0 |  |
| books\Studium\lernen\pdf\PDF\doc00282120160330124815.pdf | 10 | 270 | 23.08 | 59 | 64.5 | 59 | 64.5 | 0.0 |  |
| Mechanical\Mathematik\Mathe\Math3\Vorlesung\uebung_8_wahrsch.pdf | 2 | 270 | 22.69 | 263 | 87.7 | 263 | 87.7 | 0.0 |  |
| Mechanical\Modellbildung_technischer_Systeme\ModellbTSys\be\Pic\Be1\Nili.2.pdf | 1 | 90 | 21.57 | 77 | 28.8 | 87 | 69.4 | 40.6 |  |
| Mechanical\Mathematik\Mathe\Math3\Vorlesung\loesungs_ansaetze_1.pdf | 1 | 270 | 19.95 | 206 | 80.4 | 206 | 80.4 | 0.0 |  |
| Mechanical\Bewegungstechnik\Bewe\Bewe\neu\HiDrive-Kinematik\Aufgaben Kinematik.pdf | 8 | 90 | 19.54 | 6 | 15.6 | 76 | 58.7 | 43.0 |  |
| Mechanical\Mathematik\Mathe\Math3\Vorlesung\uebungen_wahrsch_loes.pdf | 1 | 270 | 19.30 | 337 | 72.6 | 337 | 72.6 | 0.0 |  |
| Mechanical\Modellbildung_technischer_Systeme\ModellbTSys\be\Pic\Be1\Nili.3.pdf | 1 | 90 | 17.37 | 62 | 26.4 | 65 | 71.5 | 45.1 |  |
| books\Studium\lernen\pdf\Numerik\Numerik Aufgabenblaetter\20180319190859692.pdf | 2 | 270 | 15.39 | 79 | 59.4 | 79 | 59.4 | 0.0 |  |
| [redacted: restricted-class personal document, see note] | 6 | 270 | 14.99 | 288 | 94.4 | 288 | 94.4 | 0.0 |  |
| Mechanical\werkstoffkunde\WK\WK\n\Scan\Gescannt_20201017-1522 (1).pdf | 1 | 90 | 14.97 | 107 | 28.7 | 161 | 87.1 | 58.4 |  |
| books\Studium\lernen\pdf\Numerik\Numerik Aufgabenblaetter\20180319190947643.pdf | 3 | 270 | 14.65 | 59 | 69.9 | 59 | 69.9 | 0.0 |  |
| Mechanical\Mathematik\Mathe\Math3\Vorlesung\loesungs_ansaetze_2.pdf | 1 | 270 | 14.32 | 196 | 76.4 | 196 | 76.4 | 0.0 |  |
| Mechanical\Modellbildung_technischer_Systeme\ModellbTSys\be\Pic\Be1\Nili.1.pdf | 1 | 90 | 12.99 | 59 | 31.6 | 49 | 47.8 | 16.1 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Laengsdehnungen_Bsp1_Version3.pdf | 1 | 180 | 12.96 | 136 | 30.6 | 136 | 30.6 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\MAE\Sk\gg.pdf | 2 | 90 | 12.66 | 217 | 23.6 | 435 | 93.2 | 69.6 |  |
| Mechanical\Modellbildung_technischer_Systeme\ModellbTSys\be\Pic\Be1\Nili.4.pdf | 1 | 90 | 12.47 | 17 | 34.6 | 83 | 64.3 | 29.6 |  |
| books\Studium\lernen\pdf\PDF\doc00281720160330124537.pdf | 2 | 270 | 11.97 | 140 | 94.0 | 140 | 94.0 | 0.0 |  |
| Mechanical\physik\Physik\tut\Aufgabe 12 (1).pdf | 1 | 180 | 11.82 | 244 | 56.5 | 244 | 56.5 | 0.0 |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor I\SS 2016\Versuchstermine Verdichter.pdf | 1 | 90 | 10.99 | 57 | 33.5 | 100 | 62.3 | 28.8 |  |
| Mechanical\werkstoffkunde\WK\WK\n\Scan\Gescannt_20201017-1520.pdf | 1 | 90 | 10.40 | 113 | 30.6 | 239 | 83.2 | 52.6 |  |
| Mechanical\physik\Physik\tut\Aufgabe 6.pdf | 1 | 180 | 10.38 | 94 | 36.6 | 94 | 36.6 | 0.0 |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor I\SS 2016\Termine Pumpenversuch.pdf | 1 | 90 | 10.03 | 78 | 38.9 | 99 | 53.3 | 14.4 |  |
| Mechanical\werkstoffkunde\WK\WK\n\Scan\Gescannt_20201017-1508.pdf | 1 | 90 | 9.92 | 67 | 22.2 | 151 | 86.3 | 64.0 |  |
| Mechanical\Modellbildung_technischer_Systeme\ModellbTSys\be\Pic\Be1\Nili.5.pdf | 1 | 90 | 9.89 | 76 | 21.8 | 67 | 57.0 | 35.2 |  |
| Mechanical\konstruktonsgrundlagen\KG\Gescannt_20201028-1845.pdf | 1 | 90 | 9.67 | 65 | 28.3 | 63 | 74.9 | 46.6 |  |
| Mechanical\werkstoffkunde\WK\WK\n\Scan\Gescannt_20201017-1521 (1).pdf | 1 | 90 | 9.19 | 123 | 26.3 | 181 | 82.6 | 56.3 |  |
| Mechanical\konstruktonsgrundlagen\KG\Gescannt_20201028-1846.pdf | 1 | 90 | 9.02 | 54 | 25.7 | 50 | 86.9 | 61.2 |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor I\SS 15\Termine Versuch Einspritzpumpe.pdf | 1 | 90 | 8.91 | 44 | 36.7 | 78 | 63.8 | 27.0 |  |
| Information\Vorlesung\KonstGrd\Hausaufgabe\Tabellenbuch.pdf | 5 | 270 | 8.86 | 77 | 85.6 | 77 | 85.6 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\KG\Au\Tabellenbuch.pdf | 5 | 270 | 8.86 | 77 | 85.6 | 77 | 85.6 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\KG\Gescannt_20201028-1845 (1).pdf | 1 | 90 | 8.72 | 43 | 33.5 | 46 | 81.2 | 47.7 |  |
| Mechanical\konstruktonsgrundlagen\KG\Gescannt_20201028-1846 (1).pdf | 1 | 90 | 8.67 | 51 | 25.9 | 48 | 93.5 | 67.5 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Berechnungshinweise_Traegheitsmomente_Version2.pdf | 2 | 180 | 8.33 | 111 | 23.3 | 111 | 23.3 | 0.0 |  |
| Mechanical\Modellbildung_technischer_Systeme\ModellbTSys\be\Gescannt_20201125-1206.pdf | 1 | 180 | 8.11 | 116 | 55.1 | 116 | 55.1 | 0.0 |  |
| Mechanical\Mathematik\08. Musterloesung Klausur Mathematik 2 SS 2004.pdf | 2 | 180 | 7.97 | 110 | 34.9 | 110 | 34.9 | 0.0 |  |
| Mechanical\FEM\FEM2L\Td.pdf | 1 | 90 | 7.96 | 52 | 23.9 | 47 | 52.6 | 28.7 |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor II\SS 17\Versuchstermine Dieselmotor.pdf | 1 | 90 | 7.80 | 87 | 30.3 | 95 | 51.1 | 20.8 |  |
| books\Studium\do\Aufgabe 8.pdf | 1 | 180 | 7.39 | 176 | 75.5 | 176 | 75.5 | 0.0 |  |
| Mechanical\physik\Physik\tut\Aufgabe 10 (2).pdf | 1 | 180 | 7.04 | 151 | 56.1 | 151 | 56.1 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\KG\Gescannt_20201028-1836.pdf | 1 | 90 | 6.94 | 32 | 45.8 | 41 | 82.9 | 37.1 |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor II\Alte Versuchsergebnisse\Ergebnisse Ottomotor WS 2012-13\Gruppe 4.pdf | 1 | 90 | 6.90 | 135 | 22.0 | 126 | 41.7 | 19.7 |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor II\SS 16\Versuchstermine Diesel.pdf | 1 | 90 | 6.83 | 66 | 35.9 | 109 | 52.4 | 16.5 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Berechnungshinweise_tau_xs_inf_Q_duennw_Ver13.pdf | 2 | 180 | 6.81 | 132 | 34.6 | 132 | 34.6 | 0.0 |  |
| Mechanical\physik\Physik\Phy2\PHy\klausuraufg_phys2_ss2017_erg.pdf | 1 | 180 | 6.77 | 525 | 30.5 | 525 | 30.5 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Laengsdehnungen_Bsp2_Version1.pdf | 1 | 180 | 6.72 | 97 | 45.3 | 97 | 45.3 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\KG\Gescannt_20201028-1844.pdf | 1 | 90 | 6.70 | 60 | 36.1 | 57 | 80.0 | 43.9 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Berechnungshinweise_tau_xs_inf_Q_duennw_Ver12.pdf | 2 | 180 | 6.52 | 133 | 33.7 | 133 | 33.7 | 0.0 |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor I\SS 15\Termine Verdichterversuch.pdf | 1 | 90 | 6.50 | 26 | 34.5 | 94 | 54.1 | 19.6 |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor II\SS 15\Versuchstermine Dieselmotor.pdf | 1 | 90 | 6.35 | 68 | 20.4 | 95 | 55.7 | 35.3 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\WiSe1415.pdf | 3 | 180 | 6.24 | 31 | 38.7 | 31 | 38.7 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Berechnungshinweise_Laengsdehnungen_Version7.pdf | 1 | 180 | 6.11 | 81 | 29.7 | 81 | 29.7 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\auf\Loesungshinweis_Aufgabe_3_1.pdf | 1 | 180 | 6.05 | 143 | 38.4 | 143 | 38.4 | 0.0 |  |
| Mechanical\physik\Physik\Phy2\PHy\klaus_ph2_ws17_18.pdf | 1 | 180 | 6.04 | 477 | 24.4 | 477 | 24.4 | 0.0 |  |
| Mechanical\physik\Physik\tut\Aufgabe 28.pdf | 1 | 180 | 6.03 | 61 | 77.3 | 61 | 77.3 | 0.0 |  |
| Information\BetSys_1\Bet2.pdf | 1 | 270 | 5.95 | 42 | 32.3 | 34 | 35.4 | 3.1 |  |
| Mechanical\physik\Physik\tut\Aufgabe 1.pdf | 1 | 180 | 5.94 | 146 | 72.5 | 146 | 72.5 | 0.0 |  |
| Mechanical\FEM\Fin\Finit\Klausur_FEM1_SS2020_Kurzlösungen.pdf | 2 | 90 | 5.92 | 0 | - | 0 | - | - |  |
| Mechanical\konstruktonsgrundlagen\KG\Gescannt_20201028-1835.pdf | 1 | 90 | 5.77 | 62 | 34.7 | 33 | 71.4 | 36.7 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\vid\D\Webvorlesung_6.5.20_WNV_II.pdf | 1 | 180 | 5.71 | 151 | 31.8 | 151 | 31.8 | 0.0 |  |
| Mechanical\Elektrotechnik\GrundlagenElektronik\EI\Elektrotechnik-12S-mit-Lösung.pdf | 5 | 90 | 5.70 | 73 | 34.0 | 183 | 65.4 | 31.4 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\auf\Loesungshinweis_Aufgabe_4_11.pdf | 1 | 180 | 5.70 | 90 | 33.8 | 90 | 33.8 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\kin\Klausur SS2019.pdf | 2 | 180 | 5.62 | 250 | 70.1 | 250 | 70.1 | 0.0 |  |
| Mechanical\physik\Physik\tut\Aufgabe 9.pdf | 1 | 180 | 5.45 | 140 | 38.2 | 140 | 38.2 | 0.0 |  |
| Mechanical\regelungstechnik\Alte_Klausuren_2020\Musterlösung_RT2_WS2011.pdf | 4 | 180 | 5.35 | 102 | 31.1 | 102 | 31.1 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\1.5_a.pdf | 1 | 180 | 5.32 | 104 | 45.0 | 104 | 45.0 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Traegheitsmomente_Bsp1_Version1.pdf | 1 | 180 | 5.32 | 127 | 48.8 | 127 | 48.8 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\auf\Loesungshinweis_Aufgabe_1_9.pdf | 1 | 180 | 5.26 | 71 | 33.2 | 71 | 33.2 | 0.0 |  |
| Mechanical\Mathematik\Mathe\Math2\Neu.H\Tut\Loesungen_Blatt5.pdf | 1 | 180 | 5.02 | 118 | 44.2 | 118 | 44.2 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 3_8.pdf | 1 | 180 | 4.92 | 102 | 37.0 | 64 | 31.1 | -5.9 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\TutK\IMG_20200430_111131-konvertiert.pdf | 1 | 180 | 4.82 | 264 | 32.8 | 264 | 32.8 | 0.0 |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor I\WS 14 - 15\Versuchstermine Verdichterversuch.pdf | 1 | 90 | 4.71 | 79 | 37.0 | 131 | 56.4 | 19.4 |  |
| Information\vorvorl\GrdInf\n\einführung\übung\02_Uebung_Lsg_Scan.pdf | 1 | 180 | 4.69 | 78 | 38.0 | 70 | 31.6 | -6.3 |  |
| Mechanical\werkstoffkunde\WK\WK\n\Scan\Gescannt_20201017-1529 (1).pdf | 1 | 90 | 4.49 | 86 | 23.4 | 147 | 70.4 | 47.0 |  |
| Mechanical\Bewegungstechnik\Handschriftliche Erlaeuterungen zum Skript und Klausurhinweise SS2020.pdf | 15 | 180 | 4.46 | 158 | 27.0 | 158 | 27.0 | 0.0 |  |
| Information\vorvorl\GrdInf\n\mathematische grundlagen\volesung\05 Mengen Scan 3.pdf | 1 | 180 | 4.39 | 94 | 27.0 | 94 | 27.0 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Schraubenverbindung 1.KW.pdf | 3 | 180 | 4.39 | 71 | 26.2 | 71 | 26.2 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\SoSe 2011.pdf | 2 | 180 | 4.39 | 71 | 26.2 | 71 | 26.2 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kinematik_Kurzlösungen_Kap4-5.pdf | 1 | 180 | 4.35 | 21 | 39.0 | 21 | 39.0 | 0.0 |  |
| Mechanical\Mathematik\Mathe\Math1\Übungsblätter-20200728\Uebung_2_komplett.pdf | 4 | 180 | 4.31 | 0 | - | 18 | 40.5 | - |  |
| Mechanical\Mathematik\07. Uebungsblatt\07. Uebungsblatt, Vorlesung, Erlaeuterungen, Mathematik.pdf | 3 | 180 | 4.22 | 196 | 31.8 | 182 | 27.7 | -4.1 |  |
| Mechanical\Elektrotechnik\GrundlagenElektronik\EI\Klausur Elektrotechnik 09W mit Lösung 2010-01-14.pdf | 5 | 180 | 4.22 | 130 | 37.5 | 130 | 37.5 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\KG\Gescannt_20201028-1855.pdf | 1 | 90 | 4.22 | 22 | 34.0 | 62 | 80.1 | 46.0 |  |
| Information\vorvorl\GrdInf\n\einführung\vorlesung\04 Schaltwerke Scan.pdf | 1 | 180 | 4.21 | 84 | 29.2 | 84 | 29.2 | 0.0 |  |
| Information\Vorlesung\KONleh\Gruppe5_Teil1_200506 ih.pdf | 9 | 90 | 4.18 | 17 | 35.9 | 40 | 75.3 | 39.3 |  |
| Mechanical\Mathematik\07. Uebungsblatt\07. Uebungsblatt, Tutorium, Erlaeuterungen, Mathematik.pdf | 3 | 180 | 4.17 | 211 | 30.8 | 211 | 30.8 | 0.0 |  |
| Mechanical\physik\Physik\tut\Aufgabe 4.pdf | 1 | 180 | 4.10 | 193 | 59.3 | 193 | 59.3 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Berechnungshinweise_Spannungsebene_Version4.pdf | 1 | 180 | 4.04 | 120 | 29.3 | 120 | 29.3 | 0.0 |  |
| Mechanical\Mathematik\Mathe\Math2\Neu.H\Tut\Loesungen_Blatt7.pdf | 2 | 180 | 3.97 | 262 | 27.6 | 262 | 27.6 | 0.0 |  |
| Mechanical\physik\Physik\tut\Aufgabe 10 (1).pdf | 1 | 180 | 3.97 | 187 | 52.6 | 187 | 52.6 | 0.0 |  |
| Information\vorvorl\AngeInfo\Angwinf\loesungAmmarSayyadi.pdf | 2 | 180 | 3.89 | 5 | 16.1 | 5 | 16.1 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe_2.16.pdf | 1 | 180 | 3.76 | 86 | 36.0 | 86 | 36.0 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\KG\Gescannt_20201028-1840.pdf | 1 | 90 | 3.59 | 30 | 36.6 | 27 | 86.4 | 49.8 |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor I\WS 16-17\Versuchstermine Verdichter.pdf | 1 | 90 | 3.58 | 70 | 37.7 | 100 | 57.3 | 19.6 |  |
| Information\vorvorl\GrdInf\n\mathematische grundlagen\volesung\04 Prädikatenlogik Scan 2.pdf | 2 | 180 | 3.50 | 126 | 30.7 | 126 | 30.7 | 0.0 |  |
| Information\BetSys_1\Aufgabe\Gescannt_20220428-0927.pdf | 1 | 270 | 3.49 | 72 | 31.2 | 56 | 30.8 | -0.5 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe_2.15.pdf | 1 | 180 | 3.48 | 112 | 35.6 | 112 | 35.6 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 3_1.pdf | 1 | 180 | 3.48 | 21 | 42.1 | 21 | 42.1 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Duennwandig_tau_xs_Bsp3_Version1.pdf | 5 | 180 | 3.47 | 55 | 35.7 | 55 | 35.7 | 0.0 |  |
| Mechanical\physik\Physik\tut\Aufgabe 16.pdf | 1 | 180 | 3.47 | 152 | 60.7 | 152 | 60.7 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\KL\Klausur_MAE1_SoSe_2019_Ergebnisse.pdf | 1 | 180 | 3.33 | 60 | 31.4 | 60 | 31.4 | 0.0 |  |
| Mechanical\Simulationstechnik\SMS\Go\Ge\Gescannt_20201103-1034 (1).pdf | 1 | 270 | 3.20 | 8 | 23.6 | 44 | 34.9 | 11.4 |  |
| Mechanical\Mathematik\Mathe\Math2\Neu.H\Tut\Loesungen_Blatt4.pdf | 1 | 180 | 3.17 | 53 | 25.3 | 53 | 25.3 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\auf\Loesungshinweis_Aufgabe_3_6.pdf | 2 | 180 | 3.07 | 69 | 31.4 | 69 | 31.4 | 0.0 |  |
| Information\MO\MO\Tutorien\probeklausur_loesungsvorschlag.pdf | 1 | 270 | 3.02 | 129 | 22.8 | 38 | 25.9 | 3.2 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 5_2.pdf | 1 | 180 | 2.99 | 181 | 47.9 | 181 | 47.9 | 0.0 |  |
| Mechanical\Modellbildung_technischer_Systeme\ModellbTSys\be\Geregelt11.11.pdf | 1 | 180 | 2.95 | 181 | 47.6 | 181 | 47.6 | 0.0 |  |
| Mechanical\FEM\Rust\FEM_2\Aufgabe_WS16.pdf | 1 | 180 | 2.79 | 17 | 36.1 | 17 | 36.1 | 0.0 |  |
| Mechanical\Statik\Ps\Anwendung_inkrementelles_Verfahren_V2.pdf | 1 | 180 | 2.79 | 172 | 33.1 | 172 | 33.1 | 0.0 |  |
| Mechanical\Mathematik\Mathe\Math2\Neu.H\Tut\Tutoriumsaufgaben - Lösungen-20200330\Übungsblatt1_Lösungen.pdf | 1 | 180 | 2.78 | 58 | 24.0 | 58 | 24.0 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe_3.2_b.pdf | 1 | 180 | 2.75 | 61 | 47.3 | 61 | 47.3 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\auf\Loesungshinweis_Aufgabe_1_1.pdf | 1 | 180 | 2.73 | 48 | 40.8 | 48 | 40.8 | 0.0 |  |
| Mechanical\Statik\tut\1\tme1-ws0910-lsgn.pdf | 1 | 180 | 2.72 | 41 | 30.4 | 41 | 30.4 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Berechnungshinweise_Spannungsebene_Version3.pdf | 1 | 180 | 2.72 | 120 | 27.5 | 120 | 27.5 | 0.0 |  |
| Mechanical\Mathematik\Musterloesung Vorzeigeklausur Mathematik 3.pdf | 1 | 180 | 2.70 | 43 | 38.7 | 43 | 38.7 | 0.0 |  |
| Mechanical\Bewegungstechnik\40. Musterloesung.pdf | 2 | 180 | 2.62 | 69 | 31.8 | 69 | 31.8 | 0.0 |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor I\WS 14 - 15\Versuchstermine Pumpenversuch.pdf | 1 | 90 | 2.60 | 59 | 35.3 | 61 | 70.8 | 35.5 |  |
| Information\BetSys_1\Aufgabe\Gescannt_20220317-0930.pdf | 1 | 90 | 2.53 | 21 | 26.3 | 51 | 30.2 | 3.9 |  |
| Mechanical\Bewegungstechnik\Bewe\Bewe\Issam\FS 2.pdf | 1 | 180 | 2.53 | 74 | 30.5 | 74 | 30.5 | 0.0 |  |
| Mechanical\Mathematik\16. Musterloesung Klausur Mathematik 2 SS 2009.pdf | 2 | 180 | 2.53 | 41 | 35.5 | 41 | 35.5 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe_2.52.pdf | 1 | 180 | 2.51 | 105 | 40.0 | 105 | 40.0 | 0.0 |  |
| Information\vorvorl\GrdInf\n\einführung\übung\06_Uebung_Lsg_Scan.pdf | 1 | 180 | 2.48 | 47 | 29.1 | 47 | 29.1 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Aufg\Auf.S\Loesungshinweis_Aufgabe_4_13.pdf | 1 | 180 | 2.46 | 125 | 37.0 | 125 | 37.0 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 4_3.pdf | 1 | 180 | 2.45 | 118 | 40.3 | 118 | 40.3 | 0.0 |  |
| Information\vorvorl\GrdInf\n\einführung\vorlesung\09 Suchen Komplexität Scan.pdf | 1 | 180 | 2.41 | 118 | 30.7 | 118 | 30.7 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\1.5_b.pdf | 1 | 180 | 2.32 | 103 | 41.1 | 103 | 41.1 | 0.0 |  |
| Information\Java_1\AlgDat\Vor\1\Gescannt_20201016-1845.pdf | 1 | 90 | 2.31 | 214 | 30.1 | 214 | 30.1 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe_2.50.pdf | 3 | 180 | 2.31 | 105 | 37.8 | 105 | 37.8 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Duennwandig_tau_xs_Bsp2_Version1.pdf | 5 | 180 | 2.31 | 121 | 37.7 | 121 | 37.7 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\1.3_c.pdf | 1 | 180 | 2.27 | 60 | 45.2 | 60 | 45.2 | 0.0 |  |
| Mechanical\Mathematik\Mathe\Mathe1\mathe\toturium\Lösung\11Lösung - Matrizen.pdf | 3 | 90 | 2.26 | 52 | 28.6 | 52 | 28.6 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Vid\18\18. Termin 2020.05.06.pdf | 11 | 270 | 2.23 | 27 | 33.5 | 39 | 32.6 | -1.0 |  |
| Information\vorvorl\GrdInf\n\einführung\übung\07_Uebung_Lsg_Scan.pdf | 1 | 180 | 2.18 | 88 | 30.9 | 88 | 30.9 | 0.0 |  |
| Mechanical\Mathematik\Mathe\Mathe1\mathe\toturium\Zusatzm\Spickzettel Beispiel.pdf | 2 | 180 | 2.12 | 54 | 32.0 | 54 | 32.0 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Aufg\Auf.H\3_4 Lösung.pdf | 1 | 180 | 2.12 | 0 | - | 0 | - | - |  |
| Mechanical\physik\Physik\tut\Aufgabe 12.pdf | 1 | 180 | 2.11 | 210 | 59.0 | 210 | 59.0 | 0.0 |  |
| Information\vorvorl\GrdInf\n\mathematische grundlagen\volesung\05 Mengen Scan 2.pdf | 1 | 180 | 2.07 | 91 | 29.5 | 36 | 30.6 | 1.1 |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor II\WS 14 -15\Terminplan Versuche Dieselmotor.pdf | 1 | 90 | 2.06 | 19 | 28.7 | 74 | 59.8 | 31.1 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe_3.2_a.pdf | 1 | 180 | 2.00 | 90 | 40.6 | 90 | 40.6 | 0.0 |  |
| Information\DatBan\Loesung\3\V4_T2_P1_2.pdf | 1 | 90 | 1.99 | 31 | 21.3 | 31 | 21.3 | 0.0 |  |
| books\Studium\lernen\pdf\Numerik\info 1 Aufgaben und loesungen\10\Solutions\02\HA2.pdf | 1 | 180 | 1.99 | 105 | 26.2 | 75 | 24.6 | -1.7 |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor II\WS 16-17\Versuchstermine Dieselmotor.pdf | 1 | 90 | 1.98 | 82 | 38.8 | 93 | 55.6 | 16.8 |  |
| Information\Java_1\AlgDat\Vor\4\Ü7.pdf | 1 | 180 | 1.96 | 64 | 32.5 | 64 | 32.5 | 0.0 |  |
| Information\vorvorl\GrdInf\3\BA9.pdf | 1 | 180 | 1.95 | 0 | - | 0 | - | - |  |
| Betriebslehre\Managment\RechtK\r\Recht 1 SS02.pdf | 2 | 180 | 1.92 | 317 | 92.9 | 317 | 92.9 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 5_6.pdf | 1 | 180 | 1.89 | 73 | 41.1 | 51 | 49.6 | 8.4 |  |
| Mechanical\Mathematik\Mathe\Mathe1\mathe\toturium\Lösung\4Lösung- Polynomdivision.Interpolation.pdf | 1 | 180 | 1.81 | 82 | 41.4 | 82 | 41.4 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\SS_2013.pdf | 1 | 180 | 1.81 | 120 | 29.0 | 120 | 29.0 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 5_1.pdf | 1 | 180 | 1.78 | 44 | 40.4 | 45 | 25.1 | -15.4 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\SoSe 2017.pdf | 1 | 180 | 1.72 | 103 | 37.1 | 103 | 37.1 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\auf\Loesungshinweis_Aufgabe_1_6.pdf | 1 | 180 | 1.71 | 65 | 43.4 | 65 | 43.4 | 0.0 |  |
| Mechanical\FEM\Fin\Finit\Klausur_FEM1_SS2019_Kurzlösungen.pdf | 1 | 180 | 1.70 | 0 | - | 0 | - | - |  |
| Mechanical\Simulationstechnik\SMS\Go\Ge\Gescannt_20201103-1034.pdf | 1 | 270 | 1.69 | 191 | 33.5 | 187 | 31.7 | -1.8 |  |
| Mechanical\Mathematik\Beiblaetter zur Vorlesung\Beiblaetter zur Vorlesung Mathematik 3 - Teil 1.pdf | 5 | 180 | 1.68 | 46 | 36.7 | 46 | 36.7 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\auf\Loesungshinweis_Aufgabe_4_3.pdf | 1 | 180 | 1.68 | 74 | 42.2 | 74 | 42.2 | 0.0 |  |
| Mechanical\Statik\tut\1\lsg-ws1112.pdf | 1 | 180 | 1.67 | 2 | 25.9 | 2 | 25.9 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Aufg\TUt\SS_2015.pdf | 2 | 180 | 1.66 | 64 | 42.9 | 64 | 42.9 | 0.0 |  |
| Information\vorvorl\GrdInf\3\BA7.pdf | 1 | 180 | 1.65 | 0 | - | 0 | - | - |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe_2.43.pdf | 1 | 180 | 1.65 | 69 | 37.8 | 69 | 37.8 | 0.0 |  |
| Information\Java_1\AlgDat\D\GrdInf\Uebung2.pdf | 1 | 180 | 1.63 | 0 | - | 0 | - | - |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\vid\D\MAE1_W19-20_Musterlösung.pdf | 4 | 180 | 1.61 | 105 | 34.6 | 105 | 34.6 | 0.0 |  |
| Mechanical\Elektrotechnik\Elab1 (1).pdf | 1 | 270 | 1.54 | 5 | 31.6 | 5 | 31.6 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe_2.1.pdf | 1 | 180 | 1.54 | 129 | 40.9 | 129 | 40.9 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 4_2.pdf | 1 | 180 | 1.54 | 13 | 49.6 | 13 | 49.6 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Gesamt\Loesungshinweis_Aufgabe_2_47_48.pdf | 1 | 180 | 1.50 | 30 | 30.7 | 30 | 30.7 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\auf\Loesungshinweis_Aufgabe_4_1.pdf | 1 | 180 | 1.50 | 25 | 39.8 | 25 | 39.8 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\WS_2012_13.pdf | 3 | 180 | 1.49 | 67 | 40.7 | 67 | 40.7 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe_3.3.pdf | 1 | 180 | 1.48 | 94 | 48.8 | 94 | 48.8 | 0.0 |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor I\WS 15 -16\Terminplan Verdichterversuche.pdf | 1 | 90 | 1.44 | 114 | 36.4 | 152 | 49.3 | 13.0 |  |
| Mechanical\regelungstechnik\Reg1\kl\Klausuren\SS2011\RT1_SS2011_Musterlösung.pdf | 3 | 180 | 1.39 | 61 | 33.0 | 61 | 33.0 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 5_5.pdf | 1 | 180 | 1.35 | 98 | 44.0 | 98 | 44.0 | 0.0 |  |
| Information\vorvorl\GrdInf\n\einführung\vorlesung\09 Suchen Scan.pdf | 2 | 180 | 1.33 | 40 | 26.0 | 40 | 26.0 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Aufg\Auf.H\2_47 Lösung.pdf | 1 | 180 | 1.32 | 5 | 32.6 | 5 | 32.6 | 0.0 |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor I\WS 18 - 19\Unterlagen verdichter.pdf | 1 | 180 | 1.31 | 258 | 43.4 | 258 | 43.4 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 4_4.pdf | 1 | 180 | 1.29 | 57 | 34.7 | 41 | 42.6 | 8.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 5_3.pdf | 1 | 180 | 1.28 | 58 | 33.7 | 58 | 33.7 | 0.0 |  |
| books\Studium\lernen\pdf\Numerik\Numerik Aufgabenblaetter\20180319190838052.pdf | 2 | 90 | 1.27 | 55 | 28.2 | 55 | 28.2 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 2_6.pdf | 1 | 180 | 1.26 | 116 | 37.5 | 47 | 35.3 | -2.2 |  |
| Mechanical\Elektrotechnik\LAB\Konstü.pdf | 1 | 180 | 1.25 | 60 | 28.6 | 60 | 28.6 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Konü\Be\S_20201024.pdf | 1 | 180 | 1.25 | 60 | 28.6 | 60 | 28.6 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\auf\Loesungshinweis_Aufgabe_2_13.pdf | 1 | 180 | 1.23 | 33 | 32.0 | 33 | 32.0 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Gesamt\1_11 Lösung.pdf | 1 | 180 | 1.20 | 84 | 39.6 | 24 | 36.2 | -3.4 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 2_3.pdf | 1 | 180 | 1.19 | 211 | 44.0 | 211 | 44.0 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 3_7.pdf | 1 | 180 | 1.19 | 47 | 30.9 | 47 | 30.9 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\KG\Gescannt_20201125-1826.pdf | 1 | 180 | 1.03 | 80 | 41.0 | 80 | 41.0 | 0.0 |  |
| Mechanical\regelungstechnik\Reg1\kl\Klausur_RT1_SoSe_2013.pdf | 7 | 90 | 1.00 | 5 | 34.4 | 5 | 34.4 | 0.0 |  |
| Information\Java_1\AlgDat\Vor\1\Gescannt_20201016-1845 (1).pdf | 1 | 90 | 0.97 | 123 | 26.6 | 197 | 43.4 | 16.8 |  |
| Information\Java_1\AlgDat\Vor\4\Ü4.pdf | 1 | 180 | 0.97 | 285 | 40.8 | 285 | 40.8 | 0.0 |  |
| Mechanical\Statik\tut\1\Lsg Klausur 1.pdf | 1 | 180 | 0.97 | 3 | 30.9 | 6 | 44.2 | 13.3 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Aufg\Auf.H\2_52 Lösung.pdf | 1 | 180 | 0.94 | 65 | 36.0 | 65 | 36.0 | 0.0 |  |
| Information\vorvorl\GrdInf\n\TU Clausthal\Informatik 1\Lösungen der Übungen\5_3.pdf | 1 | 270 | 0.92 | 1 | 0.0 | 1 | 0.0 | 0.0 |  |
| Information\vorvorl\GrdInf\n\TU Clausthal\Informatik 1\Lösungen der Übungen\2_3_1.pdf | 1 | 270 | 0.91 | 119 | 28.6 | 103 | 42.7 | 14.2 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Gesamt\ML_MAE1_Ergebnisse_SoSe2016.pdf | 1 | 180 | 0.90 | 161 | 34.6 | 161 | 34.6 | 0.0 |  |
| Information\Vorlesung\Elab\Berechte\S_20201024_0001.pdf | 3 | 180 | 0.88 | 88 | 54.9 | 88 | 54.9 | 0.0 |  |
| Mechanical\Elektrotechnik\LAB\Elab.pdf | 3 | 180 | 0.88 | 88 | 54.9 | 88 | 54.9 | 0.0 |  |
| Mechanical\Robotertechnik\IRO_Vers._09-2004.pdf | 40 | 180 | 0.87 | 64 | 37.3 | 64 | 37.3 | 0.0 |  |
| Information\vorvorl\GrdInf\n\mathematische grundlagen\volesung\04 Prädikatenlogik Scan.pdf | 1 | 180 | 0.85 | 39 | 38.2 | 39 | 38.2 | 0.0 |  |
| Mechanical\Mathematik\10. Uebungsblatt\Uebungsaufgaben zur Vorlesung Mathematik 3 - Teil 1.pdf | 19 | 180 | 0.85 | 175 | 24.6 | 175 | 24.6 | 0.0 |  |
| Mechanical\Maschinendynamik\12. Musterloesung.pdf | 2 | 270 | 0.84 | 61 | 34.8 | 61 | 34.8 | 0.0 |  |
| Mechanical\Bewegungstechnik\39. Musterloesung.pdf | 2 | 180 | 0.80 | 10 | 16.9 | 10 | 16.9 | 0.0 |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor II\WS 16-17\Berichtsgruppen L II.pdf | 1 | 180 | 0.80 | 152 | 52.5 | 152 | 52.5 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Gesamt\Loesungshinweis_Aufgabe_2_18.pdf | 1 | 180 | 0.79 | 62 | 38.1 | 62 | 38.1 | 0.0 |  |
| Mechanical\FEM\Finit1\Vorher\kl\Klausur_FEM1_WS2020_Kurzlösungen.pdf | 1 | 180 | 0.75 | 92 | 37.8 | 92 | 37.8 | 0.0 |  |
| Mechanical\regelungstechnik\Reg22\Tut\RT2 IV,2.pdf | 3 | 180 | 0.75 | 38 | 54.8 | 38 | 54.8 | 0.0 |  |
| Mechanical\Mathematik\15. Musterloesung Klausur Mathematik 1 WS 2007-2008.pdf | 2 | 180 | 0.74 | 102 | 32.8 | 102 | 32.8 | 0.0 |  |
| Mechanical\Elektrotechnik\LAB\Versuch 1M.pdf | 4 | 180 | 0.73 | 0 | - | 0 | - | - |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor II\WS 15-16\Versuchstermine Diesel.pdf | 1 | 90 | 0.73 | 55 | 29.7 | 42 | 32.5 | 2.8 |  |
| Mechanical\Mathematik\Mathe\Mathe1\mathe\toturium\Lösung\8.Lösung - Kurvendiskussion.pdf | 3 | 270 | 0.73 | 9 | 31.3 | 5 | 37.7 | 6.4 |  |
| Mechanical\Mathematik\Mathe\Math2\Neu.H\Tut\Loesungen_Blatt8.pdf | 2 | 180 | 0.72 | 206 | 24.6 | 206 | 24.6 | 0.0 |  |
| Information\Java_1\AlgDat\Vor\4\Ü9.pdf | 1 | 180 | 0.71 | 29 | 20.1 | 29 | 20.1 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\KL\Klausur_WiSe_2018_19_Ergebnisse.pdf | 1 | 180 | 0.70 | 63 | 25.2 | 63 | 25.2 | 0.0 |  |
| Mechanical\regelungstechnik\Reg22\Tut\RT2 III,2.pdf | 8 | 180 | 0.69 | 39 | 16.4 | 39 | 16.4 | 0.0 |  |
| Mechanical\regelungstechnik\Reg\Reg2\Tut\RT2 III,2.pdf | 8 | 180 | 0.69 | 39 | 16.4 | 39 | 16.4 | 0.0 |  |
| books\Studium\lernen\pdf\Numerik\Numerik Aufgabenblaetter\20180319191201852.pdf | 4 | 90 | 0.68 | 0 | - | 0 | - | - |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\WiSe 201617.pdf | 1 | 180 | 0.63 | 60 | 36.4 | 60 | 36.4 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\WS_2012_13 (1).pdf | 3 | 180 | 0.60 | 42 | 36.9 | 42 | 36.9 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\WS_2012_13 .pdf | 3 | 180 | 0.60 | 42 | 36.9 | 42 | 36.9 | 0.0 |  |
| Mechanical\Mathematik\Mathe\Math2\Neu.H\Tut\Loesungen_Blatt6.pdf | 4 | 90 | 0.59 | 175 | 18.7 | 175 | 18.7 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 6_1.pdf | 1 | 180 | 0.59 | 0 | - | 0 | - | - |  |
| Mechanical\messundsteuerungstechnik\Messtechnik\DatenblätterDruck_und-Wegmessung\Messverstärker_HBM-M50.pdf | 1 | 180 | 0.54 | 220 | 80.0 | 220 | 80.0 | 0.0 |  |
| Mechanical\Bewegungstechnik\Bewe\Bewe\Issam\WS 99_00 (Lösung).pdf | 1 | 180 | 0.48 | 81 | 35.0 | 81 | 35.0 | 0.0 |  |
| Mechanical\regelungstechnik\Reg22\Tut\RT2 III,1.pdf | 9 | 180 | 0.47 | 19 | 60.7 | 19 | 60.7 | 0.0 |  |
| Information\DatBan\Loesung\3\V4_T2_P3.pdf | 1 | 90 | 0.44 | 2 | 3.9 | 2 | 3.9 | 0.0 |  |
| Information\BetSys_1\Aufgabe\Gescannt_20220317-0931 (1).pdf | 1 | 270 | 0.42 | 76 | 34.7 | 49 | 35.0 | 0.3 |  |
| Information\BetSys_1\Aufgabe\Gescannt_20220317-0931.pdf | 1 | 90 | 0.41 | 56 | 28.1 | 57 | 34.3 | 6.3 |  |
| books\Studium\lernen\pdf\Numerik\info 1 Aufgaben und loesungen\10\Solutions\01\HA1.pdf | 1 | 180 | 0.40 | 56 | 28.0 | 56 | 28.0 | 0.0 |  |
| Information\vorvorl\GrdInf\n\mathematische grundlagen\volesung\05 Mengen Scan.pdf | 3 | 180 | 0.32 | 61 | 29.0 | 61 | 29.0 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Gesamt\Loesungshinweis_Aufgabe_2_52.pdf | 1 | 180 | 0.32 | 43 | 34.6 | 43 | 34.6 | 0.0 |  |
| books\Studium\lernen\pdf\Numerik\info 1 Aufgaben und loesungen\6\Lösung\Boolsche Gesetze.pdf | 1 | 270 | 0.32 | 48 | 30.8 | 48 | 30.8 | 0.0 |  |
| Mechanical\messundsteuerungstechnik\Mes\mes\L├Âsung Klausur WS 15-16-2.pdf | 1 | 270 | 0.30 | 14 | 24.1 | 14 | 24.1 | 0.0 |  |
| Information\Java_1\AlgDat\Vor\5\1.pdf | 2 | 180 | 0.28 | 0 | - | 0 | - | - |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 3_4.pdf | 1 | 180 | 0.28 | 9 | 35.6 | 9 | 35.6 | 0.0 |  |
| Mechanical\messundsteuerungstechnik\MSR2\MSR2\Lab\MSR2\G\Dok1.pdf | 1 | 180 | 0.27 | 23 | 77.0 | 23 | 77.0 | 0.0 |  |
| Mechanical\Modellbildung_technischer_Systeme\ModellbTSys\be\Pic\Be1\Nili3c.pdf | 1 | 270 | 0.25 | 46 | 30.7 | 46 | 30.7 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 2_5.pdf | 1 | 270 | 0.20 | 223 | 46.7 | 223 | 46.7 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 3_5.pdf | 1 | 180 | 0.18 | 100 | 49.0 | 61 | 43.0 | -6.0 |  |
| Information\vorvorl\AngeInfo\Angwinf\SayyadiAmmar.pdf | 1 | 270 | 0.17 | 97 | 24.5 | 122 | 24.5 | -0.0 |  |
| Mechanical\Mathematik\Mathe\Mathe1\mathe\toturium\Lösung\10Lösung - Gauß.pdf | 6 | 90 | 0.17 | 6 | 5.5 | 5 | 34.2 | 28.7 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\KL\Klausur_Sommersemester_2018_Ergebnisse.pdf | 1 | 180 | 0.16 | 115 | 31.9 | 115 | 31.9 | 0.0 |  |
| Mechanical\messundsteuerungstechnik\Steuerungstechnik\ST_Skript.pdf | 42 | 180 | 0.16 | 44 | 36.8 | 44 | 36.8 | 0.0 |  |
| books\Studium\lernen\pdf\Numerik\Numerik Aufgabenblaetter\20180319191052409.pdf | 4 | 270 | 0.16 | 377 | 24.4 | 377 | 24.4 | 0.0 |  |
| Mechanical\werkstoffkunde\WK\WERK\Gescannt_20201029-1737.pdf | 1 | 180 | 0.14 | 12 | 11.9 | 12 | 11.9 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe 4.5.pdf | 3 | 180 | 0.11 | 73 | 38.9 | 73 | 38.9 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\KL\Klausur_Wintersemester_2017_18_Ergebnisse.pdf | 1 | 180 | 0.11 | 54 | 33.6 | 54 | 33.6 | 0.0 |  |
| Mechanical\Dynamik\Dyn\Auf34.pdf | 2 | 270 | 0.10 | 87 | 25.4 | 87 | 25.4 | 0.0 |  |
| Mechanical\Simulationstechnik\SMS\Go\Übungsympbpdf | 2 | 180 | 0.09 | 0 | - | 0 | - | - |  |
| Information\BetSys_1\Aufgabe\Gescannt_20220428-0926.pdf | 1 | 90 | 0.08 | 17 | 35.4 | 17 | 35.4 | 0.0 |  |
| Mechanical\Elektrotechnik\Elab1.pdf | 1 | 180 | 0.06 | 11 | 43.7 | 11 | 43.7 | 0.0 |  |
| books\Studium\lernen\pdf\Numerik\Numerik Aufgabenblaetter\20180319191313368.pdf | 4 | 90 | 0.06 | 132 | 31.2 | 132 | 31.2 | 0.0 |  |
| Information\vorvorl\AngeInfo\Angwinf\u2.ammar.sayyadi.pdf | 1 | 180 | 0.05 | 5 | 25.9 | 5 | 25.9 | 0.0 |  |
| Mechanical\Mathematik\Beiblaetter zur Vorlesung\Beiblaetter zur Vorlesung Mathematik 3 - Teil 2.pdf | 6 | 180 | 0.05 | 60 | 27.2 | 60 | 27.2 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\TutK\IMG_20200427_181652-konvertiert.pdf | 2 | 180 | 0.05 | 33 | 46.0 | 33 | 46.0 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 4_5.pdf | 1 | 180 | 0.02 | 47 | 38.8 | 31 | 43.0 | 4.3 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Gesamt\2_14 Lösung.pdf | 1 | 180 | 0.01 | 27 | 45.0 | 27 | 45.0 | 0.0 |  |

## Upright control sample (seeded, 15 pages)

| relpath | page | OSD rotate | OSD confidence | words psm3 | mean conf psm3 | words psm1 | mean conf psm1 | delta conf | error |
|---|---|---|---|---|---|---|---|---|---|
| Ckurs\Pragma9.pdf | 1 | 0 | 16.86 | 76 | 81.7 | 76 | 81.7 | 0.0 |  |
| Ckurs\Gescannt_20211104-1823.pdf | 1 | 0 | 13.69 | 84 | 85.7 | 84 | 85.7 | 0.0 |  |
| BachelorArbeit\Projekt\Rob\Roboter\Kinematic Übung Homogene Transformation.pdf | 1 | 0 | 2.61 | 8 | 48.1 | 8 | 48.1 | 0.0 |  |
| books\PhyBo\The_Art_of_Computer_Programming - Vol 1.pdf | 332 | 0 | 28.63 | 298 | 93.1 | 298 | 93.1 | 0.0 |  |
| Ckurs\Variadic8.pdf | 1 | 0 | 26.76 | 210 | 90.0 | 210 | 90.0 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\konstruktion\ss\A4_mit_Schriftfeld.pdf | 1 | 0 | 1.28 | 25 | 65.9 | 25 | 65.9 | 0.0 |  |
| Ckurs\Sockets7.pdf | 1 | 0 | 13.82 | 75 | 88.1 | 75 | 88.1 | 0.0 |  |
| Ckurs\Bitsmask1.pdf | 1 | 0 | 16.95 | 78 | 88.5 | 78 | 88.5 | 0.0 |  |
| Ckurs\Sockets04.pdf | 1 | 0 | 7.31 | 43 | 66.2 | 43 | 66.2 | 0.0 |  |
| Mechanical\Statik\übungen-tme1-tme2.pdf | 64 | 0 | 22.89 | 93 | 86.4 | 93 | 86.4 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\TutK\Lösungen Tut 4.pdf | 1 | 0 | 2.68 | 68 | 33.3 | 41 | 20.7 | -12.6 |  |
| Information\IT\auf\IT.pdf | 7 | 0 | 3.66 | 11 | 89.0 | 11 | 89.0 | 0.0 |  |
| Ckurs\Variadic6.pdf | 1 | 0 | 24.28 | 151 | 89.0 | 151 | 89.0 | 0.0 |  |
| Ckurs\Sockets12 (1).pdf | 1 | 0 | 20.68 | 133 | 90.1 | 133 | 90.1 | 0.0 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Gesamt\1_19 Lösung.pdf | 1 | 0 | 0.34 | 0 | - | 0 | - | - |  |
