# Under the Hood Episode 1 How a Graphics Card Wakes Up

A two-host podcast transcript about GPU initialization, driver backporting, and the experimental GeForce GT 1030 work on Windows XP.

- **Hosts:** Maya asks the questions; Theo explains the implementation.
- **Estimated running time:** 20–25 minutes, depending on delivery and pauses.
- **Project:** Forceware 382.69, the custom package based on NVIDIA 368.81 for XP.
- **Episode status:** The GT 1030 experiment still reports Code 10. The firmware compatibility explanation is a hypothesis, not a completed fix.

## Chapters

1. What Code 10 tells us
2. A GPU contains several cooperating engines
3. The card before the NVIDIA driver
4. How Windows selects the driver
5. How the driver selects the chip implementation
6. Firmware and the processors that run it
7. The structures between the host and the GPU
8. Graphics startup and useful acceleration
9. Why GTX 1080 support differs from GT 1030 support
10. The GT 1030 experiments
11. Why a driver backport is difficult
12. How a backport is developed
13. The next experiment and its pass conditions
14. Closing

## What Code 10 tells us

**MAYA:** Theo, I plugged a graphics card into an old computer, installed a driver, and Windows said, “Code 10: this device cannot start.” What actually happened in there?

**THEO:** Windows selected a driver, but the device did not start successfully. Code 10 is the result Windows reports. It does not tell us which internal GPU operation failed.

**MAYA:** So it could be quite far into startup?

**THEO:** Yes. In our GeForce GT 1030 experiment, the trace shows a failure during authenticated firmware startup. We can name that stage because we observed the GPU registers, not because Code 10 explains it.

**MAYA:** Let's follow the whole process. Assume I know what a graphics card is, but not how a driver starts it.

**THEO:** Then the first useful distinction is where the programs run. The Windows driver runs on the computer's CPU. Firmware runs on small processors inside the GPU. The graphics and display engines have their own jobs. Initialization must make those pieces cooperate.

## A GPU contains several cooperating engines

**MAYA:** I usually imagine the GPU as one enormous processor that draws triangles.

**THEO:** The shader hardware does much of the computational work, but the chip also contains memory-management hardware, command-processing machinery, display engines, and embedded control processors. Those components need compatible state before an application can submit useful work.

**MAYA:** How does the computer talk to all of that?

**THEO:** The card appears as a PCI Express device. The operating system assigns resources, including address windows that the driver can map. Some windows expose control registers. Others expose memory. A register read might report status; a register write might configure an operation.

**MAYA:** Like a control panel beside a warehouse?

**THEO:** That's a useful starting analogy. Registers are the controls and indicators. Memory holds data and other state. But a wrong control write can affect the whole device. We must know what a register means for the actual chip before copying a setting from another driver.

**MAYA:** And the startup sequence is one long checklist?

**THEO:** It has dependencies, but the implementation can interleave reset, memory, firmware, and display operations. Our diagram is an overview of those dependencies. It is not a claim that every driver makes every call in exactly that order.

## The card before the NVIDIA driver

**MAYA:** Why can a machine show a boot screen before I install the graphics driver?

**THEO:** Platform firmware and the card's firmware can establish basic display operation before the full operating-system driver takes over. A card can provide an early picture while accelerated graphics remains unavailable.

**MAYA:** So a picture on the monitor is useful evidence, but limited evidence.

**THEO:** Exactly. Our GT 1030 could display a basic 640-by-480 image in the XP guest without the NVIDIA driver. That established a baseline for the card and passthrough setup. It did not prove that NVIDIA's graphics engine, firmware startup, or hardware rendering worked under XP.

**MAYA:** Does this backport require flashing the card's VBIOS?

**THEO:** Our current work loads resources through the driver. It does not require a VBIOS flash. We are changing what the XP driver supplies and how it prepares initialization, rather than rewriting the card's persistent startup firmware.

## How Windows selects the driver

**MAYA:** Where does the INF file enter the picture?

**THEO:** The INF describes installation and includes hardware matches. The GT 1030 has a device ID of `1D01` under NVIDIA's vendor ID. Adding that match allows Windows to select the NVIDIA package for the card.

**MAYA:** That sounds like adding support.

**THEO:** It adds installation eligibility. The selected driver still needs the chip implementation. Imagine a directory that directs a caller to the correct office. Updating the directory does not create the missing staff or equipment inside that office.

