# Decompilation notes: GP108 (GeForce GT 1030)

Static-analysis notes for porting GP108 support from NVIDIA's GeForce 382.33 Windows 7 x86 driver to the XP 368.81 miniport. Runtime results and the test environment are in [NOTES.md](NOTES.md). Plan: [#1](https://github.com/zxj001/Forceware-382.69/issues/1).

**Working rule:** derive each change from the donor's decompiled code before testing it on hardware. No blind trial changes, especially to power, clock, memory or fan paths.

## Setup

| Item | Value |
|---|---|
| Ghidra | 12.1.4 (`ghidra_12.1.4_PUBLIC_20260921.zip`, SHA-256 `ddac49f9…4d2db`), headless, in `~/tools/ghidra_12.1.4_PUBLIC` |
| JDK | Eclipse Temurin 21.0.12.1+1 (`~/tools/jdk-21.0.12.1+1`) |
| Projects | `~/tools/ghidra-projects/nv382` and `xp368`, default auto-analysis. Heap via `GHIDRA_HEADLESS_MAXMEM=4G`. |
| Donor | GeForce 382.33 x86 `nvlddmkm.sys`, SHA-256 `862d3743…adf056f`, image base `0x10000` |
| XP target | Stock 368.81 `nv4_mini.sys` (`work/expand-1`), SHA-256 `361fbed9…2edefe`, image base `0x10000` |
| Scripts | `~/tools/ghidra-scripts/DecompileList.java <outdir> <addr>...` (selected functions); `DecompileAll.java <outfile>` (whole program, `// @ <addr>` markers) |

Re-run a single decompile:

```
JAVA_HOME=~/tools/jdk-21.0.12.1+1 ~/tools/ghidra_12.1.4_PUBLIC/support/analyzeHeadless \
  ~/tools/ghidra-projects nv382 -process nvlddmkm-382.33.sys -noanalysis -readOnly \
  -scriptPath ~/tools/ghidra-scripts -postScript DecompileList.java <outdir> 0x7df9fe
```

Decompiled output is NVIDIA code and stays out of the repository. Only addresses, structure and conclusions are recorded here.

All addresses are VAs at image base `0x10000` (raw offset = RVA for both files, alignment `0x20`).

## Driver object model (both versions)

- Each GPU family registers an **82-pointer chip table** (`register_family(key, table)`). XP: `register_family` = `0x511780`. 382.33: stubs `push table; push key; call 0x1ceba8` at `0x1c7548-0x1c75e0`.
- Each table slot is an engine **constructor** `ctor(gpu, obj)`. It either copies a static method table (`rep movsd` from `.rdata`/`PAGEcRM`) or calls a parent chip's ctor, then overrides fields.
- Firmware is reached through one-argument **getters** `mov eax, descriptor; ret 4`. A descriptor is `{u32 length, u32 va, u32 compressed}`; compressed data is raw deflate. "Not present" is the shared NULL getter (`xor eax,eax; ret 4`: XP `0x850130`, 382.33 `0x27283c`).
- Several engines have **mutually exclusive getter fields**: each chip fills exactly one field of a group and nulls the inherited one.

### Slot map (confirmed in both binaries)

| Slot (offset) | Engine | Evidence |
|---|---|---|
| 0 (`0x00`) | Secure boot / ACR object | 382.33 ctors `0x7df9fe`/`0x7df96e` copy tables of ACR getters; XP `0x4ee2b0`/`0x4ee2d0` |
| 18 (`0x48`) | FECS falcon | Signature getter group `+0x20/+0x24/+0x28/+0x2c`; upstream `gp107_fecs` |
| 25 (`0x64`) | GPCCS falcon | Signature getter group `+0x1c/+0x20/+0x24/+0x28`; upstream `gp107_gpccs` |
| 29 (`0x74`) | GR | Bundle getter group 382.33 `+0x41c..+0x428` = XP `+0x3dc..+0x3e8` (XP GR fields are `0x40` lower) |

### Family keys

| Chip | XP 368.81 key / table | 382.33 key / table |
|---|---|---|
| GP100 | 0x36 / `0xb7b038` | 0x37 / `0x564ce8` |
| GP102 | 0x37 / `0xb7b180` | 0x38 / `0x564e30` |
| GP104 | 0x38 / `0xb7b2c8` | 0x39 / `0x564f78` |
| GP10B | (not registered) | 0x3a / `0x5650c0` |
| GP106 | 0x3a / `0xb7b410` | 0x3b / `0x565208` |
| GP107 | 0x3b (upstream addition) | 0x3c / `0x565360` |
| GP108 | **0x3c (to add)** | 0x3d / `0x5654a8` |

XP maps PCI device IDs to chip IDs at `0x701100-0x701190`: `0x1C80-0x1CBF` → `0x137` (GP107), `0x1D00-0x1D3F` → `0x138` (GP108). XP therefore already identifies the GT 1030 as GP108.

## GP108 vs GP107 in 382.33

