; ============================================================================
; VERSUS RESULT: DAN AND ZANGIEF ALWAYS LISTED, ZANGIEF'S OWN COUNTERS
; The RESULT screen after a Versus match (0x80138864) lists, per character,
; P1's wins and losses and P2's: four arrays of 11 words at 0x801D2678
; (wins side 0, wins side 1, losses side 0, losses side 1; index = the
; character, side = player struct +0x67). The 8 regular characters always
; have a line; Devilot, Akuma and Dan only when unlocked (mask bits 0x100,
; 0x200, 0x400). The counters are saved with the game data on the memory
; card (0x80103E50 builds the 0x400-byte block at 0x80010000, 0x80104054
; reads it back) and cleared by CLEAR RESULT (0x80138808).
; Zangief is Dan's slot plus his bit, so vanilla counted him as Dan. Now:
; - his own four counters (XP_ZST), updated instead of Dan's when his bit
;   is set (xp_zinc replaces the update at 0x801382B8);
; - a 12th line, ZANGIEF; DAN and ZANGIEF are always shown, right under
;   DONOVAN, then AKUMA and DEVILOT when unlocked (12-entry copies of the
;   name, column and line tables);
; - his counters are saved in the unused tail of the save block (+0x380:
;   'ZGST', the 4 words, their sum) and read back with it; a block without
;   them (an older save) gives zero;
; - CLEAR RESULT clears them too;
; - with up to four extra lines the list reaches row 18, so the totals line
;   (WIN / LOSS / TOTAL, row 19) and the menu (CONTINUE / END / CLEAR
;   RESULT, rows 22 / 24 / 26) move down one row.
; Code space: 0x80107B08-0x80107C20, 0x80157AE0-0x80157BAC, 0x80117E8C-
; 0x80117F24, 0x8014E03C-0x8014E0CC and 0x8015ABC4-0x8015AC88, functions
; with no references that never run (coverage: boot, menus, Versus with the
; RESULT screen, a whole Arcade run with staff roll and HARD finale, Street
; Puzzle, option menus).
; ============================================================================
STATS     equ 0x801D2678                ; 4 x 11 words
ZST_SAVE  equ 0x80010380                ; in the save block (0x400 bytes, 0x354 used)
ZST_MAGIC equ 0x5453475A                ; 'ZGST'

.org 0x80107B08
.area 0x80107C20 - 0x80107B08, 0

; RESULT update (0x801382B8): a0 = the [winner, loser] struct pair.
; Winner: wins + 1, loser: losses + 1 (at most 999, as vanilla), Zangief's
; own counters for a player with his bit. Leaf: t0-t9, v0, v1, at.
xp_zinc:
	move    t9, ra
	lw      t0, 0(a0)
	li      t1, STATS
	la      t2, XP_ZST
	jal     @@one
	nop
	lw      t0, 4(a0)
	li      t1, STATS + 0x58
	la      t2, XP_ZST + 8
	jal     @@one
	nop
	jr      t9
	nop
@@one:
	lb      t3, 0x67(t0)                ; side
	lb      t4, 0x68(t0)                ; character
	li      at, ZG_CHAR
	bne     t4, at, @@arr
	sll     t5, t3, 2
	la      at, XP_ZBITS
	lbu     at, 0(at)
	nop
	srlv    at, at, t3
	andi    at, at, 1
	beqz    at, @@arr
	nop
	b       @@inc
	addu    t5, t2, t5                  ; Zangief: his counter
@@arr:
	sll     t6, t3, 1                   ; side * 44
	addu    t6, t6, t3
	sll     t6, t6, 2
	subu    t6, t6, t3
	sll     t6, t6, 2
	addu    t5, t1, t6
	sll     t4, t4, 2
	addu    t5, t5, t4
@@inc:
	lw      v0, 0(t5)
	nop
	addiu   v0, v0, 1
	slti    at, v0, 1000
	bnez    at, @@st
	nop
	li      v0, 999
@@st:
	jr      ra
	sw      v0, 0(t5)
.endarea

.org 0x80157AE0
.area 0x80157BAC - 0x80157AE0, 0

; RESULT list, top of the per-line loop (0x80138A04, was lw t0, 0x30(sp)):
; t0 = the line mask with DAN and ZANGIEF always on; DEVILOT moves up to
; AKUMA's line when AKUMA has none; line 11 (Zangief)
; takes its counters from XP_ZST (s2 / s3 / s5 / s4 = wins P1, wins P2,
; losses P1, losses P2). Leaf: t0, at.
xp_zrsline:
	lw      t0, 0x30(sp)
	li      at, 8
	bne     s1, at, @@z
	ori     t0, t0, 0xC00
	andi    at, t0, 0x200               ; DEVILOT: right under AKUMA, or in
	sltu    at, zero, at                ; its place when AKUMA has no line
	addiu   at, at, 10
	la      v1, xp_rs_line + 8          ; (not v0: the caller's delay slot
	sb      at, 0(v1)                   ; has put the line bit there)
@@z:
	li      at, 11
	bne     s1, at, @@ret
	nop
	la      s2, XP_ZST
	addiu   s3, s2, 4
	addiu   s5, s2, 8
	addiu   s4, s2, 12
@@ret:
	jr      ra
	nop

; CLEAR RESULT (0x80138810, was jal 0x8012102c: a0 = STATS, a1 = 0xB0)
xp_zclear:
	la      at, XP_ZST
	sw      zero, 0(at)
	sw      zero, 4(at)
	sw      zero, 8(at)
	j       0x8012102C
	sw      zero, 12(at)

