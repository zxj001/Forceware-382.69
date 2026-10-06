GP108 PIECES - INDEX
====================

1. SCOPE

1.1 This folder describes each piece of the GP108 (GeForce GT 1030) work.
1.2 Each file describes one piece.
1.3 The text follows an ASD-STE100 style: short sentences, active voice,
    and one instruction in each sentence. It has not had a full
    ASD-STE100 dictionary review.
1.4 Test results are in NOTES.md. Static analysis is in DECOMP_NOTES.md.
1.5 The task sequence is in PLAN.txt.
1.6 The piece files are in the pieces/ folder.
1.7 NOTES.md, DECOMP_NOTES.md, and PLAN.txt are in this folder. Other
    paths in these documents start at the repository root.

2. TERMS

2.1 "Donor" is the NVIDIA GeForce 382.33 x86 Windows 7 driver module.
    The build reads NVIDIA firmware from the donor. The build does not
    change the firmware instructions or the signatures.
2.2 "Miniport" is nv4_mini.sys, the XP kernel driver for the GPU.
2.3 "Piece" is one part of the driver work with one clear purpose.
2.4 "Getter" is a small function that returns a firmware resource
    descriptor. The driver calls it through a stored address.
2.5 "Slot" is one entry in the 82-pointer chip table. Each slot holds a
    constructor address for one engine.
2.6 "Pass condition" is the result required before dependent work starts.

3. STATUS KEY

   DONE        The piece has a working prototype in this repository.
   PARTIAL     The piece is mapped but not complete.
   OPEN        The piece is identified but not started.
   SCOPE-STOP  Further internal analysis of this piece was stopped on
               purpose. See each file and DECOMP_NOTES.md.

4. PIECE FILES (in pieces/)

   File                Piece                                   Status
   INF.txt             Device match and install section        DONE
   REGISTRATION.txt    GP108 family table registration         DONE
   GR.txt              Graphics engine and graphics bundle     PARTIAL
   FECS.txt            Graphics front-end processor firmware   PARTIAL
   GPCCS.txt           GPC command processor firmware          PARTIAL
   ACR.txt             Authenticated firmware startup           SCOPE-STOP
   SEC2.txt            SEC2 processor firmware set              PARTIAL
   WPR.txt             Protected memory region layout          PARTIAL
   BOOTDESC.txt        SEC2 boot descriptor adapter            PARTIAL
   VPR.txt             Video protected region resources        DONE
   CAPABILITY-SLOTS.txt  Remaining GP108 table differences     OPEN
   GPU-NAMES.txt       Internal name records for compute       DONE
   BUILD.txt           Reproducible build integration          OPEN

5. READING ORDER

5.1 Read INF.txt and REGISTRATION.txt first. They describe how the card
    selects the driver and how the driver selects the GP108 paths.
5.2 Read GR.txt, FECS.txt, and GPCCS.txt next. They describe the graphics
    firmware pieces that the prototype supplies.
5.3 Read ACR.txt, SEC2.txt, WPR.txt, and BOOTDESC.txt next. They describe
    authenticated startup and the current failure.
5.4 Read VPR.txt, CAPABILITY-SLOTS.txt, GPU-NAMES.txt, and BUILD.txt last.
    They describe the remaining work.

6. SCOPE BOUNDARY

6.1 This work uses NVIDIA-signed firmware without changes.
6.2 This work does not change or defeat the firmware verification in the
    GPU. Analysis of the verification internals was stopped on purpose.
6.3 The goal is interoperability: supply the correct signed firmware in
    the layout that NVIDIA's own driver uses.
