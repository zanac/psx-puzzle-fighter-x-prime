; ============================================================================
; FILE TABLE (new files on the disc)
; The game loads files by id through a table of LBAs at 0x80165CC0
; (0x54 files, then the two CD-DA tracks at ids 0x54/0x55). It has no room
; to grow, so it moves to 0x801548C8: a 512-byte function that nothing
; references and that never runs (coverage over boot, menus, Versus,
; Arcade and Street Puzzle). tools/discexpand.py builds the new table: the
; original LBAs, the CD-DA LBAs moved after the grown data track, and the
; new files (ids 0x56, 0x57, ...). Its two readers are repointed:
;   0x801044A8  file loader (id at +0x304)
;   0x801063A4  XA music player
; ============================================================================

XP_FILES equ 0x801548C8

.org XP_FILES
.area 0x80154AC8 - XP_FILES, 0
	.incbin XP_TABLE
.endarea

.org 0x801044A8
	lui     at, hi(XP_FILES)
	addiu   at, at, lo(XP_FILES)
.org 0x801063A4
	lui     at, hi(XP_FILES)
	addiu   at, at, lo(XP_FILES)
