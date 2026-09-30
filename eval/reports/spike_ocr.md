# SPIKE-OCR: Tesseract 5 (deu) Evidence on Scanned Pages (T-P3-08)

Scope: Tesseract 5 + deu only this pass. PaddleOCR PP-OCRv5 (large ML-framework install, not stood up this pass) and remote VLM (cloud-API policy, Q-B03 pending) are recorded as not-yet-benchmarked, not silently skipped. Handwriting-presence detection has no dedicated tool/model lined up and is explicitly deferred rather than approximated from a signal (e.g. low confidence) that doesn't actually measure it.

**CER is not computed here** - it needs a gold transcription of each page (MBI-Gold-Layout, T-P3-03), which requires owner-approved labeling this session correctly did not start. What follows is real speed and Tesseract's own reported word-confidence evidence instead.

## Key findings

- **Confidence varies enormously by content type, not just "German vs English"**: the five `Ckurs\*.pdf`
  samples (`Preprocessor8`, `Bitsflags`, `Sockets31`, `Threads1`, `Deadlock`) all score 80-90% confidence and
  produce clean, correct English text - these are the task's own explicitly-named case ("English photographed
  slide captures, Ckurs"), and they read as clean digital slide exports that merely lack an extractable text
  layer, not genuine scans of paper. Genuinely handwritten/degraded German scans (e.g. the Regelungstechnik
  and Kinematik tutorial pages) score 24-45% and the OCR text is unusable prose but often still recognizable
  as garbled German once you know what to look for.
- **A real, actionable corpus defect found by this sample**: `Mechanical\werkstoffkunde\WK\WK\n\Scan\Gescannt_20201017-1522 (1).pdf`
  (literally named "Gescannt" = "scanned") is stored **upside-down/rotated 180°** - Tesseract doesn't
  auto-rotate, so its output reads as reversed character soup (`"won Em nn -usßbunuueds yane..."`, which is
  recognizable German read backwards). Any real OCR pipeline for this corpus needs a page-orientation
  detection/correction step before recognition, independent of which OCR engine ADR-010 eventually picks -
  this is not specific to Tesseract.
- **4 of 25 sampled "scanned" pages had no embedded raster image at all** (`Bahnplanung.pdf`, `Rt1_20210514.pdf`
  page 3, `Rt3_20210604.pdf`, and one more) despite testing textless by :func:`is_scanned_page` - likely
  pages that are vector-only (e.g. a diagram with no raster background) or embed the image via a less common
  PDF structure this pass's simple `page.images` check doesn't reach. Worth a closer look if OCR coverage
  matters for the final pipeline, but out of this spike's scope to resolve.

