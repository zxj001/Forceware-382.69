.intel_syntax noprefix
.code32
.section .text
.global register_gp108, gp108_fecs, gp108_gpccs, gp108_gr
.global gp108_table, fecs108_descriptor, gpccs108_descriptor, gr108_descriptor
.global get_fecs108, get_gpccs108, get_gr108
.global acr0_payload, acr1_payload, acr2_payload, acr3_payload, acr4_payload, acr5_payload
# Experimental GP108 (GeForce GT 1030) family registration, appended after the
# GP107 block. Like gp107.s, every address is EIP-relative or rel32, so no new
# PE relocations are required.
#
# Mapping (GeForce 382.33 x86 -> XP 368.81), see docs/gp108/DECOMP_NOTES.md:
#   382.33 registers GP108 as family 0x3D, derived from GP107 (0x3C). XP's keys
#   are one lower (GP107 = 0x3B), so GP108 = 0x3C.
#   382.33 GP108 overrides GP107 in 19 of 82 slots. Only the firmware-bearing
#   ones are mirrored here: FECS (slot 18, +0x48), GPCCS (slot 25, +0x64) and
#   GR (slot 29, +0x74). The other slots keep XP's GP107 table.
#   FECS signature getter: 382.33 +0x24 (GP104/GP107 use +0x2C).
#   GPCCS signature getter: 382.33 +0x20 (GP104/GP107 use +0x28).
#   GR bundle getter: 382.33 +0x420 (GP107 +0x428); XP GR fields are 0x40 lower,
#   so XP +0x3E0 (GP107 +0x3E8).
.macro delta reg
 call 991f
991: pop \reg
 sub \reg, OFFSET FLAT:991b
.endm
.macro address reg, symbol
 delta \reg
 add \reg, OFFSET FLAT:\symbol
.endm
.macro set_callback off, symbol
 lea eax,[ebx+\symbol]
 mov [esi+\off],eax
.endm

# Replaces the CALL at 0x46F7AA (GP106 registration -> register_gp107). GP107
# registration runs first and its status is preserved; GP108 is appended after
# it succeeds, reusing the runtime-built GP107 family table.
register_gp108:
 call register_gp107
 test eax,eax
 jnz 9f
 push ebx
 push esi
 push edi
 delta ebx
 lea esi,[ebx+family_table]
 lea edi,[ebx+gp108_table]
 mov ecx,82
 rep movsd
 lea esi,[ebx+gp108_table]
 # 382.33 GP107/GP108 use the GP102/GP106 secure-boot (ACR) object in slot 0,
 # not GP104's (which XP's GP107 table copies).
 lea edx,[ebx+original_gp106_table]
 mov eax,[edx]
 mov [esi],eax
 set_callback 0x48,gp108_fecs
 set_callback 0x64,gp108_gpccs
 set_callback 0x74,gp108_gr
 .irp pair,fecs108,gpccs108,gr108
 lea eax,[ebx+\pair\()_payload]
 mov [ebx+\pair\()_descriptor+4],eax
 .endr
 push esi
 push 0x3c
 call register_family
 pop edi
 pop esi
 pop ebx
9: ret

gp108_fecs:
 push ebx
 push esi
 mov esi,[esp+16]
 push esi
 push dword ptr [esp+16]
 call original_gp104_fecs
 delta ebx
 set_callback 0x24,get_fecs108
 set_callback 0x2c,null_getter
 pop esi
 pop ebx
 ret 8

gp108_gpccs:
 push ebx
 push esi
 mov esi,[esp+16]
 push esi
 push dword ptr [esp+16]
 call original_gp104_gpccs
 delta ebx
 set_callback 0x20,get_gpccs108
 set_callback 0x28,null_getter
 pop esi
 pop ebx
 ret 8

# GP107's GR constructor (GP104 base + GP107 attrib/bundle/gfxp/caps sizes);
# 382.33 GP108 changes only the bundle getter relative to GP107.
gp108_gr:
 push ebx
 push esi
 mov esi,[esp+16]
 push esi
 push dword ptr [esp+16]
 call gp107_gr
 delta ebx
 set_callback 0x3e0,get_gr108
 set_callback 0x3e8,null_getter
 pop esi
 pop ebx
 ret 8

get_fecs108:
 address eax,fecs108_descriptor
 ret 4
get_gpccs108:
 address eax,gpccs108_descriptor
 ret 4
get_gr108:
 address eax,gr108_descriptor
 ret 4

.balign 16
gp108_table: .zero 0x148
fecs108_descriptor: .long 192,0,0
gpccs108_descriptor: .long 192,0,0
gr108_descriptor: .long gr108_payload_end-gr108_payload,0,0
.balign 16
fecs108_payload: .incbin "fecs-signature.bin"
gpccs108_payload: .incbin "gpccs-signature.bin"
gr108_payload: .incbin "gr-bundle.bin"
gr108_payload_end:
# 382.33 secure-boot (ACR) set for GP102/GP106/GP107/GP108 (slot 0 table
# 0xBCE090). patch_gp108.py points XP's existing ACR 0-5 descriptors here.
.balign 16
acr0_payload: .incbin "acr0.bin"
.balign 16
acr1_payload: .incbin "acr1.bin"
.balign 16
acr2_payload: .incbin "acr2.bin"
.balign 16
acr3_payload: .incbin "acr3.bin"
.balign 16
acr4_payload: .incbin "acr4.bin"
.balign 16
acr5_payload: .incbin "acr5.bin"
.section .note.GNU-stack,"",@progbits
