# SPIKE-OCR follow-up: rotation oracle and correction policies (T-P3-08)

Every scanned-page candidate's first embedded image is OCR'd with `tesseract -l deu --psm 3` four times, turned 0/90/180/270 degrees clockwise. `--psm 3` does no orientation correction itself, so the rotation is the only variable. The rotation with the most words at confidence >= 80 is the **readability oracle**; a leader within 15% of the runner-up is *ambiguous*, and a page with fewer than 5 such words in every rotation is *unreadable* (no verdict). OSD (`--psm 0`) and the page's PDF `/Rotate` are then scored against the oracle.

**Evidence, not a decision.** The oracle is a proxy, not ground truth: it is only as good as Tesseract's own confidence, and it says nothing about CER (that needs T-P3-03 gold transcriptions). The orientation step and threshold for the pipeline stay with ADR-010/T-P4. Blobs the sensitivity gate rejects are not opened (counts on stderr only).

- scanned-page candidates: 757; scored at all four rotations: 633; no embedded image: 119; other errors: 5
- oracle verdicts: 0=256, 90=152, 180=45, 270=15; ambiguous=311; unreadable=165
- OSD vs oracle (both decided): 48/153 agree (31.4%); OSD declined 70, oracle abstained 410
- OSD vs oracle by OSD call: 0: 26/58 agree, 90: 10/14 agree, 180: 10/72 agree, 270: 2/9 agree
- wall time: 438 s with 14 workers

## Correction policies scored against the oracle

Only pages with a decided, unambiguous oracle verdict count. *Made worse* = pages the oracle reads best as stored that the policy rotates anyway.

| policy | correct | made worse |
|---|---|---|
| never rotate | 72/157 (45.9%) | 0 |
| honour PDF /Rotate | 74/157 (47.1%) | 1 |
| apply OSD at confidence >= 0.0 | 50/157 (31.8%) | 44 |
| apply OSD at confidence >= 1.0 | 61/157 (38.9%) | 28 |
| apply OSD at confidence >= 2.0 | 62/157 (39.5%) | 21 |
| apply OSD at confidence >= 5.0 | 72/157 (45.9%) | 6 |
| apply OSD at confidence >= 10.0 | 73/157 (46.5%) | 0 |

## PDF /Rotate against the oracle

| PDF /Rotate | oracle 0 | oracle 90 | oracle 180 | oracle 270 | ambiguous or unreadable |
|---|---|---|---|---|---|
| 0 | 71 | 53 | 20 | 6 | 454 |
| 90 | 0 | 2 | 0 | 0 | 6 |
| 270 | 1 | 3 | 0 | 1 | 16 |

## Pages where OSD and a decided oracle disagree (105)