- scanned-page candidates found in the corpus: 764
- sampled for this run (seeded): 25
- pages with no embedded image to OCR: 4
- pages OCR'd successfully: 21
- mean time per page: 1.52s
- mean word confidence (Tesseract's own 0-100 scale): 52.0

## Per-page results

| relpath | page | elapsed (s) | words recognized | mean confidence | text sample | error |
|---|---|---|---|---|---|---|
| Ckurs\Preprocessor8.pdf | 1 | 1.654 | 125 | 87.01568636 | t#else  «to complement the #ifdef/#ifndef and #if directives, you have the #else directive works exactly the same way as the else statement does  -identifies a group of directives to be executed or st |  |
| Ckurs\Bitsflags.pdf | 1 | 0.921 | 59 | 80.4856102881356 | nple (cont’d)  ned int packed_data; // 32 bits on most systems  ın then arbitrarily assign specific bits or fields inside packed_data to ad to store the five data values  cked_data has three unused bi |  |
| BachelorArbeit\Projekt\Rob\Roboter\Bahnplanung.pdf | 1 | - | - | - |  | no embedded image found |
| Mechanical\regelungstechnik\Regelungstechnik-2.pdf | 32 | 0.379 | 25 | 44.366583520000006 | BOQ\aT BEGETNANCZLECHAIK e'30  vVpp’e°’S’IB: BODE-DTSRLIWW STuse JIT-pAzfswE  T8., 5 2 T8, 3 2 I 5 2 710 ss 2 T8; o ! ! ! ! |  |
| Information\vorvorl\AngeInfo\Angwinf\u2.ammar.sayyadii.pdf | 1 | 1.232 | 10 | 24.0452904 | Käse,  mr  % Fe =  SELZESINZ  EB EIN  .  AEEBARn |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Tut\Lösungen 6-10, 6-15, 4.1 und 4.3.pdf | 1 | 0.201 | 0 | None |  |  |
| Information\vorvorl\GrdInf\n\mathematische grundlagen\volesung\04 Prädikatenlogik Scan.pdf | 1 | 1.022 | 39 | 38.15565582051282 | Se L &s) olas Assersbelligt Poultat x Ve y  A Nx E y\ Loy) - Jeder LH yanandan.  - Jeder ec Um jenauda  3. IxlVy ltocn))  4. 3x (vl Ley)  5. 1x (Lex)  sch Sr  !  Beuspie Liu ahzur |  |
| Mechanical\regelungstechnik\Reg1\Kalla\Schreiben\Rt1_20210514.pdf | 3 | - | - | - |  | no embedded image found |
| Mechanical\Robotertechnik\neuRob\Robtech\[14] Interaktion mit der Umgebung.pdf | 1 | 0.184 | 0 | None |  |  |
| Ckurs\Sockets31.pdf | 1 | 0.892 | 121 | 89.45075595867769 | write function  ° the write function attempts to write nbyte bytes from the buffer pointed by buf to the file associated with the open file descriptor, fildes  int write(int fildes, const void *buf, i |  |
| Mechanical\Modellbildung_technischer_Systeme\ModellbTSys\be\Pic\Be1\Nili.2.pdf | 1 | 1.384 | 77 | 28.750066571428572 | zeige 2 EEE ET + + -a u a5 Seil auewauıo‘ gg een u u .  (b) uıs- „2-1 = Wr zu OssepyzPIp yaınp NOySENussseW op Inz SunIoyeN (b)urs-32- 4— = W :4 1JeIY OIp y9ınp Juawowyaıq sep ın) SunpyeNn (b)uıs-@ -3 |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Festigkeit\Laengsdehnungen_Bsp1_Version3.pdf | 1 | 1.457 | 136 | 30.634989544117648 | RpA_ laugsdeuuugen , Vezvou 8, 1.3.2045 o 7, bege hau: E,Au=h,h=tH, 0, F  r u * = —=*  * berucht+ ; Du uud I  LöoSung! Vube laruu te iı pr Au ZN = Ä r 2 AL =  Voswor Kafleı De = EA Alfa = E-ra-ufa M b |  |
| Mechanical\Bewegungstechnik\47. Musterloesung.pdf | 2 | 0.289 | 21 | 44.556785714285716 | a; My SE - _ —— WERL.  100 soo \- [soo \ 700 soo Pu = 60°  + >» -300  [min] |  |
| Information\vorvorl\AngeInfo\Angwinf\SayyadiAmmar.pdf | 1 | 4.202 | 99 | 24.414881656565658 | - EEE | 5 ERBE  Bike 7 | BER  Sie] 723  E Ei, ee  a M +  1) = a rn | |< | ES | Ele we imnlEcE 4 8 SI CCKSERFRERE  | -rPreee E SUN EHER lege  tt —  a:  Ns -ttet  Eee SU jet er  / > N I there) m a RE Bi |  |
| Ckurs\Threads1.pdf | 1 | 0.808 | 74 | 86.84110854054055 | pthreads API  ° the functions that comprise the pthreads API can be grouped into three major categories  ° thread management ° routines that work directly on threads - creating, detaching, joining, et |  |
| Mechanical\regelungstechnik\Reg3\Rt3_20210604.pdf | 1 | - | - | - |  | no embedded image found |
| Mechanical\konstruktonsgrundlagen\KG\Au\Tabellenbuch.pdf | 5 | 3.596 | 77 | 85.62807035064935 | 3.10 Toleranzen und Passungen  ISO-Passungen  System Einheitswelle — für Toleranzklassen”)  Grenzabmaße in Hu für Bohrungen für für Bohrungen  Welle | Beim Fügen mit einer | h5-Welle entsteht eine  Üb |  |
| Mechanical\werkstoffkunde\WK\WK\n\Scan\Gescannt_20201017-1522 (1).pdf | 1 | 1.831 | 107 | 28.692451467289718 | won Em nn -usßbunuueds yane sBuipuajje ueye}s}us Bunjpuemun S!p ySınd ‘usueH sep 'g 'z aim usyayyaıBowsßunnequeag ajjsızads ySınpep = JsuUysIaZaq USUONEYIJIPoyy Sdonyojje SIE USPISM USULMIO I 3SIIG 'U |  |
| Ckurs\Deadlock.pdf | 1 | 0.652 | 36 | 85.91874791666666 | Simple Deadlock example  ° the order of applying the mutex is also important ° potential for deadlock  void *functioni()  {  pthread_mutex_lock(&lock1); - Execution step 1 pthread_mutex_lock(&lock2);  |  |
| books\Studium\lernen\pdf\Numerik\Numerik Aufgabenblaetter\20180319191313368.pdf | 4 | 6.699 | 131 | 31.295405030534354 | mm ——— 0 m  zur u einen nn . SEIFE  EEE a | nn EEE hi =X [en QUFE, BE nn _I97A 70 I STAA, IWlı I | | nn  nn Ihe EI, VE mern Be  EEE EEE EEE ET + 1 TE  . en nn nenn nen  m — mm [2 —m  Leo) xe [1  150)  |  |
| Mechanical\Kolbenmaschinen\Todsen\Labor II\SS 17\Versuchstermine Dieselmotor.pdf | 1 | 1.174 | 91 | 33.16302542857143 | u9de.1yur UIWEUYJIEN UAP Inu ayıgq  00:81 x Proz. x x x -00:91 ee parat 2 2) 5’ ir) i ‚ ä ; nN x Er j j : Djopereen JaU7o2 mm Sayaı5 n Pe: © 00:91 >yoruıı rg over ran | YA ' 3an0ın 00:71 vE3177% duysı |  |
| books\Studium\do\Aufgabe 8.pdf | 1 | 1.07 | 176 | 75.27631603409091 | 8. Drehimpuls: Auf einer masselosen Stange sind zwei Kugeln der Masse m jeweils im Abstand  b vom Mittelpunkt der Stange durch einen Faden verbunden (siehe Skizze). Im Zustand A rotiert die Anordnung  |  |
| Mechanical\konstruktonsgrundlagen\MAE_3\Kinematik\Tut\Kin 5_3.pdf | 1 | 0.947 | 56 | 32.38516533928571 | =  ie.  F JE “ ) z od  Er  _>  ut leliae alniebsmmd  A  ara  eg  BP in as  Pr) 7 1ro I Malt ESEL | 13 Kl Ir |]  = m + Nr |  > | lu PEEZENM 80400 PT  fe A) = oO \ r g An + = BEN! sie | Eite er |  |
| Mechanical\physik\Physik\tut\Aufgabe 9.pdf | 1 | 1.362 | 137 | 37.62029471532847 | sie für das Herunterrollen?  Lösung: n=5,74 11 t=2,225 | 17.01 2006  vr 2Stum Ps  EL Mn 2a, 05”  WEy7Z u S Ei + aha + rub 7 Vrdaydiuk- mgch zw" r Av’ r mg» Cos(d) vs I$mr” A 23 Weh> A a] Ahr) as Ban 4 |  |
| Information\Java_1\AlgDat\D\GrdInf\4\Doc.pdf | 10 | - | - | - |  | no embedded image found |
