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

; ============================================================================
; In-match graphics and animations (step 3)
; Zangief's file PL0B_OBJ.EMI (built by tools/zangief.py from Pocket
; Fighter) replaces Dan's PL9A when the player is Zangief. Its record entry
; (loaded at the player's record bank) also holds his palette block and his
; state list + animation scripts, at fixed offsets.
; Code space: 0x80151AC0, a 440-byte function with no references that never
; runs (same coverage as above).
; ============================================================================
ZG_FILE   equ 0x56              ; first file of XP_NEWFILES (build.sh)
ZG_GROUP  equ 11                ; "loaded file" cache value for Zangief
ZG_PALOFF equ 0x2C00            ; tools/zangief.py PALOFF
ZG_LISTOFF equ 0x2F00           ; tools/zangief.py LISTOFF
BANK_P1   equ 0x800E7600
BANK_P2   equ 0x800EBB00

.org 0x80151AC0
.area 0x1B8, 0

; character file load (0x8010BB1C): a0 = player 0/1, s0 = its character
; byte, s1 = its "loaded file" cache byte. Same logic as the vanilla code
; (group table 0x80169E14, file table 0x80169DE8), plus Zangief.
xp_zload:
	li      t1, 1
	sllv    t1, t1, a0              ; player bit
	lb      a0, 0(s0)
	lb      v1, 0(s1)
	la      at, 0x80169E14
	addu    at, at, a0
	lb      v0, 0(at)               ; group
	sll     t0, a0, 2
	la      at, 0x80169DE8
	addu    at, at, t0
	lw      t0, 0(at)               ; file id
	li      at, ZG_CHAR
	bne     a0, at, @@cmp
	lui     at, hi(XP_ZBITS)
	lbu     at, lo(XP_ZBITS)(at)
	nop
	and     at, at, t1
	beqz    at, @@cmp
	nop
	li      v0, ZG_GROUP
	li      t0, ZG_FILE
@@cmp:
	beq     v1, v0, @@done
	sb      v0, 0(s1)
	jal     0x801043C0
	move    a0, t0
@@done:
	j       0x8010BB78
	nop

; is the object s1 / a0 Zangief? Inline test used by the two hooks below:
; obj+0x74 = character, obj+0x73 = side (0 P1, 1 P2).

; animation state start (0x80136430 and 0x801364DC): v0 = the character's
; state list, a1 = state * 4, s1 = object. Out: s0 = script pointer.
; Leaf; keeps a0 (the object), uses at, v0, v1, t8, t9.
xp_zstate:
	addu    t9, v0, a1
	lw      s0, 0(t9)               ; vanilla
	lb      v0, 0x74(s1)
	li      at, ZG_CHAR
	bne     v0, at, @@ret
	lb      t8, 0x73(s1)
	li      v1, 1
	sllv    v1, v1, t8
	lui     at, hi(XP_ZBITS)
	lbu     at, lo(XP_ZBITS)(at)
	nop
	and     at, at, v1
	beqz    at, @@ret
	addiu   v1, a1, -23 * 4         ; 23/24: select-screen poses stay Dan's
	sltiu   v1, v1, 8
	bnez    v1, @@ret
	li      v1, BANK_P1
	beqz    t8, @@bank
	nop
	li      v1, BANK_P2
@@bank:
	addu    t9, v1, a1
	lw      t9, ZG_LISTOFF(t9)
	nop
	addu    s0, v1, t9
	sltiu   at, a1, 3 * 4           ; states 0-2: coming from a hit?
	beqz    at, @@ret
	lw      t8, 0x28(s1)            ; current script
	lw      t9, ZG_LISTOFF + 54 * 4(v1)
	nop
	addu    t9, t9, v1              ; hit scripts start
	sltu    at, t8, t9
	bnez    at, @@ret
	lw      t9, ZG_LISTOFF + 55 * 4(v1)
	nop
	addu    t9, t9, v1              ; hit scripts end
	sltu    at, t8, t9
	beqz    at, @@ret
	addu    t9, v1, a1
	lw      t9, ZG_LISTOFF + 51 * 4(t9)     ; hit tail for this state
	nop
	addu    s0, v1, t9
@@ret:
	jr      ra
	nop

; palette upload (0x80136860, in 0x80136824): a0 = object, v1 = palette
; pool 0x800F8440. Out: a0 = source of the 4 palettes. Leaf; keeps a1-a3.
xp_zpal:
	lb      v0, 0x74(a0)
	lb      t9, 0x79(a0)            ; colour set
	lb      t8, 0x73(a0)            ; side
	sll     t9, t9, 7
	li      at, ZG_CHAR
	bne     v0, at, @@vanilla
	li      at, 1
	sllv    at, at, t8
	lui     a0, hi(XP_ZBITS)
	lbu     a0, lo(XP_ZBITS)(a0)
	nop
	and     at, at, a0
	beqz    at, @@vanilla
	li      a0, BANK_P1 + ZG_PALOFF
	beqz    t8, @@zg
	nop
	li      a0, BANK_P2 + ZG_PALOFF
@@zg:
	jr      ra
	addu    a0, a0, t9
@@vanilla:
	sll     v0, v0, 9
	addu    a0, v0, t9
	jr      ra
	addu    a0, a0, v1

.endarea

; ---- voices (step 4) ----
; voice bank load (0x801058D0, a0 = player): Zangief loads SE_PL0B.EMI
; (second new file) with his own "loaded bank" cache value. Code space:
; 0x8015C550, a 380-byte function with no references that never runs.
ZG_SEFILE equ 0x57
ZG_SEGROUP equ 0x20              ; voice cache value (11 is the cache's "none")
.org 0x8015C550
.area 0x17C, 0
; replaces 0x8010594C-0x80105980: s0 = character (maybe already 9 for the
; vanilla Dan -> Akuma voice case), s1 = cache byte, a1 = bank descriptor
xp_zse:
	li      at, 1
	sllv    at, at, a0
	lui     v0, hi(XP_ZBITS)
	lbu     v0, lo(XP_ZBITS)(v0)
	nop
	and     v0, v0, at
	beqz    v0, @@cache
	li      v1, 0x801AE568          ; P1 character
	beqz    a0, @@char
	nop
	li      v1, 0x801AE814          ; P2 character
@@char:
	lb      v1, 0(v1)
	li      at, ZG_CHAR
	bne     v1, at, @@cache
	nop
	li      s0, ZG_SEGROUP
@@cache:
	lb      v0, 0(s1)
	nop
	beq     v0, s0, @@done
	nop
	jal     0x80105760
	move    a0, a1
	li      at, ZG_SEGROUP
	beq     s0, at, @@load
	li      a0, ZG_SEFILE
	sll     v0, s0, 2
	la      at, 0x80165FE0
	addu    at, at, v0
	lw      a0, 0(at)
@@load:
	jal     0x801043C0
	nop
	j       0x80105980
	nop
@@done:
	j       0x80105984
	nop
; palette reload between rounds (0x80107430): both players' palettes are
; uploaded from the player structs. Wraps the two "jal 0x80108C68": a2 =
; 0xC for P1, 0x10 for P2, a0 = the vanilla source. Uses v0, v1, at.
xp_zpal2:
	li      v1, 0x801AE568          ; P1 struct + 0x68 (character)
	li      at, 1
	xori    v0, a2, 0xC
	beqz    v0, @@side
	nop
	li      v1, 0x801AE814          ; P2
	li      at, 2
@@side:
	lui     v0, hi(XP_ZBITS)
	lbu     v0, lo(XP_ZBITS)(v0)
	nop
	and     v0, v0, at
	beqz    v0, @@go
	nop
	lb      v0, 0(v1)
	nop
	xori    v0, v0, ZG_CHAR
	bnez    v0, @@go
	nop
	lb      v0, 5(v1)               ; colour set (struct + 0x6D)
	li      a0, BANK_P1 + ZG_PALOFF
	xori    at, at, 1
	beqz    at, @@set
	nop
	li      a0, BANK_P2 + ZG_PALOFF
@@set:
	sll     v0, v0, 7
	addu    a0, a0, v0
@@go:
	j       0x80108C68
	nop
.endarea

; code space: 0x80155008, a 340-byte function with no references that never runs
.org 0x80155008
.area 0x154, 0
; special palettes (0x80136908 burnt, 0x80136990 frozen): wraps their
; "jal 0x80108C68". v1 = object, a0 = vanilla source (char 10: burnt
; 0x800FA8C0, frozen 0x800FA920). Zangief's are in his bank at PALOFF+0x200.
xp_zpal3:
	lb      v0, 0x74(v1)
	li      at, ZG_CHAR
	bne     v0, at, @@go
	lb      t8, 0x73(v1)
	li      at, 1
	sllv    at, at, t8
	lui     v0, hi(XP_ZBITS)
	lbu     v0, lo(XP_ZBITS)(v0)
	nop
	and     v0, v0, at
	beqz    v0, @@go
	li      t9, 0x800FA920
	li      v0, 0
	bne     a0, t9, @@side
	nop
	li      v0, 0x60
@@side:
	li      a0, BANK_P1 + ZG_PALOFF + 0x200
	beqz    t8, @@add
	nop
	li      a0, BANK_P2 + ZG_PALOFF + 0x200
@@add:
	addu    a0, a0, v0
@@go:
	j       0x80108C68
	nop
.endarea

; hooks only when the build has Zangief's file (XP_PF in build.sh);
; otherwise he keeps Dan's in-match look
.if ZG_HAVE
.org 0x8010BB1C
	j       xp_zload
	nop

.org 0x80136430
	jal     xp_zstate
	sra     a1, a1, 0xE
	nop
.org 0x801364DC
	jal     xp_zstate
	sra     a1, a1, 0xE
	nop

.org 0x80136860
	jal     xp_zpal
	nop
	jal     0x80108C68
	nop
	nop
	nop
	nop
.org 0x8010594C
	j       xp_zse
	nop
.org 0x8010746C
	jal     xp_zpal2
.org 0x8010749C
	jal     xp_zpal2
.org 0x801368F0
	jal     xp_zpal2                ; palette from the player struct
.org 0x80136978
	jal     xp_zpal3
.org 0x80136A00
	jal     xp_zpal3
.endif
