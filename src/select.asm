; ============================================================================
; PLAYER SELECT: ZANGIEF AND DAN ON THEIR OWN ICONS
; In Versus and Arcade (XP_ZOKN == 3) the grid gets a third row on top, two
; cells over Chun-Li and Sakura: Zangief (cursor position 8) and Dan (9).
; To make room the PLAYER SELECT logo goes up three text rows and the two
; select timers move one column outwards.
; ============================================================================

; ---- logo: the tile script (0x8016FACC) starts at column 15, row 5 -> row 2
.org 0x8016FACC
	.halfword 0xC3C2
; Arcade's "STAGE n" / "FINAL STAGE" replace the logo (0x8013CA98: erase,
; then their scripts): the same three rows up, and the erase (0x8013CB38,
; 16 blank columns at column 15, rows 5-12) now covers rows 2-11
.org 0x8016FBE0                         ; STAGE
	.halfword 0xC442
.org 0x8016FDD8                         ; FINAL / STAGE
	.halfword 0xC442
.org 0x8016FE42
	.halfword 0xC446
.org 0x8016FC4C                         ; the digits 1-9
	.halfword 0xC546
.org 0x8016FC78
	.halfword 0xC546
.org 0x8016FCA4
	.halfword 0xC546
.org 0x8016FCD0
	.halfword 0xC546
.org 0x8016FCFC
	.halfword 0xC546
.org 0x8016FD28
	.halfword 0xC546
.org 0x8016FD54
	.halfword 0xC546
.org 0x8016FD80
	.halfword 0xC546
.org 0x8016FDAC
	.halfword 0xC546
.org 0x8013CB60
	addiu   a1, s0, 2               ; rows 2, 4, 6, 8, 10 (2-line font)
.org 0x8013CB68
	slti    v0, s0, 10

; ---- select timers (0x8013C428 prints, 0x8013C4B4 erases): P1 one column
; to the left, P2 one column to the right
.org 0x8013C454
	ori     a0, zero, 0x1B
.org 0x8013C470
	ori     a0, zero, 0x1B
.org 0x8013C474
	ori     a0, zero, 0xD
.org 0x8013C48C
	ori     a0, zero, 0xD
.org 0x8013C4E0
	ori     a0, zero, 0xE
.org 0x8013C4E4
	ori     a0, zero, 0x1C

; ---- the two new icons -------------------------------------------------------
; The grid icons are type 0x17 objects, subtype = character 0-7, made by
; 0x8013C29C (8 calls to 0x80114260(subtype, mode)); their init (0x80113F2C)
; reads per subtype a delay, a position and an animation. Subtypes 8
; (Zangief) and 9 (Dan) are added in Versus / Arcade, with 10-entry copies
; of the delay and position tables and their own animations (a blank frame,
; then the icon: the same 2-step script as the others, 0x80167A84 + 16 * char).
; Icon tile lists (as 0x801667C4 + 0x94 * char): 9 16x16 tiles of the
; picture on the icon page (FIRST.EMI entry 25, VRAM 704,0), (u << 8 | v, x,
; y, attr) with v counted upwards, then the 9 tiles of the white frame (its
; navy inside shows through the picture's 0 pixels), then 0xFFFF, 5.
; Dan: his laughing variant at (0,96) (one of the FINAL STAGE gag icons),
; with its two top-right tiles replaced by copies clipped to the frame's
; inside (strip slots 9-10: his ponytail crosses the frame there).
; Zangief: Pocket Fighter's grid icon, written at build time as 9 loose
; tiles in the page's empty right-hand strip, x 240, y 0-143 (tools/
; zangief.py icon: picture tile column c, row r at y = 16 * (3r + c)); the
; page's own pictures, Dan's gag variants included, are untouched. Both use
; Dan's icon palette (10).
ICON_ATTR equ 0x20 | 10                 ; zangief.py ICON_PAL

.macro xp_frame
	; the frame (icon 20 at 0,192), palette 11, as in every list
	.halfword 0x00E0, 0x00, 0x00, 0x2B
	.halfword 0x10E0, 0x10, 0x00, 0x2B
	.halfword 0x20E0, 0x20, 0x00, 0x2B
	.halfword 0x00D0, 0x00, 0x10, 0x2B
	.halfword 0x10D0, 0x10, 0x10, 0x2B
	.halfword 0x20D0, 0x20, 0x10, 0x2B
	.halfword 0x00C0, 0x00, 0x20, 0x2B
	.halfword 0x10C0, 0x10, 0x20, 0x2B
	.halfword 0x20C0, 0x20, 0x20, 0x2B
	.halfword 0xFFFF, 5
.endmacro



