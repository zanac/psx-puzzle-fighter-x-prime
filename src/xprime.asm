; Super Puzzle Fighter II Turbo (NTSC-U, SLUS-00418) — X' rebalance
; Assemble with armips: armips src/xprime.asm -strequ IN <exe> -strequ OUT <out>

.psx
.open IN, OUT, 0x80100000 - 0x800

; ============================================================================
; DROP PATTERNS  (table at 0x8016E684, 11 chars x 0xC0, rows bottom first)
; 1 Blue 2 Yellow 3 Green 4 Red; each row = 6 cells + 2 padding halfwords
; ============================================================================

.macro pattern4, r1a,r1b,r1c,r1d,r1e,r1f, r2a,r2b,r2c,r2d,r2e,r2f, r3a,r3b,r3c,r3d,r3e,r3f, r4a,r4b,r4c,r4d,r4e,r4f
	.halfword r1a,r1b,r1c,r1d,r1e,r1f,0,0
	.halfword r2a,r2b,r2c,r2d,r2e,r2f,0,0
	.halfword r3a,r3b,r3c,r3d,r3e,r3f,0,0
	.halfword r4a,r4b,r4c,r4d,r4e,r4f,0,0
	.halfword r1a,r1b,r1c,r1d,r1e,r1f,0,0
	.halfword r2a,r2b,r2c,r2d,r2e,r2f,0,0
	.halfword r3a,r3b,r3c,r3d,r3e,r3f,0,0
	.halfword r4a,r4b,r4c,r4d,r4e,r4f,0,0
	.halfword r1a,r1b,r1c,r1d,r1e,r1f,0,0
	.halfword r2a,r2b,r2c,r2d,r2e,r2f,0,0
	.halfword r3a,r3b,r3c,r3d,r3e,r3f,0,0
	.halfword r4a,r4b,r4c,r4d,r4e,r4f,0,0
.endmacro

PATTERNS equ 0x8016E684

.org PATTERNS + 0 * 0xC0            ; Morrigan
	pattern4 1,2,4,4,2,1, 1,2,3,4,2,1, 2,1,3,4,1,2, 2,1,3,3,1,2

.org PATTERNS + 2 * 0xC0            ; Ryu
	pattern4 4,3,1,2,4,3, 4,3,1,2,4,3, 1,2,4,3,1,2, 4,3,1,2,4,3

.org PATTERNS + 4 * 0xC0            ; Hsien-Ko (and Mei-Ling)
	pattern4 1,2,1,3,4,3, 1,1,3,4,2,3, 1,3,4,2,1,3, 1,4,2,1,3,3

.org PATTERNS + 6 * 0xC0            ; Felicia
	pattern4 3,4,4,1,1,2, 2,4,1,4,1,3, 3,4,1,4,1,2, 2,1,1,4,4,3

.org PATTERNS + 7 * 0xC0            ; Sakura
	pattern4 3,4,4,4,4,2, 3,1,1,1,1,2, 2,4,4,4,4,3, 2,1,1,1,1,3

