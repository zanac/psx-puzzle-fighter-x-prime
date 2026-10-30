; ============================================================================
; ZANGIEF (hidden character, Versus only)
; Zangief is Dan's slot (10) plus his own per-player bit in XP_ZBITS, the
; same way Mei-Ling / Anita are Hsien-Ko / Donovan plus a bit. He is only
; real in Versus: every test also checks the game mode.
;   select:  Down cycles ... Mei-Ling -> Anita -> Zangief -> cell character,
;            Up walks back (Zangief -> Anita); Arcade skips him
;   pattern: "Siberian Bear" (XP_ZPATTERN), via the pattern lookup 0x801350E4
;   damage:  index 11 in DMGTAB (send 90 %, receive 90 %), via xp_zchar
; Code space: 0x80163CDC, a 684-byte function with no references that never
; runs (coverage over boot, menus, Versus, Arcade, Street Puzzle).
; ============================================================================

; (ZG_CHAR, P1_STRUCT, ZG_MAGIC are defined at the top of xprime.asm)

.org 0x80163CDC
.area 684, 0

; xp_zbit: v1 = this player's Zangief bit if the mode is Versus, else 0.
; In: t5 = player bit. Leaf, v1 only.
xp_zbit:
	lui     v1, hi(MODE_NEXT)
	lbu     v1, lo(MODE_NEXT)(v1)
	nop
	xori    v1, v1, 3
	bnez    v1, @@no
	lui     v1, hi(XP_ZBITS)
	lbu     v1, lo(XP_ZBITS)(v1)
	jr      ra
	and     v1, v1, t5
@@no:
	jr      ra
	move    v1, zero

; ---- cursor movement pieces (jumped to from xp_move, see CHARACTER SELECT) ----
; Dan on the bottom row, Down: Zangief -> cell character, Dan -> Mei-Ling.
xp_zg_dan:
	jal     xp_zbit
	nop
	bnez    v1, @@zangief
	nop
	j       xp_mv_apply             ; Dan -> Mei-Ling (t3 = t5 already)
	li      t2, 4
@@zangief:
	j       xp_mv_cell
	move    t3, zero

; Anita, Down: Zangief in Versus, else the cell character.
xp_zg_anita:
	lui     v1, hi(MODE_NEXT)
	lbu     v1, lo(MODE_NEXT)(v1)
	li      v0, 3
	bne     v1, v0, @@cell
	li      t2, ZG_CHAR
	move    t3, zero
	move    t9, zero
	j       xp_mv_apply
	li      t1, ZG_MAGIC
@@cell:
	j       xp_mv_cell
	nop

; head of the apply step: Mei-Ling bits (the two replaced instructions), then
; the Zangief bit: cleared, or set when t1 = ZG_MAGIC
xp_zg_apply:
	and     t7, t7, t6
	or      t7, t7, t3
	lui     v1, hi(XP_ZBITS)
	lbu     v0, lo(XP_ZBITS)(v1)
	nop
	and     v0, v0, t6
	li      at, ZG_MAGIC
	bne     t1, at, @@store
	nop
	or      v0, v0, t5
@@store:
	sb      v0, lo(XP_ZBITS)(v1)
	j       xp_mv_apply + 8
	nop

; ---- is this player Zangief? (match side) ----
; xp_zchar: t7 = character of the player struct t6, or 11 for Zangief.
; Used by the damage routine (DMGTAB index 11). Leaf: t7, t8 only.
xp_zchar:
	lbu     t7, 0x68(t6)
	li      t8, ZG_CHAR
	bne     t7, t8, @@ret
	lui     t8, hi(MODE)
	lbu     t8, lo(MODE)(t8)
	nop
	xori    t8, t8, 3
	bnez    t8, @@ret               ; not a Versus match
	li      t8, P1_STRUCT
	beq     t6, t8, @@p1
	li      t8, 2
	b       @@test
	nop
@@p1:
	li      t8, 1
@@test:
	lui     t7, hi(XP_ZBITS)
	lbu     t7, lo(XP_ZBITS)(t7)
	nop
	and     t7, t7, t8
	beqz    t7, @@ret
	li      t7, ZG_CHAR
	li      t7, 11
@@ret:
	jr      ra
	nop

; pattern lookup (0x801350E4, a2 = the player whose pattern drops, a1 =
; pattern table + row offset): replaces "lbu v1, 0x68(a2)" at 0x80135110.
; For Zangief, a1 points into his own table and v1 = 0 (no per-char step).
; The function uses no t registers, so t7/t8 are free here.
xp_patchar:
	lbu     v1, 0x68(a2)
	li      t7, ZG_CHAR
	bne     v1, t7, @@done
	nop
	; same tests as xp_zchar, inline (no ra here: this is a leaf caller)
	lui     t7, hi(MODE)
	lbu     t7, lo(MODE)(t7)
	nop
	xori    t7, t7, 3
	bnez    t7, @@done
	li      t7, P1_STRUCT
	beq     a2, t7, @@p1
	li      t8, 2
	b       @@test
	nop