The raw chip tables differ in 19 of 82 slots. Decompiling each GP108 ctor at its exact address shows that **7 of those are thunks** (a single `jmp`) to the GP107 ctor, so they are functionally identical: slots 2, 3, 7, 10, 19, 22, 47. (An earlier byte-level reading attributed feature-flag stores to slots 19, 22 and 47; those bytes belonged to the following function. Corrected here.)

The **12 real differences**:

| Slot | GP107 ctor | GP108 ctor | GP108 change | Notes |
|---|---|---|---|---|
| 18 FECS | `0x7dd7e2` (GP104 + `+0x2c`) | `0x7ddb14` (base `0x7dd2f4`) | signature getter `+0x24` → `0xb2daf0`; nulls `+0x28` | Mirrored in `sources/gp108` |
| 25 GPCCS | `0x7cce8a` (GP104 + `+0x28`) | `0x7cd070` (base `0x7cc7fa`) | signature getter `+0x20` → `0xb9c5f8`; nulls `+0x24` | Mirrored |
| 29 GR | `0x7ced84` (GP104 + `+0x428`) | `0x7cf19a` (GP107 + override) | bundle getter `+0x420` → `0xa9fdec`; nulls `+0x428` | Mirrored (XP `+0x3e0`) |
| 4 | `0x7db9e0` → method `+0x04` = `0x86de06` | `0x7dbbb2` | `+0x04` = `0x2f4628` (plain base) | Bus init (PBUS `0x1538`/`0x1558`). GP107's method adds a Quadro P400 (`0x1cb3`) quirk; GP108 drops it. XP's GP106-derived table has no such quirk. |
| 5 | `0x7cc7d4` (table `0xbafaa8`) | `0x7cc8c0` (table `0xbaed00` via `0x7cc074`) | `+0x7c` = `0x347ef8` | `0x347ef8` writes `0x10402c = 0x77777732`, `0x104034 = 0xb0a`. Memory-subsystem settings; must be understood before mirroring. |
| 6 | `0x7d15d0` (thunk to `0x7d0cb4`) | `0x7d1aa0` | `+0x0c` = `0x7e16ca` | Sets capability bytes `+0x74 = 0x01010101`, `+0x78 = 1` |
| 8 | `0x7df568` | `0x7df6dc` | `+0x400` = `0x7e18c8` | Capability-byte setter (`+0x6f8..+0x720`) |
| 15 | `0x7cd1c0` | `0x7cd27c` | `+0x24` = `0x86e60e`, `+0x57c` = `0x86e69e`, `+0x588` = `0x7e3216` | `0x7e3216` is a capability-byte setter (`+0x732..+0x7b1`); the other two select per-config paths |
| 27 | `0x7d91c8` | `0x7d926e` | `+0x134` → (0x25, `0x685f00`), `+0x138` → (0x43, `0x685950`) | Two register/value list getters (count, table) |
| 50 | `0x7de6ba` | `0x7de850` (table `0xbc9f78` via `0x7dd91c`) | `+0x88` returns `4`; `+0x94` returns `0x20000` if `arg & 0x100` | Small constant/mask getters |
| 53 | `0x7da84e` | `0x7da9c0` | `+0xd8` = `0x7e4c0e` | Capability bytes `+0x141 = 0x0101`, `+0x143 = 1` |
| 55 | `0x7d963a` | `0x7d9766` | GP106's slot-55 implementation | GP108 reverts to GP106 here |

To do for a complete port: name each engine (5, 6, 8, 15, 27, 50, 53, 55), compare each capability setter with the inherited GP104/GP106 values, and map them to XP objects. The slot-5 memory-subsystem writes are the highest-risk item and should not be mirrored without understanding them.

Slot 0 (ACR) is **identical** for GP107 and GP108 in 382.33: both use the GP102/GP106 object `0x7df9fe`.

**GR bundle `0xa9fdec`** (87603 B) vs GP107 `0xaf5c5c`: equal except FECS/GPCCS microcode (types 0-3) and type 18 (`5` vs `7`). The 376.84 and 382.33 GP107 bundles differ only in types 0-3.

## Secure boot (ACR), slot 0

382.33 ACR object tables (getter field → descriptor):

| Field | GP102/106/107/108 table `0xbce090` | GP104/GP10B table `0xbceff0` |
|---|---|---|
| `+0x64` ACR image | `0xb16cec` 16640 B | `0xb16cec` 16640 B |
| `+0x68` (alt image) | - | `0xb1875c` 15616 B (= 376.84 `0x698b34`) |
| `+0x6c` ACR header | `0xb187c8` 36 B | same, plus alt `+0x70` |
| `+0x74`, `+0x7c` | 16 B signatures `0xb189a4`, `0xb18a54` | same, plus alts |
| `+0x84`, `+0x8c` | 4 B values `0xb18af8`, `0xb18b4c` | same, plus alts |
| `+0x94..+0xa8` | second ucode set (13568 B `0xb1a298` + headers) | same |
| `+0xc4..`, `+0xf4..`, `+0x13c..`, `+0x16c..`, `+0x184..` | further ucode sets (2816, 6144, 3072, 3584, 3584 B) | same, with alternates |