**MAYA:** And we tried that first?

**THEO:** Yes. The first experiment added the GT 1030 INF entry to the standard build. Installation completed, but the device returned Code 10 after restart. It proved that Windows could select the package. It did not establish a working GP108 driver.

**MAYA:** GP108 is the chip inside the GT 1030?

**THEO:** Yes. The retail product name and the chip-family name describe different levels. That distinction becomes important when we compare it with a GTX 1080.

## How the driver selects the chip implementation

**MAYA:** Once Windows loads the driver, how does the driver choose the right behavior?

**THEO:** It identifies the chip and selects a family implementation. In the binaries we examined, a family registers a table containing 82 constructor addresses. Those constructors create or specialize the objects that control different engines and subsystems.

**MAYA:** Could XP's driver already recognize the GT 1030 without knowing how to initialize it?

**THEO:** Yes. The XP miniport already maps the relevant device-ID range to GP108. Recognition exists, but the standard implementation does not register a GP108 family table. Our standalone prototype supplies that registration.

**MAYA:** Why build the table from GP107?

**THEO:** The newer donor's GP108 implementation derives much of its behavior from GP107. That gives us a basis for comparison. But inheritance does not establish complete equivalence. The donor has 12 real table-slot differences between GP107 and GP108. Three concern graphics firmware resources. Nine concern other initialization behavior.

**MAYA:** So “they are both Pascal” doesn't resolve those differences.

**THEO:** Right. Sharing an architecture helps us reuse machinery. It does not make every initialization callback, resource, or capability identical.

## Firmware and the processors that run it

**MAYA:** Let's meet the small processors inside the GPU.

**THEO:** For this investigation, three names matter: SEC2, FECS, and GPCCS. SEC2 is a processor involved in authenticated startup. FECS and GPCCS are control processors used by the graphics engine. Their programs are firmware.

**MAYA:** And ACR is another processor?

**THEO:** ACR names the authenticated-startup machinery and its code. In the Pascal path we are discussing, ACR startup code runs on SEC2. The ACR resources and the later SEC2 firmware resources are separate.

**MAYA:** Why does that distinction matter?

**THEO:** Because “something failed on SEC2” does not automatically mean the later SEC2 firmware is the faulty image. The processor can be executing the ACR startup program when it reports a failure concerning the prepared firmware set.

**MAYA:** What does that set contain?

**THEO:** Program images, the descriptors needed to locate and load them, and signature data. The authenticated startup path checks the required resources before successful engine startup. On this path, operational SEC2 firmware also participates in starting FECS and GPCCS.

**MAYA:** Can we fix a rejected image by changing a few instructions inside it?

**THEO:** That would no longer preserve the original signed image. Our approach uses NVIDIA's signed firmware without changing its instructions or signatures. We must supply the compatible images and the correct loading structures. We do not bypass the firmware checks.

## The structures between the host and the GPU

**MAYA:** If we have the right firmware file, why isn't loading it straightforward?

**THEO:** The bootloader needs instructions about the load operation: where code and data are, their sizes, and the entry point. The host encodes those instructions in a boot descriptor. The bootloader interprets particular fields at particular positions.

**MAYA:** So both sides need to agree on the format.

**THEO:** Yes. The standard backport already encountered a mismatch. The XP host constructs a 56-byte descriptor. The selected newer bootloader expects an 84-byte descriptor with a different layout. The original embedded buffer has only 76 bytes of capacity.

**MAYA:** We cannot just write 84 bytes into that old buffer.

**THEO:** That could overwrite neighboring state. The existing adapter builds the newer descriptor in a temporary buffer, translates the necessary fields, and uses the original copy operation. It also checks guards tied to a tested firmware build and layout.

**MAYA:** What happens when we replace that firmware with a newer donor?

**THEO:** We must check the adapter again. Its firmware-build guard might no longer match. The newer bootloader might require a different field translation. Finding the right firmware bytes is only part of establishing the interface.

**MAYA:** And protected memory adds another interface?

**THEO:** Yes. The driver prepares a protected region, called WPR, with headers, images, signatures, and loading information. Correct sizes alone are not enough. The pointers, field values, alignment, and resource associations must also be correct.

## Graphics startup and useful acceleration