| relpath | page | PDF /Rotate | OSD rotate | OSD confidence | oracle rotate | words>=80 at 0/90/180/270 |
|---|---|---|---|---|---|---|
| Mechanical\Modellbildung_technischer_Systeme\ModellbTSys\be\Pic\Be1\Nili.1.pdf | 1 | 0 | 90 | 12.99 | 180 | 6 / 20 / 24 / 7 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Laengsdehnungen_Bsp1_Version3.pdf | 1 | 0 | 180 | 12.96 | 90 | 6 / 12 / 7 / 5 |
| Mechanical\physik\Physik\tut\Aufgabe 6.pdf | 1 | 0 | 180 | 10.38 | 90 | 5 / 8 / 3 / 3 |
| Mechanical\Kolbenmaschinen\Todsen\Labor I\SS 15\Berichtsgruppen.pdf | 1 | 0 | 0 | 9.91 | 90 | 47 / 57 / 9 / 5 |
| Mechanical\werkstoffkunde\WK\WK\n\Scan\Gescannt_20201017-1521.pdf | 1 | 0 | 0 | 9.54 | 90 | 54 / 67 / 14 / 11 |
| Mechanical\Kolbenmaschinen\Todsen\Labor II\Alte Versuchsergebnisse\Ergebnisse Ottomotor WS 2012-13\Gruppe 4.pdf | 1 | 0 | 90 | 6.90 | 180 | 2 / 12 / 30 / 3 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Berechnungshinweise_tau_xs_inf_Q_duennw_Ver13.pdf | 2 | 0 | 180 | 6.81 | 90 | 16 / 20 / 3 / 3 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\WiSe1415.pdf | 3 | 0 | 180 | 6.24 | 0 | 9 / 7 / 6 / 6 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Berechnungshinweise_Laengsdehnungen_Version7.pdf | 1 | 0 | 180 | 6.11 | 90 | 6 / 8 / 3 / 3 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\auf\Loesungshinweis_Aufgabe_3_1.pdf | 1 | 0 | 180 | 6.05 | 0 | 15 / 7 / 7 / 1 |
| Information\BetSys_1\Bet2.pdf | 1 | 0 | 270 | 5.95 | 180 | 3 / 2 / 6 / 2 |
| Mechanical\physik\Physik\tut\Aufgabe 1.pdf | 1 | 0 | 180 | 5.94 | 0 | 95 / 34 / 15 / 10 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\kin\Klausur SS2019.pdf | 2 | 0 | 180 | 5.62 | 0 | 139 / 97 / 17 / 20 |
| Mechanical\regelungstechnik\Alte_Klausuren_2020\Musterlösung_RT2_WS2011.pdf | 4 | 0 | 180 | 5.35 | 0 | 10 / 7 / 3 / 5 |
| Mechanical\Prozessleittechnik\CAE-PLS\PLS-Vorlesung-Folien.pdf | 45 | 90 | 0 | 5.27 | 90 | 34 / 49 / 10 / 10 |
| Mechanical\Prozessleittechnik\PLS-Vorlesung-Folien.pdf | 45 | 90 | 0 | 5.27 | 90 | 34 / 49 / 10 / 10 |
| Mechanical\Mathematik\Mathe\Math2\Neu.H\Tut\Loesungen_Blatt5.pdf | 1 | 0 | 180 | 5.02 | 0 | 19 / 10 / 10 / 7 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 3_8.pdf | 1 | 0 | 180 | 4.92 | 0 | 7 / 0 / 4 / 0 |
| Information\vorvorl\GrdInf\n\einführung\übung\02_Uebung_Lsg_Scan.pdf | 1 | 0 | 180 | 4.69 | 90 | 5 / 7 / 5 / 5 |
| Mechanical\Bewegungstechnik\Handschriftliche Erlaeuterungen zum Skript und Klausurhinweise SS2020.pdf | 15 | 0 | 180 | 4.46 | 0 | 9 / 6 / 3 / 3 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Schraubenverbindung 1.KW.pdf | 3 | 0 | 180 | 4.39 | 90 | 5 / 20 / 1 / 7 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\SoSe 2011.pdf | 2 | 0 | 180 | 4.39 | 90 | 5 / 20 / 1 / 7 |
| Mechanical\Mathematik\07. Uebungsblatt\07. Uebungsblatt, Vorlesung, Erlaeuterungen, Mathematik.pdf | 3 | 0 | 180 | 4.22 | 90 | 11 / 13 / 7 / 9 |
| Information\vorvorl\GrdInf\n\einführung\vorlesung\04 Schaltwerke Scan.pdf | 1 | 0 | 180 | 4.21 | 90 | 5 / 7 / 1 / 1 |
| Mechanical\Dynamik\Dyn_1\HiDrive-Maschinendynamik 1\Gemischte.pdf | 7 | 0 | 0 | 4.18 | 90 | 3 / 7 / 1 / 3 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Berechnungshinweise_Spannungsebene_Version4.pdf | 1 | 0 | 180 | 4.04 | 0 | 8 / 1 / 5 / 4 |
| Mechanical\Mathematik\Mathe\Math2\Neu.H\Tut\Loesungen_Blatt7.pdf | 2 | 0 | 180 | 3.97 | 0 | 7 / 5 / 0 / 2 |
| Mechanical\physik\Physik\tut\Aufgabe 10 (1).pdf | 1 | 0 | 180 | 3.97 | 0 | 64 / 20 / 6 / 7 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe_2.16.pdf | 1 | 0 | 180 | 3.76 | 0 | 10 / 4 / 2 / 3 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 6_2.pdf | 1 | 0 | 0 | 3.70 | 180 | 0 / 0 / 18 / 0 |
| Information\vorvorl\GrdInf\n\mathematische grundlagen\volesung\04 Prädikatenlogik Scan 2.pdf | 2 | 0 | 180 | 3.50 | 0 | 9 / 7 / 5 / 5 |
| Mechanical\Simulationstechnik\SMS\Go\Ge\Gescannt_20201103-1034 (1).pdf | 1 | 0 | 270 | 3.20 | 90 | 0 / 19 / 2 / 15 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\auf\Loesungshinweis_Aufgabe_3_6.pdf | 2 | 0 | 180 | 3.07 | 90 | 4 / 8 / 2 / 3 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 5_2.pdf | 1 | 0 | 180 | 2.99 | 0 | 34 / 1 / 2 / 6 |
| Mechanical\Robotertechnik\neuRob\Robtech\Wiederholungerweitertenmatix.pdf | 1 | 0 | 0 | 2.98 | 180 | 46 / 36 / 61 / 1 |
| books\Studium\lernen\pdf\Numerik\Numerik Aufgabenblaetter\20180319191133101.pdf | 3 | 270 | 0 | 2.98 | 270 | 27 / 3 / 4 / 41 |
| Mechanical\Modellbildung_technischer_Systeme\ModellbTSys\be\Geregelt11.11.pdf | 1 | 0 | 180 | 2.95 | 0 | 36 / 18 / 8 / 3 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe_3.2_b.pdf | 1 | 0 | 180 | 2.75 | 90 | 15 / 19 / 4 / 6 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\auf\Loesungshinweis_Aufgabe_1_1.pdf | 1 | 0 | 180 | 2.73 | 90 | 5 / 6 / 2 / 2 |
| Mechanical\Statik\tut\1\tme1-ws0910-lsgn.pdf | 1 | 0 | 180 | 2.72 | 90 | 1 / 6 / 0 / 4 |
| Mechanical\Mathematik\Musterloesung Vorzeigeklausur Mathematik 3.pdf | 1 | 0 | 180 | 2.70 | 0 | 6 / 3 / 0 / 1 |
| Mechanical\Bewegungstechnik\40. Musterloesung.pdf | 2 | 0 | 180 | 2.62 | 0 | 5 / 4 / 1 / 3 |
| Ckurs\Sockets03.pdf | 1 | 0 | 0 | 2.60 | 90 | 3 / 5 / 0 / 0 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\TutK\2_1.pdf | 1 | 0 | 0 | 2.60 | 270 | 1 / 0 / 1 / 8 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe_2.52.pdf | 1 | 0 | 180 | 2.51 | 0 | 19 / 14 / 3 / 2 |
| Mechanical\Mathematik\Mathe\Math2\Neu.H\Tut\Tutoriumsaufgaben - Lösungen-20200330\Übungsblatt3_Lösungen.pdf | 3 | 0 | 0 | 2.50 | 90 | 1 / 7 / 5 / 5 |
| Information\vorvorl\GrdInf\n\einführung\übung\06_Uebung_Lsg_Scan.pdf | 1 | 0 | 180 | 2.48 | 90 | 2 / 5 / 4 / 3 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\1.5_b.pdf | 1 | 0 | 180 | 2.32 | 0 | 16 / 11 / 4 / 5 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Duennwandig_tau_xs_Bsp2_Version1.pdf | 5 | 0 | 180 | 2.31 | 90 | 12 / 15 / 1 / 11 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\1.3_c.pdf | 1 | 0 | 180 | 2.27 | 0 | 9 / 7 / 1 / 0 |
| Mechanical\regelungstechnik\Reg1\kl\Klausuren\SS2010\Lösungen_Regelungstechnik_1_SS2010.pdf | 4 | 0 | 0 | 2.04 | 90 | 3 / 6 / 4 / 1 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe_3.2_a.pdf | 1 | 0 | 180 | 2.00 | 0 | 17 / 13 / 2 / 11 |
| Mechanical\Modellbildung_technischer_Systeme\ModellbTSys\be\Gescannt_20201125-1240.pdf | 1 | 0 | 0 | 1.99 | 90 | 10 / 18 / 3 / 5 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\SS_2013.pdf | 1 | 0 | 180 | 1.81 | 90 | 3 / 5 / 3 / 3 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\auf\Loesungshinweis_Aufgabe_1_6.pdf | 1 | 0 | 180 | 1.71 | 0 | 6 / 5 / 3 / 3 |
| Mechanical\Simulationstechnik\SMS\Go\Ge\Gescannt_20201103-1034.pdf | 1 | 0 | 270 | 1.69 | 90 | 18 / 44 / 14 / 37 |
| Mechanical\Mathematik\Beiblaetter zur Vorlesung\Beiblaetter zur Vorlesung Mathematik 3 - Teil 1.pdf | 5 | 0 | 180 | 1.68 | 270 | 5 / 2 / 8 / 13 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe_2.43.pdf | 1 | 0 | 180 | 1.65 | 0 | 5 / 4 / 0 / 2 |
| Mechanical\konstruktonsgrundlagen\MAE_3\vid\D\MAE1_W19-20_Musterlösung.pdf | 4 | 0 | 180 | 1.61 | 270 | 8 / 9 / 10 / 12 |
| Mechanical\regelungstechnik\Reg22\Tut\RT2 V,1.pdf | 3 | 0 | 0 | 1.61 | 90 | 3 / 9 / 2 / 4 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe_2.1.pdf | 1 | 0 | 180 | 1.54 | 0 | 15 / 6 / 1 / 3 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\WS_2012_13.pdf | 3 | 0 | 180 | 1.49 | 0 | 12 / 8 / 4 / 3 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\Aufgabe_3.3.pdf | 1 | 0 | 180 | 1.48 | 90 | 15 / 19 / 3 / 3 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\TutK\Lösung 3.2.pdf | 1 | 0 | 0 | 1.46 | 90 | 2 / 5 / 4 / 2 |
| Mechanical\Kolbenmaschinen\Todsen\Labor I\WS 18 - 19\Unterlagen verdichter.pdf | 1 | 0 | 180 | 1.31 | 0 | 42 / 18 / 12 / 2 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\auf\Loesungshinweis_Aufgabe_1_11.pdf | 1 | 0 | 0 | 1.28 | 270 | 4 / 3 / 2 / 6 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Gesamt\1_11 Lösung.pdf | 1 | 0 | 180 | 1.20 | 0 | 10 / 0 / 5 / 0 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 2_3.pdf | 1 | 0 | 180 | 1.19 | 0 | 41 / 23 / 33 / 25 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\AlteK\Klausur-Kinematik_SS2019_Kurzlösungen.pdf | 1 | 0 | 0 | 1.13 | 180 | 3 / 2 / 10 / 0 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Gesamt\Klausur_WiSe_2016_17_Aufgaben_Ergebnisse.pdf | 1 | 0 | 0 | 1.12 | 180 | 5 / 4 / 7 / 3 |
| Information\Java_1\AlgDat\Vor\4\Ü5.pdf | 1 | 0 | 0 | 1.08 | 90 | 2 / 7 / 0 / 0 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 2_2.pdf | 1 | 0 | 0 | 0.98 | 90 | 0 / 15 / 0 / 0 |
| Information\Java_1\AlgDat\Vor\4\Ü4.pdf | 1 | 0 | 180 | 0.97 | 0 | 40 / 9 / 14 / 5 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\auf\Loesungshinweis_Aufgabe_3_4.pdf | 1 | 0 | 0 | 0.94 | 90 | 2 / 6 / 2 / 5 |
| Information\vorvorl\GrdInf\n\TU Clausthal\Informatik 1\Lösungen der Übungen\5_3.pdf | 1 | 270 | 270 | 0.92 | 90 | 4 / 7 / 2 / 4 |
| Mechanical\Mathematik\10. Uebungsblatt\Uebungsaufgaben zur Vorlesung Mathematik 3 - Teil 1.pdf | 19 | 0 | 180 | 0.85 | 0 | 9 / 5 / 7 / 2 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Gesamt\Loesungshinweis_Aufgabe_2_18.pdf | 1 | 0 | 180 | 0.79 | 0 | 12 / 5 / 0 / 1 |
| Mechanical\regelungstechnik\Reg22\Tut\RT2 V,2.pdf | 5 | 0 | 0 | 0.79 | 90 | 5 / 8 / 2 / 0 |
| Mechanical\FEM\Finit1\Vorher\kl\Klausur_FEM1_WS2020_Kurzlösungen.pdf | 1 | 0 | 180 | 0.75 | 0 | 10 / 5 / 8 / 4 |
| Mechanical\Mathematik\15. Musterloesung Klausur Mathematik 1 WS 2007-2008.pdf | 2 | 0 | 180 | 0.74 | 0 | 11 / 5 / 5 / 7 |
| Mechanical\Mathematik\Mathe\Math2\Neu.H\Tut\Loesungen_Blatt8.pdf | 2 | 0 | 180 | 0.72 | 90 | 5 / 11 / 2 / 4 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\KL\Klausur_WiSe_2018_19_Ergebnisse.pdf | 1 | 0 | 180 | 0.70 | 90 | 1 / 5 / 2 / 1 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\WiSe 201617.pdf | 1 | 0 | 180 | 0.63 | 0 | 9 / 6 / 2 / 0 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Gesamt\Loesungshinweis_Aufgabe_2_51.pdf | 2 | 0 | 0 | 0.60 | 90 | 6 / 8 / 3 / 1 |
| Mechanical\Mathematik\Mathe\Math2\Neu.H\Tut\Loesungen_Blatt6.pdf | 4 | 0 | 90 | 0.59 | 0 | 5 / 3 / 0 / 0 |
| Mechanical\Bewegungstechnik\Bewe\Bewe\Issam\WS 99_00 (Lösung).pdf | 1 | 0 | 180 | 0.48 | 0 | 11 / 6 / 3 / 5 |
| Mechanical\regelungstechnik\Reg22\Tut\RT2 III,1.pdf | 9 | 0 | 180 | 0.47 | 90 | 5 / 6 / 1 / 1 |
| Information\BetSys_1\Aufgabe\Gescannt_20220317-0931 (1).pdf | 1 | 0 | 270 | 0.42 | 0 | 8 / 1 / 6 / 3 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Aufg\Auf.H\2_48 Lösung.pdf | 1 | 0 | 0 | 0.42 | 180 | 3 / 0 / 8 / 0 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 3_3.pdf | 1 | 0 | 0 | 0.38 | 180 | 5 / 4 / 10 / 0 |
| Mechanical\Mathematik\Mathe\Math1\Übungsblätter-20200728\Uebung_4_Loesungen_aktualisiert.pdf | 4 | 0 | 0 | 0.35 | 90 | 5 / 21 / 13 / 8 |
| books\Studium\lernen\pdf\Numerik\New folder\09 Ingenieurmathematik III 2009-02-16.pdf | 1 | 0 | 0 | 0.35 | 90 | 7 / 10 / 1 / 4 |
| Information\vorvorl\GrdInf\n\mathematische grundlagen\volesung\05 Mengen Scan.pdf | 3 | 0 | 180 | 0.32 | 0 | 8 / 3 / 3 / 5 |
| books\Studium\lernen\pdf\Numerik\info 1 Aufgaben und loesungen\6\Lösung\Normalformen.pdf | 1 | 0 | 0 | 0.32 | 90 | 4 / 5 / 4 / 4 |
| Mechanical\Modellbildung_technischer_Systeme\ModellbTSys\be\Ski11.pdf | 1 | 0 | 0 | 0.31 | 90 | 4 / 5 / 1 / 1 |
| Mechanical\Modellbildung_technischer_Systeme\ModellbTSys\be\Pic\Be1\Nili3c.pdf | 1 | 0 | 270 | 0.25 | 180 | 3 / 3 / 5 / 3 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Gesamt\2_13 Lösung.pdf | 1 | 0 | 0 | 0.24 | 90 | 0 / 6 / 0 / 1 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 2_5.pdf | 1 | 0 | 270 | 0.20 | 0 | 48 / 23 / 27 / 19 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 3_5.pdf | 1 | 0 | 180 | 0.18 | 0 | 11 / 0 / 5 / 0 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\KL\Klausur_Sommersemester_2018_Ergebnisse.pdf | 1 | 0 | 180 | 0.16 | 0 | 10 / 6 / 5 / 4 |
| Ckurs\Semaphore2.pdf | 1 | 0 | 0 | 0.15 | 90 | 9 / 17 / 11 / 8 |
| Mechanical\konstruktonsgrundlagen\MAED\TutLos\KL\Klausur_Wintersemester_2017_18_Ergebnisse.pdf | 1 | 0 | 180 | 0.11 | 0 | 7 / 5 / 5 / 3 |
| Ckurs\Semaphore1.pdf | 1 | 0 | 0 | 0.07 | 90 | 3 / 37 / 24 / 5 |
| books\Studium\lernen\pdf\Numerik\Numerik Aufgabenblaetter\20180319191313368.pdf | 4 | 270 | 90 | 0.06 | 0 | 13 / 8 / 10 / 1 |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\TutK\IMG_20200427_181652-konvertiert.pdf | 2 | 0 | 180 | 0.05 | 0 | 7 / 1 / 3 / 2 |
