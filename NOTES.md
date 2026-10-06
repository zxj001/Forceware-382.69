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

### Next

- Phase 1: build upstream `main` with only a `1D01` INF entry added, install from a `gpu_baseline` snapshot, and record the result (Code 10 / Code 43 / stop code).
- Phase 2: pick and pin a GP108 donor (#2), then compare its GP108 resources with the GP107 set from 376.84.