**MAYA:** Suppose authenticated startup succeeds. Are we finished?

**THEO:** We have passed an important dependency. We still need the graphics control processors and engine initialization to work. The driver must prepare contexts and buffers and establish the command-submission paths used for rendering.

**MAYA:** What is a context?

**THEO:** It is the state associated with a graphics workload: the objects and settings that let the GPU execute that workload correctly. A driver can recognize the device and start firmware while still constructing the wrong context state.

**MAYA:** How do we show that acceleration actually works?

**THEO:** We execute hardware work and check its results. For Direct3D 9, a draw followed by a pixel readback is much stronger evidence than a settings panel saying that acceleration is available. OpenGL needs its own context and rendering checks. Physical monitor output needs its own confirmation.

**MAYA:** Our existing package needed fixes after initialization, too?

**THEO:** Yes. The GTX 1080 Ti work needed a display-object selection correction and a separate OpenGL display-class correction. Compute and GPU PhysX also encountered missing internal GPU-name records. Those were distinct failures with distinct fixes.

**MAYA:** Does GT 1030 need that same name-table change?

**THEO:** The current project notes say its internal name record already exists. That removes one proposed change, but it does not establish that compute features work. Those features still require execution tests after successful device startup.

## Why GTX 1080 support differs from GT 1030 support

**MAYA:** Explain the comparison directly. Why can this package support a GTX 1080 family card while GT 1030 startup fails?

**THEO:** The GTX 1080 uses GP104. The GTX 1080 Ti uses GP102. The GT 1030 uses GP108. XP 368.81 already contains substantial Pascal implementation, including registered GP104 and GP102 family paths. The standard patches connect and correct that existing implementation.

**MAYA:** What did the display correction do?

**THEO:** The display DLL missed a Pascal capability bit when selecting required display objects. The patch selects the Pascal display-root class and expands a related acceptance mask. It uses the existing XP allocation and acceleration paths.

**MAYA:** GP108 starts with less of the required implementation connected?

**THEO:** It lacks the registered family implementation, and it needs different graphics resources and callback behavior. Its donor also selects a different ACR object from the one used by GP104. That object controls startup methods and resource selection.

**MAYA:** So GP104 success doesn't mean the same resource selection is valid for GP108.

**THEO:** Correct. We have recorded GTX 1080 Ti rendering tests and P4000 operation; P4000 uses GP104. We should not turn those results into a claim that every Pascal model was individually tested. GP107 cards still have reported Code 10 failures.

**MAYA:** But aren't we using Forceware 382.69?

**THEO:** We are. That is this project's custom package version. Its underlying XP driver is NVIDIA 368.81, modified with patches and selected newer firmware. The 382.33 number describes our GP108 donor, not a replacement Windows 7 driver running on XP.

## The GT 1030 experiments

**MAYA:** Walk through what the experiments actually established.

**THEO:** The first build, p1, added the INF entry. It installed and then returned Code 10. The trace shows authenticated startup on SEC2 halting immediately with mailbox status `0x23`. The project's earlier firmware investigation associates that status with a version failure.

**MAYA:** Then p2 added the family implementation?

**THEO:** It added GP108 registration and selected GP108 graphics resources from 382.33. It still returned Code 10. We have no BAR trace for p2, so we do not assign it a measured mailbox result.

**MAYA:** What changed in p3?

**THEO:** It selected the 382.33 ACR resources and the GP106 ACR object for GP108. Startup ran longer, for about 57 polls, before returning `0x0b`. That is progress past the earlier failure, but it is still failed startup.

**MAYA:** Do we know what that later code means?

**THEO:** Our notes cite NVIDIA's open Tegra driver, nvgpu, where that value names a signature-verification failure. The notes also state that the mapping is not independently confirmed for the 2017 desktop ACR. Even if the interpretation transfers, it does not identify which image or loading input caused the rejection.

**MAYA:** What is the leading explanation?

**THEO:** p3 uses 382.33 ACR and graphics resources while retaining the 376.84 SEC2 set. That SEC2 image is not present in the 382.33 donor. The resource combination, or the structures used to supply it, is our leading suspect.

**MAYA:** Different release numbers are enough to prove an incompatibility?

**THEO:** No. The working standard package itself uses ACR and SEC2 from 376.84 with VPR resources from 378.78. Those VPR resources are byte-identical to the corresponding 382.33 resources. Compatibility must be established from the actual resources and interfaces, rather than their release labels alone.