Non-getter methods of `0xbce090` (fields `+0x00..+0x48`): `0x31ed0c, 0x1c7114, 0x31ec00, 0x31e94e, 0x31ed9c, 0x294844, 0x31e13e, 0x31debe, 0x31dc1a, 0x31e3a2, 0x31e302, 0x31ead0, 0x31ea46, 0x31e4e4, 0x31dbde, 0x31db8e, 0x31e448, 0x31eb90, 0x7dc5e4`.

- `0x31e4e4`: runs an HS ucode on the **PMU** (mailbox `0x10a040`, poisoned with `0xdeadbeef` first) and stores the result in registry value **`RMPsdlCertStatus`**. This is the PSDL certificate path, not the SEC2 ACR boot.
- `0x31ed9c`: allocates and fills a 256-byte-aligned buffer from a ucode descriptor (fields `[0],[1],[2],[3],[5],[6]` → load parameters), then calls `[falcon+0x3c4]` to execute it. A generic HS-ucode loader.

XP: ACR 0-5 descriptors at `0xc33f90 + 0x18*i`, getters `0x4d3e10..0x4d3eb0`, referenced from tables `.rdata 0x8ad348` and `0x8ad4e8`. SEC2 image/descriptor/signature getters `0x4ea830/0x4ea850/0x4ea880` → descriptors `0xc35118/0xc35130/0xc35154`.

## Runtime cross-check (from the BAR0 trace, see NOTES.md)

| Build | SEC2 result |
|---|---|
| ACR 376.84 (upstream) | halts immediately, MAILBOX0 `0x23` |
| ACR 382.33 set | runs about 57 polls, MAILBOX0 `0x0b` |

## Public ACR status codes (nvgpu)

NVIDIA's open-source Tegra driver **nvgpu** (MIT licensed; mirror `github.com/OE4T/linux-nvgpu`, commit `21d928824dc7`, `drivers/gpu/nvgpu/common/acr/acr_priv.h`) lists the status codes the ACR firmware returns in MAILBOX0:

| Code | Name |
|---|---|
| `0x0B` | `ACR_ERROR_LS_SIG_VERIF_FAIL`: signature verification of an LS (light-secure) falcon image failed |
| `0x1B` | `ACR_ERROR_REG_ACCESS_FAILURE` |
| `0x66` | `ACR_ERROR_WDT` (watchdog) |
| `0x84` | `ACR_ERROR_RISCV_EXCEPTION` (RISC-V ACR only) |

`acr_bootstrap.c` reads **MAILBOX1** on failure to get the falcon ID of the image that failed. IDs from `include/nvgpu/falcon.h`: PMU 0, GSPLITE 1, FECS 2, GPCCS 3, NVDEC 4, SEC2 7, MINION 10, PMU_NEXT_CORE 13.

Caveats: nvgpu documents these alongside its newer (GSP/RISC-V) ACR. The ACR codebase is shared across generations and `0x0B` fits our observation, but the mapping for the 2017 desktop Pascal ACR is not independently confirmed. `0x23` is not listed in nvgpu; upstream's reading (fused minimum version not met) comes from their disassembly of the ACR (REBUILDING.md §5.1).

**Applied to GP108 p3:** MAILBOX0 `0x0B` means the 382.33 ACR passed its own checks and then **rejected the signature of one of the LS images** in the WPR. The XP driver reads and clears only MAILBOX0 and never reads MAILBOX1 (`0x87044`; no access in either trace), so which image failed (FECS, GPCCS, SEC2 or PMU) is not yet known. This fits the mixed-release hypothesis: the SEC2 LS image and signature are from 376.84 while the ACR is from 382.33.

## Status (2026-10-05)

- **Graphics path (FECS/GPCCS/GR) is mapped** and mirrored in the `sources/gp108` prototype using NVIDIA-signed 382.33 resources, unmodified.
- **Secure-boot findings:** XP's and 382.33's WPR construction match structurally (same header and LSB header sizes). The one known layout difference is the per-falcon bootloader descriptor (76 vs 84 bytes), which upstream's SEC2 adapter already addresses.
- **Firmware version consistency:** the VPR payload, header and signatures used upstream (from 378.78) are byte-identical in 382.33. The SEC2 firmware used upstream (376.84) is **not** present in 382.33, so the p3 prototype runs a mixed-release set (382.33 ACR/GR + 376.84 SEC2). That mix is the leading explanation for ACR status `0x0b`.
- **Scope boundary:** this work only uses NVIDIA's signed firmware unmodified and never tries to alter or bypass the GPU's firmware verification. Analysis of the secure-boot internals beyond this point was stopped. Resolving the SEC2 version consistency is left open.

## Remaining work (outside secure boot)

1. Name and evaluate the non-firmware GP108 differences (slots 4, 5, 6, 8, 15, 27, 50, 53, 55) against XP's GP106/GP104 objects.
2. Build the GP108 changes into `patches.json` / `rebuild.py` (third donor input, pinned hashes) instead of the standalone `sources/gp108/patch_gp108.py`.
3. Keep the ACR change chip-specific, or verify it on GP102/GP104/GP106 hardware before any release. p3 currently swaps ACR 0-5 for every Pascal GPU.
