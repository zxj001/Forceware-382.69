# Podcast outline: How a GPU starts up (and why our GT 1030 doesn't, yet)

Original rough outline for a two-host, beginner-friendly episode. The completed [podcast transcript](gpu-initialization.md) uses Maya and Theo and includes the verified technical details and qualifications. Read the transcript for the final episode.

Source material: [docs/gp108](../gp108/) (README, NOTES.md, PLAN.txt and the per-piece files).

## 1. Cold open (1 min)
- Host B: "I plugged a five-year-old graphics card into a twenty-year-old operating system, and Windows says 'This device cannot start.' Why?"
- The episode's promise: follow a GPU from power-on to a working desktop, and see where ours stops.

## 2. What a GPU is, from the computer's point of view (2 min)
- The GPU is a device on the PCI Express bus, like a network or sound card.
- The computer sees it through a few memory windows: one for control registers, others for video memory.
- Analogy: a building with a front desk (registers) and a warehouse (video memory).

## 3. Power-on and the VBIOS (2 min)
- The card carries its own small startup program, the VBIOS.
- Platform and card firmware can give a basic picture before the NVIDIA driver loads; our GT 1030 showed 640x480 in the XP guest with no driver.
- Point for listeners: "the screen works" only proves basic display, not that the driver can start the card.

## 4. Windows meets the card: the INF (2 min)
- Windows reads the card's device ID and looks for a matching INF entry.
- No match: the card stays on the generic VGA driver.
- Match: Windows loads the NVIDIA kernel driver (the miniport). For the GT 1030 this is the `1D01` entry. See `INF.txt`.

## 5. The driver takes over: chip families and tables (2-3 min)
- The driver looks up the chip family and gets a table of constructors, one per engine.
- GP108 needs its own family registration. See `REGISTRATION.txt`.
- Host B asks: "Why not reuse the GP107 table?" Answer: most of it is the same, but some entries differ (`CAPABILITY-SLOTS.txt`).

## 6. Little computers inside the big one (3 min)
- A modern GPU contains small embedded processors (Falcons): SEC2, FECS, GPCCS and others.
- In the path we examined, each one runs firmware that the driver supplies.
- Short tour: SEC2 (security), FECS and GPCCS (they feed the graphics engine).

## 7. Signed firmware and secure boot (3 min)
- In the Pascal path we examined, authenticated startup (ACR) checks NVIDIA-signed firmware before the engines start.
- ACR startup code runs on SEC2; the ACR resources and the later SEC2 firmware are separate sets.
- Make the project's boundary clear: we supply NVIDIA's signed firmware without changes; we do not bypass the check (`ACR.txt`, section 6).

## 8. Our GT 1030 story so far (3 min)
- What the prototype supplies: the INF match, family registration, VPR, GPU name records, and GR/FECS/GPCCS resources (runtime behaviour unverified).
- How we watched it fail: a VM with PCI passthrough and every register access traced.
- The two results:
  - p1 (376.84 ACR): SEC2 halts at once, mailbox `0x23`.
  - p3 (382.33 ACR): about 57 polls, then `0x0B`. Tegra nvgpu names this a signature-check failure; that meaning is not confirmed for desktop ACR.
- Leading hypothesis, not a confirmed cause: p3 pairs 382.33 ACR/GR resources with 376.84 SEC2 firmware that is not in the 382.33 donor (`SEC2.txt`).

## 9. What comes next (1-2 min)
- Pull one consistent SEC2/ACR firmware set from the 382.33 donor, in the donor's layout.
- Check whether the Tegra mailbox interface applies to desktop ACR; if it does, the second mailbox may identify the failing image.
- Keep the existing Pascal paths (GP102/104/106) unchanged by the shared edits. Only GTX 1080 Ti (GP102) and P4000 (GP104) have recorded hardware results; GP106 has no hardware test (static checks only).
- Side note: the GP107 Code 10 may be the same ACR failure.

## 10. Recap (1 min)
- Power-on → VBIOS → INF match → driver tables → firmware load → secure boot → graphics engine → desktop.
- Our GT 1030 reaches the driver but stops at secure boot with Code 10; there is no working acceleration or completed fix yet.
- Close with a teaser for a later episode, when (or if) the card boots.
