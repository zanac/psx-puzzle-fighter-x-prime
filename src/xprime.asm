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

; ---- character select confirm hook (see CHARACTER SELECT below) ----
; In: a0 = secret code result (0 none, 1..3), s0 = select struct.
; If no code was entered but the cursor already shows Devilot/Akuma/Dan
; (8..10, reached by cycling), take the vanilla secret-character path with
; a0 = char - 7, which also sets the per-secret "used" globals.
xp_confirm:
	bnez    a0, @@secret            ; code entered: vanilla, v1 = a0 + 7
	nop
	lb      v1, 0x74(s0)
	nop
	slti    v0, v1, 8
	bnez    v0, @@normal
	nop
	addiu   a0, v1, -7
@@secret:
	j       0x8013AB88
	nop
@@normal:
	j       0x8013AC18
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

; ============================================================================
; CHARACTER SELECT
; Pressing Down while on the bottom row cycles the character on that cell:
;   cell char -> Devilot -> Akuma -> Dan -> Mei-Ling -> Anita -> cell char
; The cursor stays on the visible cell (there is no screen room for a third
; row). Up/Left/Right behave as in vanilla and restore the cell's character.
; Mei-Ling / Anita are Hsien-Ko / Donovan (4 / 5) plus the player's bit in
; 0x801AE4D8 / 0x801AE4D9, exactly what the vanilla code entry produces.
; ============================================================================

CURSOR_CHARS equ 0x8016F6E4             ; cursor position -> character
ALT_BITS     equ 0x801AE4D8             ; +0 Mei-Ling bits, +1 Anita bits

; cursor badge ("1P"/"2P"): vanilla hides it when the character is >= 8;
; keep it on the cell while a secret character is shown there
.org 0x80115FB8
	sltiu   v0, v0, 11                  ; P1
.org 0x80115FC8
	sltiu   v0, v0, 11                  ; P2

; confirm: let cycled Devilot/Akuma/Dan go through the secret-code path
.org 0x8013AB80
	j       xp_confirm
	addiu   v1, a0, 7                   ; (vanilla delay slot)

; cursor movement (vanilla 0x8013AD30), a0 = select struct, a1 = pad,
; a2 = cursor struct (+0 character, +1 position 0..7)
.org 0x8013AD30
.area 0x8013AEC8 - 0x8013AD30, 0
xp_move:
	addiu   sp, sp, -0x18
	sw      s0, 0x10(sp)
	sw      ra, 0x14(sp)
	andi    v0, a1, 0xF000
	beqz    v0, @@ret
	move    s0, a0
	lbu     t0, 1(a2)                   ; cursor position
	lb      t4, 0x73(s0)                ; player index
	li      t5, 1
	sllv    t5, t5, t4                  ; t5 = this player's alt bit
	nor     t6, t5, zero                ; t6 = ~bit
	lui     t4, hi(ALT_BITS)
	lbu     t7, lo(ALT_BITS)(t4)        ; Mei-Ling bits
	lbu     t8, lo(ALT_BITS + 1)(t4)    ; Anita bits
	move    t3, zero                    ; bit to set in Mei-Ling bits
	move    t9, zero                    ; bit to set in Anita bits
	andi    a1, a1, 0xFFFF
	li      v0, 0x1000                  ; up
	beq     a1, v0, @@updown
	addiu   t1, t0, -4
	li      v0, 0x8000                  ; left
	beq     a1, v0, @@leftright
	addiu   t1, t0, -1
	li      v0, 0x2000                  ; right
	beq     a1, v0, @@leftright
	addiu   t1, t0, 1
	li      v0, 0x4000                  ; down
	bne     a1, v0, @@ret
	addiu   t1, t0, 4
	sltiu   v0, t0, 4
	bnez    v0, @@updown                ; top row: plain move down
	nop

	; Down on the bottom row: cycle the character of this cell
	lbu     t2, 0(a2)
	li      v0, 10
	bne     t2, v0, @@not_dan
	slti    v0, t2, 8
	li      t2, 4                       ; Dan -> Mei-Ling
	b       @@apply
	move    t3, t5
@@not_dan:
	bnez    v0, @@not_secret
	li      v0, 4
	b       @@apply
	addiu   t2, t2, 1                   ; Devilot -> Akuma -> Dan
@@not_secret:
	bne     t2, v0, @@not_meiling
	and     v1, t7, t5
	beqz    v1, @@not_meiling
	nop
	li      t2, 5                       ; Mei-Ling -> Anita
	b       @@apply
	move    t9, t5
@@not_meiling:
	li      v0, 5
	bne     t2, v0, @@to_devilot
	and     v1, t8, t5
	bnez    v1, @@cell_char             ; Anita -> cell character
	nop
@@to_devilot:
	b       @@apply
	li      t2, 8                       ; cell character -> Devilot

@@leftright:                            ; stay on the same row
	srl     v0, t1, 2
	srl     v1, t0, 2
	bne     v0, v1, @@ret
	nop
	b       @@moved
	nop
@@updown:
	sltiu   v0, t1, 8
	beqz    v0, @@ret
	nop
@@moved:
	sb      t1, 1(a2)
	move    t0, t1
@@cell_char:                            ; t0 = cursor position
	la      v0, CURSOR_CHARS
	addu    v0, v0, t0
	lbu     t2, 0(v0)

@@apply:                                ; t2 = character, t3/t9 = alt bit to set
	and     t7, t7, t6
	or      t7, t7, t3
	and     t8, t8, t6
	or      t8, t8, t9
	sb      t7, lo(ALT_BITS)(t4)
	sb      t8, lo(ALT_BITS + 1)(t4)
	sb      t2, 0x74(s0)
	sb      t2, 0(a2)
	li      a0, 0xD                     ; cursor sound
	move    a1, zero
	jal     0x80105C88
	lb      a2, 0x73(s0)
	move    a0, s0                      ; character animation
	jal     0x80136400
	li      a1, 0x17
	lb      a0, 0x73(s0)                ; portrait / name
	lb      a1, 0x74(s0)
	lui     a2, 0x801B
	bnez    a0, @@p2
	nop
	b       @@portrait
	lb      a2, -0x1A93(a2)             ; P1 +0x6D (0x801AE56D)
@@p2:
	lb      a2, -0x17E7(a2)             ; P2 +0x6D (0x801AE819)
@@portrait:
	nop                                 ; load delay
	jal     0x8010789C
	nop
@@ret:
	lw      ra, 0x14(sp)
	lw      s0, 0x10(sp)
	jr      ra
	addiu   sp, sp, 0x18
.endarea

.close