.endarea

; Saving (0x80103E50) zeroes the counters of a secret character that was
; only reached by its code this session (Dan: 0x80103F04, flag 0x8016CAFA
; clear and "used" 0x801BF120 set), so they never reach the card. Dan is
; listed like everyone else now: his counters are always saved.
.org 0x80103F10
	b       0x80103F4C                  ; (delay slot: ori a1, s0, 0x200)

.org 0x8014E03C
.area 0x8014E0CC - 0x8014E03C, 0
; save block (0x801039C0, was jal 0x80103E50): then 'ZGST', his counters
; and their sum at +0x380
xp_rssave:
	addiu   sp, sp, -0x18
	sw      ra, 0x10(sp)
	jal     0x80103E50
	nop
	li      t0, ZST_SAVE
	li      t1, ZST_MAGIC
	sw      t1, 0(t0)
	la      t2, XP_ZST
	li      t3, 4
@@cp:
	lw      t4, 0(t2)
	addiu   t2, t2, 4
	addu    t1, t1, t4
	sw      t4, 4(t0)
	addiu   t3, t3, -1
	bnez    t3, @@cp
	addiu   t0, t0, 4
	sw      t1, 4(t0)                   ; sum (magic + counters)
	lw      ra, 0x10(sp)
	addiu   sp, sp, 0x18
	jr      ra
	nop

.endarea

.org 0x8015ABC4
.area 0x8015AC88 - 0x8015ABC4, 0
; save block read back (0x80103830, was jal 0x80104054): v0 = 0 when it
; was valid; then his counters, if the block has them, else zero
xp_rsload:
	addiu   sp, sp, -0x18
	sw      ra, 0x10(sp)
	jal     0x80104054
	nop
	la      t2, XP_ZST
	sw      zero, 0(t2)
	sw      zero, 4(t2)
	sw      zero, 8(t2)
	bnez    v0, @@ret
	sw      zero, 12(t2)
	li      t0, ZST_SAVE
	lw      t1, 0(t0)
	li      t3, ZST_MAGIC
	bne     t1, t3, @@ret
	lw      t4, 4(t0)
	lw      t5, 8(t0)
	lw      t6, 12(t0)
	lw      t7, 16(t0)
	lw      t8, 20(t0)                  ; sum
	addu    t3, t3, t4
	addu    t3, t3, t5
	addu    t3, t3, t6
	addu    t3, t3, t7
	bne     t3, t8, @@ret
	nop
	sw      t4, 0(t2)
	sw      t5, 4(t2)
	sw      t6, 8(t2)
	sw      t7, 12(t2)
@@ret:
	lw      ra, 0x10(sp)
	addiu   sp, sp, 0x18
	jr      ra
	nop
.endarea

.org 0x80117E8C
.area 0x80117F24 - 0x80117E8C, 0
XP_ZST:
	.word   0, 0, 0, 0                  ; wins side 0 / 1, losses side 0 / 1

xp_rs_names:                            ; 12 x 9 bytes
	.incbin IN, 0x8016F64C - 0x80100000 + 0x800, 11 * 9
	.ascii  "ZANGIEF"
	.byte   0, 0
xp_rs_col:                              ; name column
	.incbin IN, 0x8016F6B0 - 0x80100000 + 0x800, 11
	.byte   0x14                        ; ZANGIEF, as FELICIA
xp_rs_line:                             ; line: the regulars as vanilla, then
	.incbin IN, 0x8016F6BC - 0x80100000 + 0x800, 8
	.byte   11, 10, 8, 9                ; DEVILOT, AKUMA, DAN, ZANGIEF
	.align  4

.endarea

; ---- hooks ----
.org 0x801382B8                         ; the counter update
	lui     at, 0x801A
	sh      zero, -0x2B8(at)
	sh      zero, -0x2F8(at)
	jal     xp_zinc
	move    a0, s4
	j       0x801383B4
	nop
.org 0x80138A04
	jal     xp_zrsline                  ; (delay slot: sllv v0, s7, s1)
.org 0x80138A18
	lui     a2, hi(xp_rs_names)
	addiu   a2, a2, lo(xp_rs_names)
.org 0x80138A24
	lui     at, hi(xp_rs_line)
	addiu   at, at, lo(xp_rs_line)
.org 0x80138A34
	lui     at, hi(xp_rs_col)
	addiu   at, at, lo(xp_rs_col)
.org 0x80138B30
	slti    v0, s1, 12
.org 0x80138810
	jal     xp_zclear
.org 0x801039C0
	jal     xp_rssave
.org 0x80103830
	jal     xp_rsload

; totals line and menu, one row down
.org 0x80138970
	ori     a1, zero, 0x14
.org 0x80138988
	ori     a1, zero, 0x14
.org 0x801389A0
	ori     a1, zero, 0x14
.org 0x801389B0
	ori     a1, zero, 0x14
.org 0x801389CC
	ori     a1, zero, 0x14
.org 0x80138B70
	ori     a1, zero, 0x14
.org 0x80138B9C
	ori     a1, zero, 0x14
.org 0x80138BBC
	ori     a1, zero, 0x14
.org 0x80138BDC
	ori     a1, zero, 0x14
.org 0x80138C98
	ori     a1, zero, 0x17
.org 0x80138CB4
	ori     a1, zero, 0x19
.org 0x80138CD0
	ori     a1, zero, 0x1B
.org 0x801387F4
	ori     a1, zero, 0x1B              ; the line that clears the menu row
