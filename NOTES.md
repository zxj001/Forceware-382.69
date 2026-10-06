# GP108 (GeForce GT 1030) notes

Working notes for adding GP108 support on the `gp108` branch. Plan and task tracking: [#1](https://github.com/zxj001/Forceware-382.69/issues/1), with sub-issues [#2](https://github.com/zxj001/Forceware-382.69/issues/2) (donor driver), [#3](https://github.com/zxj001/Forceware-382.69/issues/3) (nouveau / linux-firmware) and [#4](https://github.com/zxj001/Forceware-382.69/issues/4) (NVIDIA published docs).

## Repository state (upstream `main` @ `9935e77`)

- GP108 is excluded everywhere: `README.md`, `REBUILDING.md` §4 and §10, `templates/package/ListDevices.txt`, `templates/package/README-INSTALL.txt`.
- No GP108 code exists in `sources/` or `rebuild.py`, and there is no `1D01` entry in the INF.
- The closest existing work is GP107 (`sources/gp107/gp107.s`, `templates/package/Documentation/GP107-experimental.md`):
  - A hook at preferred VA `0x46F7AA` keeps the GP106 registration, then registers GP107 index `0x3B` through its own 82-pointer table.
  - The added block at `0xD07C40` holds the FECS/GPCCS constructors and an 87,842-byte graphics bundle from the Quadro 376.84 x86 donor.
  - The ACR/VPR/SEC2 resources and the SEC2 boot-descriptor adapter (`sources/sec2-bootdesc.S`) are shared with the other Pascal chips.
  - XP 368.81 already had a GP107 identity and lacked only the family registration. **It is not known yet whether 368.81 has any GP108 identity.**
- **GP107 does not work.** Testers reported Code 10, and `9935e77` removed the GP107 INF entries while keeping the code.
- Upstream branch `gp107-test2` (`bb1afc0`) differs from `main` in one instruction plus INF/docs. In `gp107_caps`, `mov byte ptr [esi+0x62d],0` becomes `,1`. It is an untested guess about the meaning of that capability flag.
- `gp108` is branched from `main`, which passed hardware tests on the GTX 1080 Ti, not from `gp107-test2`.

## Donor driver concern

- The GP107 resources come from **Quadro 376.84** (January 2017). The GT 1030 launched around May 2017, so 376.84 very likely has no GP108 resources. *Unverified: the expanded donor hasn't been inspected for GP108 yet.*
- A GP108 donor must be a **32-bit (x86) Win7/8** `nvlddmkm.sys` that lists `DEV_1D01`. The earliest such release is preferred, because it is closest to 368.81's internal layouts. NVIDIA's 32-bit drivers ended with the 390 series. Tracked in #2.
- Firmware donors are the expanded `Display.Driver/nvlddmkm.sys` (from `nvlddmkm.sy_`), pinned by SHA-256 like the existing inputs in `REBUILDING.md` §2.1.

## Reference sources (guidance only, don't copy)

- nouveau: `drivers/gpu/drm/nouveau/nvkm/engine/device/base.c` (GP108 vs GP107 chipset entries), `engine/gr/`, `subdev/acr/`, `engine/sec2/`.
- `linux-firmware`: `nvidia/gp108/` vs `nvidia/gp107/`.
- NVIDIA `open-gpu-doc`: Pascal class headers (`0xC197`, `0x9870`, `0x927C`, …).
- NVIDIA `open-gpu-kernel-modules` is Turing and newer only. It has no Pascal support, though its shared class/ctrl headers may help.

## Test environment

### Hardware / host

- Proxmox VE 9.2.2, kernel 7.0.2-6-pve, UEFI boot with GRUB, root on LVM.
- Supermicro board, Xeon E3-1270L v4 (VT-x/VT-d), 31 GB RAM.
- The onboard ASPEED AST2400 is the host's boot VGA (`boot_vga=1`), so the GT 1030 (`boot_vga=0`) is free for passthrough.
- GT 1030: Gigabyte, `01:00.0` `10de:1d01` + HDMI audio `01:00.1` `10de:0fb8`, subsystem `1458:3799`.
- IOMMU group 1 contains only `00:01.0` (root port), `01:00.0` and `01:00.1`.
- IOMMU was already on by default on this kernel. The explicit parameters were added anyway.

### Host passthrough configuration

`/etc/modprobe.d/vfio.conf`:

```
options vfio-pci ids=10de:1d01,10de:0fb8
softdep nouveau pre: vfio-pci
softdep snd_hda_intel pre: vfio-pci
blacklist nouveau
blacklist nova_core
```

`/etc/modules`: `vfio`, `vfio_iommu_type1`, `vfio_pci`.

`/etc/default/grub`: `GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on iommu=pt"`, then `update-grub` and `update-initramfs -u -k all`, then reboot.

After the reboot, both functions show `Kernel driver in use: vfio-pci`.

Notes:

- `nomodeset` on the kernel command line comes from `/etc/default/grub.d/installer.cfg` (added by the Proxmox installer). It's harmless.
- `update-grub` warns that `grub-efi-amd64` isn't installed. This was already the case before these changes, and the config update still applies. `apt install grub-efi-amd64` fixes the warning.

### XP VM (VMID 101, `xp-gp108`)

```
ostype: wxp
machine: pc-i440fx-11.0     # i440fx; XP handles it better than q35
bios: seabios
cpu: host,hidden=1          # hide KVM so older NVIDIA drivers don't give the VM Code 43
cores: 2
memory: 3072
balloon: 0                  # XP has no balloon driver
ide0: local-lvm:vm-101-disk-0,size=30G
net0: rtl8139=BC:24:11:93:06:25,bridge=vmbr0
serial0: socket             # for WinDbg kernel debugging later
vga: none
hostpci0: 0000:01:00,pcie=0,x-vga=1
```

- Installed from *Windows XP Professional SP3 x86 Integral Edition 2024.11.29 (Vanilla)* with `vga: std`, then switched to passthrough. This is a community remix with integrated updates and drivers, not stock SP3.
- Starting the VM prints `failed to reset PCI device '0000:01:00.0' ... trying to continue`. The card has no PCIe function-level reset, and it works anyway. If the GPU hangs after a guest crash, reboot the host.
- The Proxmox noVNC console is blank with `vga: none`. Use the in-guest VNC server (below) or a monitor on the GT 1030.
- The guest gets its IP from DHCP: `192.168.1.141` at the time of writing. Reserve it on the router.

### Snapshots

LVM-thin, disk-only. With a passed-through PCI device a snapshot can't include RAM, so shut down first.

| Snapshot | State |
|---|---|
| `clean_xp` | XP installed, emulated VGA, no NVIDIA driver |
| `vnc_ready` | `clean_xp` + TightVNC service, emulated VGA |

`hostpci0` / `vga: none` were set after `vnc_ready`. Check `qm config 101` after a rollback.

### Remote control: TightVNC in the guest

- TightVNC 2.8.90 32-bit MSI (`tightvnc-2.8.90-gpl-setup-32bit.msi`, SHA-256 `669bcf5796c2655fb1a8b556cad8decf25d3008a650ef495b1ed3882aa918211`), from tightvnc.com. It runs on XP.
- Installed with no input devices: the VM was stopped, the disk was mounted on the host (`losetup -fP --show /dev/pve/vm-101-disk-0`, `mount -t ntfs3 /dev/loopNp1`), and the MSI was copied to `C:\vncsetup\` along with a batch file in `All Users\Start Menu\Programs\Startup` that runs at the next login:

  ```
  msiexec /i "C:\vncsetup\tightvnc.msi" /quiet /norestart /l*v "C:\vncsetup\install.log" ADDLOCAL=Server SERVER_REGISTER_AS_SERVICE=1 SERVER_ADD_FIREWALL_EXCEPTION=1 SET_USEVNCAUTHENTICATION=1 VALUE_OF_USEVNCAUTHENTICATION=1 SET_PASSWORD=1 VALUE_OF_PASSWORD=<pw> SET_USECONTROLAUTHENTICATION=1 VALUE_OF_USECONTROLAUTHENTICATION=1 SET_CONTROLPASSWORD=1 VALUE_OF_CONTROLPASSWORD=<pw>
  ```

  The batch file deletes itself afterwards. The VNC password is 8 characters at most and isn't stored in this repo. Keep port 5900 LAN-only.
- Scripted screenshots and input from Linux: `vncdo -s <ip>::5900 -p <pw> capture out.png` (from `pip install vncdotool`).

## Results

### 2026-10-05: baseline, no NVIDIA driver

GT 1030 passed through as primary VGA. XP boots and displays through the GT 1030 at 640×480 using its VGA BIOS.

| Device | PnP ID | Status |
|---|---|---|
| GT 1030 | `PCI\VEN_10DE&DEV_1D01&SUBSYS_37991458&REV_A1` | "Video Controller (VGA Compatible)", ConfigManagerErrorCode **1** (no driver installed) |
| HDMI audio | `PCI\VEN_10DE&DEV_0FB8&SUBSYS_37991458&REV_A1` | Code 0, Microsoft UAA Bus Driver (`HDAudBus`) |

`Win32_VideoController` returns no instances, because no display driver is installed.

### 2026-10-05: Phase 1, `main` + `1D01` INF entry only

Build `build-gp108-p1`: upstream `main` with `%XPP_GPU_58% = Section012, PCI\VEN_10DE&DEV_1D01` ("NVIDIA GeForce GT 1030") added to `nv4_dispi.inf`, and its hash/size updated in `patches.json`. An unmodified rebuild of `main` first reproduced upstream exactly (585/585 package files, 469/469 CPL files).

- Installed with `setup.exe -s -n -clean -log:C:\fwtest\nvlog -loglevel:6`. `setupapi.log`: matched `Section012`, unsigned INF accepted (Policy=Ignore), `Device install of PCI\VEN_10DE&DEV_1D01... finished successfully`. Setup exit code 1 (reboot required).
- After the reboot: **GT 1030 = ConfigManagerErrorCode 10, service `nv`**, no bugcheck. XP stays on VGA at 640x480. Same symptom testers reported for GP107.

## GP108 donor driver

| Release | 32-bit Win7/8 package | Lists `DEV_1D01`? |
|---|---|---|
| 376.84 Quadro (current GP107 donor) | pinned | no |
| 378.78 GeForce (current VPR donor) | pinned | no |
| 382.05 GeForce | `672d9f8f…5e38` | no |
| 382.19 | not on NVIDIA's server (404) | - |
| **382.33 GeForce** | `4f09a41726ecfbdd01a31a4b49cc9a9f7baae78715c9d2898f096a10f55380f9` | **yes** (`nv_dispi.inf` Section091, `nvmoi.inf`, `nvrfi.inf`) |
| 391.35 GeForce (last 32-bit) | `1687319094fbcf7bb3e45ffa713916d94ebd9c838672720558553132becd2ac3` | not checked; firmware storage format differs (see below) |

**Chosen donor: GeForce 382.33**, the earliest 32-bit release that lists the GT 1030. Download URL: `https://us.download.nvidia.com/Windows/382.33/382.33-desktop-win8-win7-32bit-international-whql.exe`. Expanded `Display.Driver/nvlddmkm.sys` SHA-256: `862d3743cd2629d0adc7b0d303a5bb4bd966df95bbca977db640ff983adf056f` (12,277,880 bytes, PE32 i386).

### Firmware layout findings

- Descriptors are `{u32 length, u32 va, u32 compressed}`. Compressed payloads are raw deflate (same as `rebuild.py`). A scan of 376.84 finds all 18 pinned resources at their recorded descriptor VAs.
- **No 376.84 ACR/SEC2/GP107 blob is byte-identical in 382.33.** The firmware was rebuilt and re-signed, so resources must be matched by structure, not hash.
- 382.33 splits firmware into per-architecture sections: `PAGErFRM`, `PAGErKPL`, `PAGErMXL`, **`PAGErPSL` (Pascal)**.
- GR bundle format: `u32 0, u32 count`, then `count` x `{u32 type, u32 size, u32 offset}`. Types: 0 fecs_data, 1 fecs_inst, 2 gpccs_data, 3 gpccs_inst, 4 sw_bundle_init, 5 sw_ctx, 6 sw_nonctx, 7 sw_method_init, plus further types.
- 382.33 `PAGErPSL` bundles (descriptor VA, length, fecs_inst size): `0xa9fdec` 87603/22684, `0xaa8e44` 84262/19375, `0xab12bc` 89792/22857, `0xab9674` 89768/22857, `0xaed7b8` 89814/22868, `0xaf5c5c` 87842/22879, `0xba5dd0` 86626/21284.
- linux-firmware `nvidia/gp108` fecs/gpccs code is not byte-identical to anything in 382.33 (it came from a later driver). Fuzzy similarity can't separate GP102/GP104/GP108.

### 382.33 chip registration (how GP108 was identified)

Pascal chip tables are registered by internal index through `push table; push index; call 0x1ceba8` stubs at `.text 0x1c7580-0x1c75e0`. Each table is **82 pointers** (the same size as upstream's XP GP107 table), and slot 29 is the GR constructor:

| Index | Table | GR ctor | Inherits | Chip |
|---|---|---|---|---|
| 0x37 | `0x564ce8` | `0x7ce4e8` (static 271-dword table `0xbb4288`) | - | GP100 |
| 0x38 | `0x564e30` | `0x7ce61e` | 0x37 | GP102 |
| 0x39 | `0x564f78` | `0x7ce89e` | 0x38 | GP104 |
| 0x3a | `0x5650c0` | `0x7ceb50` | standalone | GP10B |
| 0x3b | `0x565208` | `0x7cebf2` | 0x38 | GP106 |
| 0x3c | `0x565360` | `0x7ced84` | 0x39 | **GP107**: bundle getter `0x2bf79a` → `0xaf5c5c` (fecs/gpccs byte-identical to linux-firmware gp107) |
| 0x3d | `0x5654a8` | `0x7cf19a` | 0x3c | **GP108**: sets `[+0x420]` = getter `0x2bf732` → **`0xa9fdec`**, nulls inherited `[+0x428]` |

Chip names for 0x37-0x3b are inferred from inheritance and order. GP107 and GP108 are confirmed by firmware content and inheritance. Upstream's XP code registers GP107 as index `0x3B`, so the XP enumeration is one lower (368.81 likely predates GP10B's insertion). The earlier `0xba5dd0` guess was wrong: it is a default in the base (GP100) static table.

### GP108 resources in 382.33

**GR bundle `0xa9fdec`** vs GP107 bundle `0xaf5c5c`: identical in every directory type except:

| Type | Content | GP107 | GP108 |
|---|---|---|---|
| 0 | fecs_data | 2756 | 2752 |
| 1 | fecs_inst | 22879 | 22684 |
| 2 | gpccs_data | 2100 | 2100 (different bytes) |
| 3 | gpccs_inst | 12587 | 12547 |
| 18 | 4-byte value | `7` | `5` (meaning unknown, possibly a unit count) |

Types 4-7 (`sw_bundle_init`, `sw_ctx`, `sw_nonctx`, `sw_method_init`) equal linux-firmware gp108 exactly. The **376.84 GP107 bundle equals the 382.33 GP107 bundle except types 0-3** (microcode version only), so the tables upstream already uses for GP107 also hold for GP108.

**FECS/GPCCS signatures** (192 bytes, uncompressed):

| | GP104 | GP107 | GP108 |
|---|---|---|---|
| FECS ctor (slot 18) | `0x7dd482`: base `0x7dd2f4`, `[+0x2c]`=getter→sig, nulls `+0x28` | `0x7dd7e2`: GP104 + `[+0x2c]`=`0x2bf62a`→`0xb65700` | `0x7ddb14`: base `0x7dd2f4`, `[+0x24]`=`0x2bf5f2`→**`0xb2daf0`**, nulls `+0x28` |
| GPCCS ctor (slot 25) | `0x7cc976`: base `0x7cc7fa`, `[+0x28]`=getter | `0x7cce8a`: GP104 + `[+0x28]`=`0x2bf6aa`→`0xb9de58` | `0x7cd070`: base `0x7cc7fa`, `[+0x20]`=`0x2bf672`→**`0xb9c5f8`**, nulls `+0x24` |

This matches upstream's XP GP107 code (`get_fecs` at `+0x2c`, `get_gpccs` at `+0x28`). GP108 uses different fields (`+0x24` / `+0x20`). **Open question:** which field XP 368.81 reads, and whether the XP port can just place the GP108 getters where GP107's go.

GP108 signature SHA-256 prefixes: FECS `c8cf2a7d02d3b3d4`, GPCCS `60fa424d739ecd21`. They must be paired with the 382.33 GP108 microcode, not mixed with 376.84 resources.

**Other GP108 overrides:** GP108 differs from GP107 in 19 of 82 slots (2-8, 10, 15, 18, 19, 22, 25, 27, 29, 47, 50, 53, 55). Most inherit GP107's ctor and override one to three pointers. Slot 22 (`0x7cf2a6`) sets about 101 bytes of feature flags from scratch, slot 19 sets 6 and slot 47 sets 4. These look like capability tables, relevant to upstream's GP107 `+0x62D` capability-flag question. The GP107 effective flag set still needs to be expanded through its parent chain before comparing.

### 2026-10-05: GP108 prototypes p2/p3 and BAR0 tracing

**Tracing method:** run VM 101 by hand from `qm showcmd 101`, with `x-no-mmap=on` on `hostpci0.0` and `-trace events=/root/vfio-events -D /root/gp108-trace.log` (`vfio_region_read`, `vfio_region_write`). Every BAR access is then logged. KVM can't emulate the MMX blits XP's fallback display driver performs on BAR3 afterwards, so the guest stops with "KVM internal error" *after* the NVIDIA init has already failed. The full init sequence is captured before that. BAR0 is region0, BAR3 is region3, the I/O BAR is region5.

| Build | Change | Result |
|---|---|---|
| p1 | `main` + `1D01` INF | Code 10. Trace: SEC2 bootloader loaded (84-byte DMEM descriptor, IMEM at tag `0xfd`, BOOTVEC `0xfd00`), started, **halts at once with MAILBOX0 = `0x23`** (same status upstream saw for GP102 before switching ACR). |
| p2 | + GP108 family `0x3C` (GP107 table + 382.33 GP108 FECS/GPCCS signatures at `+0x24`/`+0x20`, GR bundle at `+0x3E0`) | Code 10, no bugcheck. (Not traced; the ACR failure precedes GR.) |
| p3 | p2 + XP ACR 0-5 descriptors pointed at the 382.33 ACR set (`0xb16cec` 16640 B, `0xb187c8` 36, `0xb189a4`/`0xb18a54` 16, `0xb18af8`/`0xb18b4c` 4) + GP108 slot 0 = GP106's ACR object (`0x4ee2b0`) | Code 10. **SEC2 now runs about 57 polls, then halts with MAILBOX0 = `0x0b`** (twice; RM retries once). The version check passes; ACR fails at a later step. |

**Secure boot (slot 0) in 382.33:** GP102/GP106/GP107/GP108 share ACR ctor `0x7df9fe` (static table `0xbce090`); GP104/GP10B use `0x7df96e` (`0xbceff0`, which holds both the new and the old 15616-byte ACR). XP: GP102/GP106 slot 0 = `0x4ee2b0`, GP104 = `0x4ee2d0`. Upstream's XP GP107 copies GP104's slot 0. Both XP ACR objects use the same ACR 0-5 descriptors at `0xc33f90 + 0x18*i` (pointer fields have base relocations).

**Implication for upstream GP107:** the GP107 Code 10 is plausibly the same ACR failure (`0x23`), not the `+0x62D` capability flag.

**Hardware-risk note:** no VBIOS/EEPROM writes, voltage, clock or fan programming were attempted. ACR rejects the firmware before any LS falcon runs. Further changes (PMU/FB/clock slots) will be derived from decompiled donor code before testing.

**Open:** meaning of ACR status `0x0b`. Candidates are LS image verification (FECS/GPCCS/SEC2 signature or WPR/LSB header format) and the SEC2 tuple (376.84, GP102-signed). Next step: decompile the 382.33 ACR/SEC2 path (Ghidra 12.1.4 headless) and XP's equivalent, then compare.

### Status (2026-10-05)

- The GT 1030 reaches the driver (`1D01` INF, GP108 family `0x3C` registered) but stops at Code 10 because secure boot (ACR on SEC2) rejects the setup: `0x23` with the 376.84 ACR, `0x0b` with the 382.33 ACR.
- VPR firmware is already consistent with 382.33. SEC2 firmware is still 376.84 (mixed release), the leading explanation for `0x0b`.
- Work on the secure-boot internals was stopped deliberately (see `DECOMP_NOTES.md`, "Scope boundary"). Graphics-engine mapping and documentation are complete; non-firmware GP108 differences are listed for future work.
- VM 101 is stopped with the p3 miniport on disk. Snapshots: `clean_xp`, `vnc_ready`, `gpu_baseline`, `p1_code10`.

### Next

- Determine which FECS/GPCCS signature field XP 368.81 reads, and map the 19 GP108 slot overrides onto XP's 82-slot GP107 table.
- Prototype: GP107 path + GP108 index/registration + 382.33 GP108 bundle + GP108 signatures, then test on the GT 1030 (#1 Phase 3).