@@p1:
	li      t8, 1
@@test:
	lui     t7, hi(XP_ZBITS)
	lbu     t7, lo(XP_ZBITS)(t7)
	nop
	and     t7, t7, t8
	beqz    t7, @@done
	nop
	la      t7, PATTERNS
	subu    a1, a1, t7              ; row offset
	la      t7, XP_ZPATTERN
	addu    a1, a1, t7
	move    v1, zero
@@done:
	j       0x80135118
	nop

; new game: clear the Zangief bits with the alternate bits (0x80123D80)
xp_alt_reset:
	lui     at, hi(XP_ZBITS)
	j       0x801245DC
	sb      zero, lo(XP_ZBITS)(at)

.endarea

; second area: 0x801639F8-0x80163C24, two more unreferenced functions that
; never run (same coverage)
.org 0x801639F8
.area 0x80163C24 - 0x801639F8, 0

; select-screen name label: key and frame for Zangief (label 13, frame 0x40,
; built by tools/labels.py). xp_labelkey2 replaces xp_labelkey in the two
; per-frame hooks: v1 = character | 0x10 when the player shows an alternate.
; Only t0-t3 are touched, as in xp_labelkey.
xp_labelkey2:
	lb      v1, 0x74(a1)
	li      t2, ZG_CHAR
	bne     v1, t2, @@other
	lb      t0, 0x73(a1)
	lui     t1, hi(MODE_NEXT)
	lbu     t1, lo(MODE_NEXT)(t1)
	li      t2, 3
	bne     t1, t2, @@ret
	lui     t1, hi(XP_ZBITS)
	lbu     t1, lo(XP_ZBITS)(t1)
	nop
	srlv    t1, t1, t0
	andi    t1, t1, 1
	sll     t1, t1, 4
	or      v1, v1, t1
@@ret:
	jr      ra
	nop
@@other:
	j       xp_labelkey             ; Mei-Ling / Anita
	nop

; label setter tail (0x801163DC): key 0x1A (Dan | 0x10) = Zangief
xp_labelframe2:
	lbu     t0, 0x58(a0)
	li      t1, ZG_CHAR | 0x10
	bne     t0, t1, @@other
	srl     t1, a2, 1
	ori     t1, t1, 0x10
	bne     t0, t1, @@done
	li      v1, 0x40
	sw      v1, 0x28(a0)
@@done:
	jr      ra
	nop
@@other:
	j       xp_labelframe
	nop

; Counter Gem preview panel (0x8013B0E8): the panel is a tile script, picked
; from the per-character table 0x8016FA84. Replaces "lui at / addiu at /
; addu at / lw a0" at 0x8013B15C: v0 = character * 4, s0 = panel side
; (0 = P1). Zangief gets XP_ZPREVIEW, his tiles at (152,152) of the preview
; page (drawn by tools/previews.py). Leaf: v0, v1, at, a0.
xp_zpv:
	lui     at, 0x8017
	addu    at, at, v0
	lw      a0, -0x57C(at)
	li      at, ZG_CHAR * 4
	bne     v0, at, @@ret
	lui     v1, hi(XP_ZBITS)
	lbu     v1, lo(XP_ZBITS)(v1)
	beqz    s0, @@p1
	li      at, 1
	li      at, 2
@@p1:
	and     v1, v1, at
	beqz    v1, @@ret
	nop
	la      a0, XP_ZPREVIEW
@@ret:
	jr      ra
	nop

XP_ZPREVIEW:                            ; Dan's script (0x8016FA60), tiles +10
	.halfword 0x4273, 0x4274, 0x4275, 0x4276, 0x4277, 0xF141
	.halfword 0x4293, 0x4294, 0x4295, 0x4296, 0x4297, 0xF141
	.halfword 0x42B3, 0x42B4, 0x42B5, 0x42B6, 0x42B7, 0

.align 4
XP_ZPATTERN:                            ; "Siberian Bear": 3x2 blocks
	pattern4 3,3,3,2,2,2, 3,3,3,2,2,2, 4,4,4,1,1,1, 4,4,4,1,1,1
XP_ZBITS:
	.byte   0                       ; bit 0 P1, bit 1 P2
.endarea

.org 0x80135110
	j       xp_patchar              ; (delay slot: the vanilla nop)

.org 0x80123D80
	jal     xp_alt_reset

.org 0x8013B15C
	jal     xp_zpv
	nop
	jal     0x80108924
	nop
	nop
	nop