## Why a driver backport is difficult

**MAYA:** What makes this harder than an ordinary software update?

**THEO:** Several interfaces can change independently. The newer driver targets a newer Windows graphics-driver model. Its private object layouts can differ. The chip has its own callbacks and hardware state. Firmware introduces another set of formats and startup expectations.

**MAYA:** Why not copy the whole newer Windows driver?

**THEO:** Windows XP and Windows 7 use different graphics-driver interfaces. Copying a Windows 7 module does not provide the operating-system services it expects. Our approach preserves the XP-facing stack and adapts the needed hardware behavior inside it.

**MAYA:** And we don't have the original Pascal XP driver source?

**THEO:** Right. We inspect the binaries and follow callers, data structures, and resource getters. Decompilation helps reconstruct intent, but its output still needs checking against instructions and observed behavior. NVIDIA's published open kernel modules support Turing and later GPUs; they are not a ready-made Pascal XP source tree.

**MAYA:** What errors can that reconstruction introduce?

**THEO:** A copied offset can address the wrong field in XP. A callback can use the wrong calling convention or stack cleanup. An inserted pointer can work at the preferred image address and fail when the driver relocates. A new section can have incorrect bounds or image metadata.

**MAYA:** And hardware differences add another class of problem.

**THEO:** Yes. Nine non-firmware GP108 table differences remain to evaluate. One involves memory-subsystem register writes. We must establish their purpose before mirroring them. A capability byte that looks harmless can select an initialization path with assumptions the older implementation does not satisfy.

**MAYA:** Can a GT 1030 fix break a working card?

**THEO:** It can if the change is shared. The p3 prototype rewrites ACR descriptors used by other Pascal GPUs. Before a release, that selection must be restricted to GP108 or validated on every affected family. One card passing does not establish that a shared change is safe for another.

**MAYA:** Debugging the experiment itself can also be difficult?

**THEO:** Our passthrough card lacks PCIe function-level reset, so a failed guest session can leave state that affects the next test. The tracing configuration also recorded a later KVM error during fallback VGA writes. That occurred after the NVIDIA initialization failure. We need a normal boot to confirm the driver result separately from the tracing artifact.

## How a backport is developed

**MAYA:** Describe the usual method when source code is available first.

**THEO:** Keep the implementation that works with the old operating system, bring over the needed hardware routines, and adapt their dependencies and interfaces. Rebuild it, then test the new hardware and existing devices. Source makes the intended contracts much easier to inspect.

**MAYA:** And in our proprietary-driver case?

**THEO:** First, establish a reproducible baseline. Identify the exact base driver, donor, chip, and existing failure. Then select a donor that supports the target hardware and is close enough for a useful comparison. Here that donor is the 32-bit 382.33 driver.

**MAYA:** What do we compare?

**THEO:** Family tables, constructors, firmware selection, getters, and the callers that consume their results. We map each needed behavior into the XP implementation. We preserve inherited behavior where comparison shows that it is equivalent.

**MAYA:** So we port behavior rather than copying a function without its surroundings.

**THEO:** Yes. A function may depend on object layouts, helpers, and firmware conventions that changed between releases. Those dependencies are part of the adaptation.

**MAYA:** How small should a change be?

**THEO:** Small enough to describe its cause and expected result. Register the missing family, supply an established resource set, translate a known structure, or adapt a verified callback. Change one logical cause at a time so that a new result remains interpretable.

**MAYA:** What can we check before installing it?

**THEO:** Exact input hashes and original bytes at patch locations. Compile the added assembly. Check calling conventions, stack and register preservation, relocations, section bounds, alignment, and the PE checksum. Where executable harnesses exist, use them to exercise the adapters and callbacks, including relocated addresses.

**MAYA:** And hardware validation comes in stages.

**THEO:** Successful firmware startup first. Healthy device initialization next. Then low-bandwidth physical output and hardware rendering. After that, test intended modes, optional features, restart behavior, reconnects, and shared-path regressions. Each result should identify the tested binary and configuration.

**MAYA:** Finally, the experiment becomes part of the builder.

