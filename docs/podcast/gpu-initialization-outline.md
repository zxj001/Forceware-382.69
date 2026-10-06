# Podcast outline: How a GPU starts up (and why our GT 1030 doesn't, yet)

Rough outline for a two-host, beginner-friendly episode of about 15-20 minutes. Hosts: **Host A** (explains) and **Host B** (asks the questions a newcomer would ask). Each segment lists the talking points; the full script is still to be written.

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
- The VBIOS trains the video memory and gives a basic text/VGA picture, which is why the boot screen works with no driver.
- Point for listeners: "the screen works" only proves the VBIOS ran, not that the driver can start the card.

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
- Each one runs its own firmware, and the driver must load it.
- Short tour: SEC2 (security), FECS and GPCCS (they feed the graphics engine).

## 7. Signed firmware and secure boot (3 min)
- Since Maxwell/Pascal, the GPU accepts only firmware that NVIDIA signed.
- ACR runs on SEC2 and checks each image before it is allowed to run.
- Make the project's boundary clear: we supply NVIDIA's signed firmware without changes; we do not bypass the check (`ACR.txt`, section 6).

## 8. Our GT 1030 story so far (3 min)
- What already works: the INF match, family registration, GR/FECS/GPCCS pieces, VPR, GPU name records.
- How we watched it fail: a VM with PCI passthrough and every register access traced.
- The two results:
  - p1 (376.84 ACR): SEC2 halts at once, mailbox `0x23`.
  - p3 (382.33 ACR): about 57 polls, then `0x0B`, a signature-check failure in nvgpu's naming.
- Leading explanation: p3 mixes firmware from two releases, a combination NVIDIA never shipped (`SEC2.txt`).

## 9. What comes next (1-2 min)
- Pull one consistent SEC2/ACR firmware set from the 382.33 donor, in the donor's layout.
- Read the second mailbox to find which image failed.
- Keep Pascal cards that already work (GP102/104/106) safe from the shared changes.
- Side note: the GP107 Code 10 may be the same ACR failure.

## 10. Recap (1 min)
- Power-on → VBIOS → INF match → driver tables → firmware load → secure boot → graphics engine → desktop.
- Our GT 1030 gets through about two-thirds of that chain and stops at secure boot.
- Close with a teaser for a later episode, when (or if) the card boots.

## Open items for the full script
- Pick host names and voice (the earlier draft used Maya/Theo).
- Decide how much hex to read aloud; maybe keep the codes for show notes only.
- Check each technical claim against the gp108 docs before recording.