; 0x801609C0, 0x80161170, 0x801653C0, 0x80163574, 0x80160FF4: functions with no
; references that never run (coverage: boot, menus, Versus with RESULT,
; Arcade to the HARD finale, Street Puzzle, option menus)
.org 0x801609C0
.area 0x80160AD4 - 0x801609C0, 0
xp_icon_zangief:                        ; list y counts up: y 0 = bottom row (r 2)
	.halfword 0xF000 | 0x60, 0x00, 0x00, ICON_ATTR
	.halfword 0xF000 | 0x70, 0x10, 0x00, ICON_ATTR
	.halfword 0xF000 | 0x80, 0x20, 0x00, ICON_ATTR
	.halfword 0xF000 | 0x30, 0x00, 0x10, ICON_ATTR
	.halfword 0xF000 | 0x40, 0x10, 0x10, ICON_ATTR
	.halfword 0xF000 | 0x50, 0x20, 0x10, ICON_ATTR
	.halfword 0xF000 | 0x00, 0x00, 0x20, ICON_ATTR
	.halfword 0xF000 | 0x10, 0x10, 0x20, ICON_ATTR
	.halfword 0xF000 | 0x20, 0x20, 0x20, ICON_ATTR
	xp_frame
.align 4
xp_iconscr:                             ; subtype 8, 9: blank frame, then the icon
	.word   0x80166D8C, 1, xp_icon_zangief, 0x81
	.word   0x80166D8C, 1, xp_icon_dan, 0x81
.endarea

.org 0x80161170
.area 0x80161208 - 0x80161170, 0
xp_icon_dan:                            ; (0,96), top-right tiles from the strip
	.halfword (0x00 << 8) | 0x80, 0x00, 0x00, ICON_ATTR
	.halfword (0x10 << 8) | 0x80, 0x10, 0x00, ICON_ATTR
	.halfword (0x20 << 8) | 0x80, 0x20, 0x00, ICON_ATTR
	.halfword (0x00 << 8) | 0x70, 0x00, 0x10, ICON_ATTR
	.halfword (0x10 << 8) | 0x70, 0x10, 0x10, ICON_ATTR
	.halfword (0x20 << 8) | 0x70, 0x20, 0x10, ICON_ATTR
	.halfword (0x00 << 8) | 0x60, 0x00, 0x20, ICON_ATTR
	.halfword 0xF000 | 0x90, 0x10, 0x20, ICON_ATTR
	.halfword 0xF000 | 0xA0, 0x20, 0x20, ICON_ATTR
	xp_frame
.endarea

.org 0x801653C0
.area 0x801654AC - 0x801653C0, 0
xp_icondelay:                           ; 0x8016A840 + Zangief, Dan
	.byte   76, 64, 60, 72, 80, 84, 88, 68, 92, 96
.align 4
; the whole grid sits GRID_DY pixels lower than in vanilla, for some room
; between the logo (which cannot go higher: row 1 is off the visible top)
; and the new row
GRID_DY equ 4
xp_iconpos:                             ; 0x8016A850 (x, y; y up) + Zangief, Dan
	.halfword 88, -112-GRID_DY, 136, -64-GRID_DY, 88, -64-GRID_DY, 232, -64-GRID_DY
	.halfword 136, -112-GRID_DY, 184, -112-GRID_DY, 232, -112-GRID_DY, 184, -64-GRID_DY
	.halfword 136, -16-GRID_DY, 184, -16-GRID_DY
xp_cursorxy:                            ; 0x8016A974 + positions 8 (Zangief), 9 (Dan)
	.halfword 84, 136-GRID_DY, 132, 136-GRID_DY, 180, 136-GRID_DY, 228, 136-GRID_DY
	.halfword 84, 88-GRID_DY, 132, 88-GRID_DY, 180, 88-GRID_DY, 228, 88-GRID_DY
	.halfword 132, 184-GRID_DY, 180, 184-GRID_DY
xp_cursorchars:                         ; CURSOR_CHARS + positions 8, 9
	.byte   2, 1, 7, 3, 0, 4, 5, 6, ZG_CHAR, ZG_CHAR
.align 4