**THEO:** Correct. Pin the donor hashes, record extraction and patch operations, extend source verification, and update package inventories and build identification. Rebuild from clean inputs. Test the integrated package again, because a successful standalone patch does not prove that the installer contains and installs the same files.

## The next experiment and its pass conditions

**MAYA:** What is the immediate next step for our GT 1030?

**THEO:** Preserve the identified p3 baseline and map the complete SEC2 set selected by the 382.33 donor. That includes the image, descriptor, signature, and loading parameters. Then verify how the XP consumers receive those resources.

**MAYA:** What else must be checked before the next hardware test?

**THEO:** The signature getters for FECS and GPCCS, protected-memory headers and resource placement, and the boot descriptor adapter's guards and field translation. The next candidate must isolate changes that would otherwise affect the existing Pascal cards.

**MAYA:** Could another mailbox tell us which image failed?

**THEO:** The Tegra reference uses additional mailbox information. Whether that interface applies to this desktop firmware must be established before treating a value as a processor ID. It is a possible diagnostic lead, not a confirmed desktop result.

**MAYA:** What counts as success for the next candidate?

**THEO:** Authenticated startup completes and reaches graphics initialization. Merely changing `0x0b` into another error does not pass. If startup succeeds, we evaluate the remaining callbacks and test physical output and hardware rendering. If it fails, we inspect the first failed operation before adding unrelated changes.

**MAYA:** And the existing scope boundary stays in place.

**THEO:** Yes. We supply compatible original NVIDIA firmware and correct host structures. We preserve firmware verification. That is the method this project is pursuing.

## Closing

**MAYA:** A visible boot screen proves basic output. An INF match selects a driver. A family table selects chip behavior. Firmware startup makes the internal processors operational. Graphics contexts, command submission, and display paths still need to work after that.

**THEO:** And each boundary explains a different kind of failure. Our GT 1030 prototype has reached an identifiable firmware-startup failure. We have a concrete resource-compatibility hypothesis and a way to test it, but we do not yet have working accelerated GP108 support.

**MAYA:** That gives the next experiment a specific question: can a compatible resource set and verified loading structures complete authenticated startup?

**THEO:** If they can, the rendering work becomes testable. The next result should tell us which dependency we have actually passed.

*[Outro music]*

## Show notes and sources

The following links support the technical explanation and the recorded experiment. The firmware-startup diagram is in section 3.1 of the plan.

- [Initialization diagram and backport procedure](../gp108/PLAN.txt)
- [Recorded p1 p2 and p3 results](../gp108/NOTES.md#2026-10-05-gp108-prototypes-p2p3-and-bar0-tracing)
- [Chip-family tables and the GP108 differences](../gp108/DECOMP_NOTES.md)
- [ACR status interpretation and its desktop applicability limit](../gp108/pieces/ACR.txt)
- [SEC2 resource set and the mixed-resource hypothesis](../gp108/pieces/SEC2.txt)
- [Boot descriptor adapter and its activation guards](../gp108/pieces/BOOTDESC.txt)
- [FECS signature selection](../gp108/pieces/FECS.txt) and [GPCCS signature selection](../gp108/pieces/GPCCS.txt)
- [Protected-memory layout](../gp108/pieces/WPR.txt)
- [Remaining non-firmware callbacks](../gp108/pieces/CAPABILITY-SLOTS.txt)
- [Existing GT 1030 internal name record](../gp108/pieces/GPU-NAMES.txt)
- [Standard package implementation and recorded validation](../../REBUILDING.md)
- [Host-side descriptor adapter source](../../sources/sec2-bootdesc.S)
- [Microsoft WDDM overview](https://learn.microsoft.com/en-us/windows-hardware/drivers/display/windows-vista-display-driver-model-design-guide) for the driver-model boundary introduced with Windows Vista
- [Nouveau Pascal SEC2 implementation](https://github.com/torvalds/linux/blob/v6.12/drivers/gpu/drm/nouveau/nvkm/engine/sec2/gp102.c) for firmware loading and commands that start FECS and GPCCS
- [Nouveau Pascal ACR implementation](https://github.com/torvalds/linux/blob/v6.12/drivers/gpu/drm/nouveau/nvkm/subdev/acr/gp102.c) for protected-memory and startup structures
- [NVIDIA open kernel module compatibility](https://github.com/NVIDIA/open-gpu-kernel-modules#compatible-gpus) for the supported GPU generations