; ============================================================================
; DAMAGE TABLES  (replace the vanilla margin/level tables, same 0x50 bytes,
; same layout as the arcade X' patch at CPS2 0x10110)
; ============================================================================

DMGTAB equ 0x8016E5F4

.org DMGTAB
.area 0x50
	; +0x00 margin time thresholds (seconds, compared against time+15)
	.halfword 90, 120, 150, 180, 210, 240, 270, 2970
	; +0x10 receive rate /20, indexed by the receiving player's character
	;       (looked up through the attacker's opponent pointer +0x84)
	;        Mor  Chun Ryu  Ken  Hsien Don  Fel  Sak  Devi Akuma Dan
	.byte    20,  20,  20,  20,  20,   20,  20,  20,  20,  24,   20,  20, 20, 20, 20, 20
	; +0x20 margin time numerators /10
	.halfword 10, 11, 12, 13, 14, 15, 16, 17
	; +0x30 send rate /20, indexed by own character
	.byte    20,  24,  20,  20,  20,   20,  20,  20,  17,  20,   20,  20, 20, 20, 20, 20
	; +0x40 damage level numerators /10 (option 0..3)
	.halfword 8, 10, 13, 15, 15, 15, 15, 15
.endarea

; ============================================================================
; DAMAGE ROUTINE  (0x80134D80, called once per attack with a0 = player)
; Rewrites the computation part; falls into the vanilla tail at 0x80134F58
; (Versus handicap, add to pending garbage +0x22A, cap 250) with a3 = damage.
;
; X' formula (bit-exact with the arcade patch), mf(x,n,d) = floor(x/d)*n,
; skipped when n == d:
;   x = sum(+0x10C..+0x118)
;   x = mf(x, 10+i, 10)            margin time
;   x = mf(x, recv[opp char], 20)  NOTE: arcade uses the opponent's char
;   x = mf(x, send[own char], 20)
;   if diamond: x = mf(x, 8, 10)
;   x = mf(x, level[opt], 10)
;   x = mf(x, 1, 100)
; Dropped vanilla rules: diamond >>1, Devilot/Akuma x/2+x/4,
; Mei-Ling/Anita +25 % (they now count as Hsien-Ko/Donovan).
; ============================================================================

.org 0x80134D80
.area 0x80134F58 - 0x80134D80, 0
xp_damage:
	move    t9, ra

	; x = sum of score components
	lh      t0, 0x10C(a0)
	lh      t2, 0x10E(a0)
	lh      t3, 0x110(a0)
	addu    t0, t0, t2
	lh      t2, 0x112(a0)
	addu    t0, t0, t3
	lh      t3, 0x114(a0)
	addu    t0, t0, t2
	lh      t2, 0x116(a0)
	addu    t0, t0, t3
	lh      t3, 0x118(a0)
	addu    t0, t0, t2
	lh      t5, 0x1F0(a0)           ; elapsed seconds
	addu    t0, t0, t3

	; margin time
	la      t1, DMGTAB
	addiu   t5, t5, 15
	move    t4, t1
@@margin_loop:
	lh      t2, 0(t4)
	nop
	slt     t3, t2, t5              ; threshold < time+15 -> next step
	beqz    t3, @@margin_done
	nop
	b       @@margin_loop
	addiu   t4, t4, 2
@@margin_done:
	lh      t2, 0x20(t4)
	jal     xp_mulfrac
	li      t3, 10

	; receive rate (opponent's character, as in the arcade patch)
	lw      t6, 0x84(a0)
	nop
	lbu     t7, 0x68(t6)
	li      t3, 20
	addu    t7, t1, t7
	lbu     t2, 0x10(t7)
	jal     xp_mulfrac
	nop

	; send rate (own character)
	lbu     t7, 0x68(a0)
	li      t3, 20
	addu    t7, t1, t7
	lbu     t2, 0x30(t7)
	jal     xp_mulfrac
	nop

	; diamond: 80 %
	lb      t7, 0x23F(a0)
	li      t3, 10
	beqz    t7, @@no_diamond
	li      t2, 8
	jal     xp_mulfrac
	nop
@@no_diamond:

	; damage level option
	lui     t7, 0x801A
	lb      t7, -0x3BFB(t7)         ; 0x8019C405
	li      t3, 10
	andi    t7, t7, 7
	sll     t7, t7, 1
	addu    t7, t1, t7
	lh      t2, 0x40(t7)
	jal     xp_mulfrac
	nop

	; / 100
	li      t2, 1
	jal     xp_mulfrac
	li      t3, 100

	move    ra, t9
	j       0x80134F58              ; vanilla tail: handicap, pending, cap
	move    a3, t0

; t0 = floor(t0 / t3) * t2, unchanged if t2 == t3, 0 if t0 < 0
xp_mulfrac:
	beq     t2, t3, @@ret
	nop
	bltz    t0, @@zero
	nop
	div     t0, t3
	mflo    t0
	nop
	nop
	mult    t0, t2
	mflo    t0
	jr      ra
	nop
@@zero:
	move    t0, zero
@@ret:
	jr      ra
	nop
.endarea

; ============================================================================
; DIAMOND  (0x8012FC9C)
; Vanilla sets the 50 % flag (+0x23F) only for a top diamond; rotating the
; pair so the diamond lands at the bottom gives 100 % ("diamond trick").
; X': flag in both cases; top diamond on 0xFF ("teched") behaves like the
; bottom one (-> 5), as in the arcade patch.
; ============================================================================

.org 0x8012FCC8
	j       0x8012FCE4              ; top diamond: go through the 0xFF -> 5 check

.org 0x8012FCDC
	sb      v0, 0x23F(s0)           ; bottom diamond: set penalty flag (v0 = 1)

.close