; spawn (end of 0x8013C29C, s0 = mode, its frame still on the stack): the
; two extra icons on the Versus / Arcade select screen (mode 3)
xp_icons:
	lui     v0, hi(XP_ZOK)             ; Versus / Arcade, Arcade challenge included
	lbu     at, lo(XP_ZOK)(v0)
	lbu     v0, lo(XP_ZOKN)(v0)
	nop
	or      v0, v0, at
	li      v1, 3
	bne     v0, v1, @@ret
	nop
	bne     s0, v1, @@ret           ; mode 3 only: the select screen (mode 1 is
	li      a0, 8                   ; Arcade's STAGE screen, its "?" cards)
	jal     0x80114260
	move    a1, s0
	li      a0, 9
	jal     0x80114260
	move    a1, s0
@@ret:
	lw      ra, 0x14(sp)
	lw      s0, 0x10(sp)
	jr      ra
	addiu   sp, sp, 0x18

; icon init (0x80113FE4, was jal 0x8010B734): subtypes 8 and 9 take their
; own script; a0 = object, a1 = animation
xp_iconanim:
	lb      v0, 3(a0)
	nop
	addiu   v0, v0, -8
	bltz    v0, @@vanilla
	sll     v0, v0, 4
	la      a1, xp_iconscr
	j       0x8010B778              ; +0x28 = script, +0x12 = its duration
	addu    a1, a1, v0
@@vanilla:
	j       0x8010B734
	nop
.endarea

.org 0x80113F60                         ; delay
	lui     at, hi(xp_icondelay)
	addiu   at, at, lo(xp_icondelay)
.org 0x80113F8C                         ; x
	lui     at, hi(xp_iconpos)
	addiu   at, at, lo(xp_iconpos)
.org 0x80113FA4                         ; y
	lui     at, hi(xp_iconpos + 2)
	addiu   at, at, lo(xp_iconpos + 2)
.org 0x80113FE4
	jal     xp_iconanim
.org 0x8013C310
	j       xp_icons
	nop

; cursor and badge position, per cursor position (0x80116140)
.org 0x80116150
	lui     at, hi(xp_cursorxy)
	addiu   at, at, lo(xp_cursorxy)
.org 0x8011618C
	lui     at, hi(xp_cursorxy)
	addiu   at, at, lo(xp_cursorxy)
.org 0x801161B8
	lui     at, hi(xp_cursorxy + 2)
	addiu   at, at, lo(xp_cursorxy + 2)

; ---- cursor movement (xp_move, CHARACTER SELECT in xprime.asm) ---------------
; Versus / Arcade: Up from Chun-Li (position 1) / Sakura (2) goes to Zangief
; (8) / Dan (9); from there Down comes back, Left / Right swap the two. Dan
; and Zangief leave the Down ring: Devilot -> Akuma -> Mei-Ling -> Anita ->
; cell character (Up walks it back). Elsewhere (Street Puzzle) the ring keeps
; Dan as before.
.org 0x80163574
.area 0x80163644 - 0x80163574, 0

; (XP_ZOK | XP_ZOKN is 3 in Versus and Arcade: XP_ZOKN alone is 0 on the
; select screen of an Arcade challenge, where MODE_NEXT stays 0)

; xp_selchk: t0 = cursor position, a1 = pad (masked in the delay slot)
xp_selchk:
	sltiu   v0, t0, 8
	beqz    v0, @@top
	nop
	j       xp_mv_dir               ; the grid: as before
	li      v0, 0x1000
@@top:
	li      v0, 0x4000              ; down
	beq     a1, v0, @@down
	li      v0, 0x8000              ; left
	beq     a1, v0, @@swap
	li      v0, 0x2000              ; right
	bne     a1, v0, xp_mv_ret_t
	nop
@@swap:
	j       xp_mv_moved
	xori    t1, t0, 1               ; 8 <-> 9
@@down:
	j       xp_mv_moved
	addiu   t1, t0, -7              ; 8 -> 1, 9 -> 2
xp_mv_ret_t:
	j       xp_mv_ret
	nop

; xp_up_top: Up on the grid's top row (t0 = position)
xp_up_top:
	addiu   v0, t0, -1
	sltiu   v0, v0, 2               ; Chun-Li or Sakura?
	beqz    v0, @@vanilla
	lui     v0, hi(XP_ZOK)             ; Versus / Arcade, Arcade challenge included
	lbu     at, lo(XP_ZOK)(v0)
	lbu     v0, lo(XP_ZOKN)(v0)
	nop
	or      v0, v0, at
	nop
	xori    v0, v0, 3
	bnez    v0, @@vanilla
	nop
	j       xp_mv_moved
	addiu   t1, t0, 7
@@vanilla:
	j       xp_mv_updown
	nop

; xp_cellchar: t2 = the character of cursor position t0; position 8 is
; Zangief (t1 = ZG_MAGIC: xp_zg_apply sets his bit)
xp_cellchar:
	li      v0, 8
	bne     t0, v0, @@char
	nop
	li      t1, ZG_MAGIC
@@char:
	la      v0, xp_cursorchars
	addu    v0, v0, t0
	j       xp_mv_apply
	lbu     t2, 0(v0)
.endarea

.org 0x80160FF4
.area 0x801610B8 - 0x80160FF4, 0
; xp_ringnext: Down on a secret character, t2 = the next one; Akuma -> Dan
; becomes Akuma -> Mei-Ling in Versus / Arcade
xp_ringnext:
	li      v0, ZG_CHAR
	bne     t2, v0, @@apply
	lui     v0, hi(XP_ZOK)             ; Versus / Arcade, Arcade challenge included
	lbu     at, lo(XP_ZOK)(v0)
	lbu     v0, lo(XP_ZOKN)(v0)
	nop
	or      v0, v0, at
	nop
	xori    v0, v0, 3
	bnez    v0, @@apply
	nop
	li      t2, 4                   ; Mei-Ling: Hsien-Ko + her bit
	move    t3, t5
@@apply:
	j       xp_mv_apply
	nop

; xp_ringprev: Up on Mei-Ling (t2 = ZG_CHAR): Dan, or Akuma in Versus / Arcade
xp_ringprev:
	lui     v0, hi(XP_ZOK)             ; Versus / Arcade, Arcade challenge included
	lbu     at, lo(XP_ZOK)(v0)
	lbu     v0, lo(XP_ZOKN)(v0)
	nop
	or      v0, v0, at
	nop
	xori    v0, v0, 3
	bnez    v0, @@apply
	nop
	li      t2, 9                   ; Akuma
@@apply:
	j       xp_mv_apply
	nop
.endarea

; ---- big portrait: Dan <-> Zangief ----------------------------------------
; The select portrait object (0x80114510) redraws only when the player's
; character differs from the one it shows (+0x58). Dan and Zangief are both
; character 10, and now sit side by side: the shown value becomes a key,
; character | 0x10 for Zangief, so moving between the two redraws it.
; 0x801618A4 (132 bytes): a function with no references that never runs.
.org 0x801618A4
.area 0x80161928 - 0x801618A4, 0
; v0 = key of portrait object s0 (+3: side) for character s1. Leaf: v0, at, t8.
xp_pkey:
	andi    v0, s1, 0xFF
	li      at, ZG_CHAR
	bne     v0, at, @@ret
	lui     at, hi(XP_ZOK)             ; Versus / Arcade, Arcade challenge included
	lbu     t8, lo(XP_ZOK)(at)
	lbu     at, lo(XP_ZOKN)(at)
	nop
	or      at, at, t8
	nop
	xori    at, at, 3
	bnez    at, @@ret
	lui     at, hi(XP_ZBITS)
	lbu     at, lo(XP_ZBITS)(at)
	lb      t8, 3(s0)
	nop
	srlv    at, at, t8
	andi    at, at, 1
	sll     at, at, 4
	or      v0, v0, at
@@ret:
	jr      ra
	nop

; compare (0x801145A8, was lb v0, 0x58(s0); the delay slot sets v1 = s1):
; v0 = v1 when the key is unchanged (the caller's beq skips), else -1
xp_portcmp:
	move    t9, ra
	jal     xp_pkey
	nop
	lb      at, 0x58(s0)
	move    ra, t9
	bne     at, v0, @@diff
	nop
	jr      ra
	move    v0, v1
@@diff:
	jr      ra
	li      v0, -1

.endarea

; 0x80152D60 (128 bytes): a function with no references that never runs
.org 0x80152D60
.area 0x80152DE0 - 0x80152D60, 0
; xp_samechar: confirming a character the other player already has gives
; the second one the other colour set (0x8013B058). Dan and Zangief are
; both character 10: unless both are Zangief or both Dan, they count as
; different. Replaces "lb v1, 0x74(s1)" at 0x8013B05C (a0 = the other
; player's character, s0 / s1 = other / this select struct). Out: v1 =
; this character, or -1. Keeps v0 (the colour set). Uses at, t0-t2.
xp_samechar:
	lb      v1, 0x74(s1)
	li      at, ZG_CHAR
	bne     v1, at, @@ret
	nop
	bne     a0, at, @@ret
	lui     t0, hi(XP_ZOK)             ; Versus / Arcade, Arcade challenge included
	lbu     t1, lo(XP_ZOK)(t0)
	lbu     t0, lo(XP_ZOKN)(t0)
	nop
	or      t0, t0, t1
	nop
	xori    t0, t0, 3
	bnez    t0, @@ret
	lui     t0, hi(XP_ZBITS)
	lbu     t0, lo(XP_ZBITS)(t0)
	lb      t1, 0x73(s0)
	lb      t2, 0x73(s1)
	srlv    t1, t0, t1
	srlv    t2, t0, t2
	xor     t1, t1, t2
	andi    t1, t1, 1
	beqz    t1, @@ret
	nop
	li      v1, -1
@@ret:
	jr      ra
	nop

; store (0x801145F0: j 0x80114628 / sb s1, 0x58(s0)): the key
xp_portstore:
	jal     xp_pkey
	nop
	j       0x80114628
	sb      v0, 0x58(s0)
.endarea

.org 0x801145A8
	jal     xp_portcmp
.org 0x801145F0
	j       xp_portstore
	nop

.org 0x8013B05C
	jal     xp_samechar             ; (delay slot: nop)
