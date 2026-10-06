# GP108 (GeForce GT 1030) notes

Test environment, test results and donor choice for the GP108 work. Static analysis is in [DECOMP_NOTES.md](DECOMP_NOTES.md); the plan is in [PLAN.txt](PLAN.txt); one file per piece is in [pieces/](pieces/). Issue tracking: [#1](https://github.com/zxj001/Forceware-382.69/issues/1), with sub-issues [#2](https://github.com/zxj001/Forceware-382.69/issues/2) (donor driver), [#3](https://github.com/zxj001/Forceware-382.69/issues/3) (nouveau / linux-firmware) and [#4](https://github.com/zxj001/Forceware-382.69/issues/4) (NVIDIA published docs).

## Reference sources (guidance only, don't copy)

- nouveau: `drivers/gpu/drm/nouveau/nvkm/engine/device/base.c` (GP108 vs GP107 chipset entries), `engine/gr/`, `subdev/acr/`, `engine/sec2/`.
- `linux-firmware`: `nvidia/gp108/` vs `nvidia/gp107/`.
- NVIDIA `open-gpu-doc`: Pascal class headers (`0xC197`, `0x9870`, `0x927C`, …).
- NVIDIA `open-gpu-kernel-modules` is Turing and newer only. It has no Pascal support, though its shared class/ctrl headers may help.

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
| `gpu_baseline` | `vnc_ready` booted on GT 1030 passthrough, no NVIDIA driver (Code 1) |
| `p1_code10` | Phase 1 driver installed (`1D01` INF), Code 10 |

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

### 2026-10-05: GP108 prototypes p2/p3 and BAR0 tracing

**Tracing method:** run VM 101 by hand from `qm showcmd 101`, with `x-no-mmap=on` on `hostpci0.0` and `-trace events=/root/vfio-events -D /root/gp108-trace.log` (`vfio_region_read`, `vfio_region_write`). Every BAR access is then logged. KVM can't emulate the MMX blits XP's fallback display driver performs on BAR3 afterwards, so the guest stops with "KVM internal error" *after* the NVIDIA init has already failed. The full init sequence is captured before that. BAR0 is region0, BAR3 is region3, the I/O BAR is region5.

| Build | Change | Result |
|---|---|---|
| p1 | `main` + `1D01` INF | Code 10. Trace: SEC2 bootloader loaded (84-byte DMEM descriptor, IMEM at tag `0xfd`, BOOTVEC `0xfd00`), started, **halts at once with MAILBOX0 = `0x23`** (same status upstream saw for GP102 before switching ACR). |
| p2 | + GP108 family `0x3C` (GP107 table + 382.33 GP108 FECS/GPCCS signatures at `+0x24`/`+0x20`, GR bundle at `+0x3E0`) | Code 10, no bugcheck. (Not traced; the ACR failure precedes GR.) |
| p3 | p2 + XP ACR 0-5 descriptors pointed at the 382.33 ACR set (`0xb16cec` 16640 B, `0xb187c8` 36, `0xb189a4`/`0xb18a54` 16, `0xb18af8`/`0xb18b4c` 4) + GP108 slot 0 = GP106's ACR object (`0x4ee2b0`) | Code 10. **SEC2 now runs about 57 polls, then halts with MAILBOX0 = `0x0b`** (twice; RM retries once). The version check passes; ACR fails at a later step. |

**Implication for upstream GP107:** the GP107 Code 10 is plausibly the same ACR failure (`0x23`), not the `+0x62D` capability flag.

**Hardware-risk note:** no VBIOS/EEPROM writes, voltage, clock or fan programming were attempted. ACR rejects the firmware before any LS falcon runs. Further changes (PMU/FB/clock slots) will be derived from decompiled donor code before testing.

### Status (2026-10-05)

- The GT 1030 reaches the driver (`1D01` INF, GP108 family `0x3C` registered) but stops at Code 10 because secure boot (ACR on SEC2) rejects the setup: `0x23` with the 376.84 ACR, `0x0b` with the 382.33 ACR.
- VPR firmware is already consistent with 382.33. SEC2 firmware is still 376.84 (mixed release), the leading explanation for `0x0b`.
- Work on the secure-boot internals was stopped deliberately (see `DECOMP_NOTES.md`, "Scope boundary"). Graphics-engine mapping and documentation are complete; non-firmware GP108 differences are listed for future work.
- VM 101 is stopped with the p3 miniport on disk. Snapshots: `clean_xp`, `vnc_ready`, `gpu_baseline`, `p1_code10`.
