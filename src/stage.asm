; ============================================================================
; VERSUS STAGE SELECTOR
; Vanilla: the stage is the character of P1 (0x8012CCE0 -> 0x8019FC98), and
; the stage brings its own music. In Versus, a line under the character grid
;   L1 < STAGE:  NORMAL  > R1
; is changed by P1 (until P1 confirms): R1 next, L1 previous:
;   NORMAL, RANDOM, MORRIGAN .. AKUMA (the 10 stages), [ZANGIEF], NORMAL ...
; NORMAL is vanilla (P1's stage; Zangief's own with ZG_HAVE). RANDOM (the
; default) draws a stage at every match, never the one of the previous
; match; Zangief's stage (ZG_HAVE) has 3 tickets of 13 when he plays, 1 of
; 11 otherwise. The setting lives until the title
; screen comes back (xp_title resets it to RANDOM). Arcade, Street Puzzle and demo are not touched.
;
; Code space: 0x801544E4 is a 996-byte function that nothing references
; (no jal, no pointer, no lui/addiu pair) and that never runs (emulator
; coverage over boot, attract, menus, select and matches).
; ============================================================================

STAGE_IDX   equ 0x8019FC98              ; halfword, read by the stage loader
PAD_P1      equ 0x801BF09E              ; pad bits pressed this frame
PAD_L1      equ 0x0004
PAD_R1      equ 0x0008
STAGE_COL   equ 11
STAGE_ROW   equ 27
STAGE_PAL   equ 5
STAGE_CELL  equ TEXT_MAP + STAGE_COL * 0x78 + STAGE_ROW * 4
STAGE_TAG   equ (STAGE_PAL << 16) | 0xCC ; 'L' top half: marks our line
STAGE_LEN   equ 25
N_SETTINGS  equ 12 + ZG_HAVE            ; NORMAL, RANDOM, 10 stages (+ ZANGIEF)

.org 0x801544E4
.area 0x801548C8 - 0x801544E4, 0

; select handler, once per frame for each player still choosing; runs
; inline (jumped to from 0x8013AA60, ends at 0x8013AACC), so t/a regs and
; ra are free here (the handler restores ra from its frame)
xp_stagekey:
	lui     t0, hi(MODE_NEXT)
	lbu     t0, lo(MODE_NEXT)(t0)
	li      t1, 3
	bne     t0, t1, @@out           ; Versus only
	lb      t0, 0x73(s0)            ; player index
	lui     t1, hi(PAD_P1)
	bnez    t0, @@draw              ; only P1 changes the stage
	lhu     t2, lo(PAD_P1)(t1)
	nop
	andi    t2, t2, PAD_L1 | PAD_R1
	beqz    t2, @@draw
	la      t3, xp_stg_setting
	lbu     t1, 0(t3)
	andi    t2, t2, PAD_R1
	beqz    t2, @@prev
	nop
	addiu   t1, t1, 1               ; R1: next
	sltiu   t2, t1, N_SETTINGS
	bnez    t2, @@store
	nop
	b       @@store
	move    t1, zero
@@prev:                                 ; L1: previous
	bnez    t1, @@dec
	nop
	li      t1, N_SETTINGS
@@dec:
	addiu   t1, t1, -1
@@store:
	sb      t1, 0(t3)
	li      a0, 0xD                 ; cursor sound
	move    a1, zero
	jal     0x80105C88
	move    a2, t0
@@draw:
	jal     xp_stage_draw
	nop
@@out:
	j       0x8013AACC
	nop

; draw the line if the setting changed or the cells are not ours (leaf)
xp_stage_draw:
	la      t0, xp_stg_setting
	lbu     t1, 0(t0)               ; setting
	la      t2, STAGE_CELL
	lw      t3, 0(t2)
	li      t4, STAGE_TAG
	bne     t3, t4, @@redraw
	lbu     t3, 1(t0)               ; setting on screen
	nop
	beq     t3, t1, @@ret
	nop
@@redraw:
	sb      t1, 1(t0)
	la      t3, xp_stg_names        ; name -> line[12..19]
	sll     t5, t1, 3
	addu    t3, t3, t5
	la      t5, xp_stg_line + 12
	li      t4, 8
@@copy:
	lbu     t6, 0(t3)
	addiu   t3, t3, 1
	addiu   t4, t4, -1
	sb      t6, 0(t5)
	bnez    t4, @@copy
	addiu   t5, t5, 1
	la      t3, xp_stg_line
	lui     t7, STAGE_PAL
@@chr:                                  ; 8x16 font: top = (c&1F)+((c&E0)<<1)+40
	lbu     t4, 0(t3)
	addiu   t3, t3, 1
	beqz    t4, @@dirty
	andi    t5, t4, 0x1F
	andi    t6, t4, 0xE0
	sll     t6, t6, 1
	addu    t5, t5, t6
	addiu   t5, t5, 0x40
	or      t5, t5, t7
	sw      t5, 0(t2)
	addiu   t5, t5, 0x20            ; bottom half
	sw      t5, 4(t2)
	b       @@chr
	addiu   t2, t2, 0x78
@@dirty:
	li      t4, 2
	lui     t5, hi(TEXT_DIRTY)
	sb      t4, lo(TEXT_DIRTY)(t5)
@@ret:
	jr      ra
	nop

; scene init (from xp_marker_clear): blank the line if it is there.
; Only t0-t3: the caller relies on a0-a3 and t8.
xp_stage_erase:
	la      t0, STAGE_CELL
	lw      t1, 0(t0)
	li      t2, STAGE_TAG
	bne     t1, t2, @@ret
	li      t1, 0x20                ; blank cell
	li      t2, STAGE_LEN
@@loop:
	sw      t1, 0(t0)
	sw      t1, 4(t0)
	addiu   t2, t2, -1
	bnez    t2, @@loop
	addiu   t0, t0, 0x78
	li      t1, 2
	lui     t0, hi(TEXT_DIRTY)
	sb      t1, lo(TEXT_DIRTY)(t0)
@@ret:
	jr      ra
	nop

; stage index at match start (replaces "lbu v0, 0x68(s2)" at 0x8012CCE0,
; returns v0; a0-a2 and s regs preserved; ra is saved by the caller).
; With Zangief's stage (ZG_HAVE) there is an 11th stage, index 11
; (zangief.asm); 10 stays Dan's (Ken's picture, Dan's music).
xp_stage:
	move    t9, ra
	lbu     v0, 0x68(s2)            ; vanilla: P1's character
	lui     t0, hi(MODE)
	lbu     t0, lo(MODE)(t0)
	li      t1, 3
	la      t2, xp_stg_setting
	bne     t0, t1, @@arc               ; not Versus
	lbu     t1, 0(t2)
	nop
	bnez    t1, @@set
	addiu   t1, t1, -2
.if ZG_HAVE
	jal     xp_zchar                ; NORMAL: P1's character, 11 = Zangief
	move    t6, s2
	b       @@last
	move    v0, t7
.else
	b       @@last
	nop
.endif
.if ZG_HAVE
@@arc:                                  ; Arcade: the CPU's stage; Zangief's own
	li      t3, ZG_CHAR
	bne     v0, t3, @@last
	nop
	jal     xp_zchar
	move    t6, s2
	b       @@last
	move    v0, t7
.else
@@arc:
	b       @@last
	nop
.endif
@@set:
	bgez    t1, @@pos               ; fixed stage (position 0..N_STAGES-1)
	move    v0, t1
.if ZG_HAVE
	jal     xp_zstg_tickets         ; t5 = 11 tickets, 13 if Zangief plays
	nop
.else
	li      t5, 10
.endif
	lw      t3, 4(t2)               ; RANDOM: LCG, stirred with the root
	lui     t6, 0x1F80              ; counters (so it depends on when the
	lhu     t7, 0x1100(t6)          ; players press the buttons)
	lhu     t6, 0x1110(t6)
	addu    t3, t3, t7
	sll     t6, t6, 16
	addu    t3, t3, t6
	lui     t4, 0x41C6
	ori     t4, t4, 0x4E6D
	lbu     t6, 2(t2)               ; position of the previous match's stage
@@draw:
	multu   t3, t4
	mflo    t3
	addiu   t3, t3, 0x3039
	srl     t7, t3, 8
	divu    t7, t5
	mfhi    v0
	sltiu   t7, v0, 10
	bnez    t7, @@again
	nop
	li      v0, 10                  ; tickets 10.. = Zangief's stage
@@again:
	beq     v0, t6, @@draw          ; never the previous one
	nop
	sw      t3, 4(t2)
@@pos:                                  ; position 10 = Zangief's stage (11)
	xori    t7, v0, 10
	bnez    t7, @@last
	nop
	li      v0, 11
@@last:                                 ; remember the position used:
	sltiu   t4, v0, 10              ; Dan (10) plays on Ken's picture (3),
	bnez    t4, @@keep              ; Zangief's stage (11) is position 10
	move    t4, v0
	xori    t3, v0, 11              ; 10 -> 1, 11 -> 0
	sll     t4, t3, 3
	subu    t4, t4, t3
	li      t3, 10
	subu    t4, t3, t4              ; 10 - 7 * (v0 == 10)
@@keep:
	jr      t9
	sb      t4, 2(t2)

; ---- character select: Up cycles back (see zangief.asm) ----
; Up on the bottom row while a secret character is shown walks the Down ring
; backwards: Zangief -> Anita -> Mei-Ling -> Dan -> Akuma -> Devilot -> cell.
; (kept here: xp_move's branches must reach it)
; Branched to from xp_move on Up with t0 = cursor position, t1 = t0 - 4,
; t4 = hi(ALT_BITS), t5 = player bit, t7/t8 = Mei-Ling/Anita bits.
xp_up:
	sltiu   v0, t0, 4
	bnez    v0, @@vanilla           ; top row
	lbu     t2, 0(a2)               ; character shown on the cell
	nop
	sltiu   v0, t2, 8
	bnez    v0, @@alts
	li      v0, 8
	beq     t2, v0, @@cell          ; Devilot -> cell character
	li      v0, ZG_CHAR
	bne     t2, v0, @@down1
	nop
	jal     xp_zbit
	nop
	beqz    v1, @@down1
	nop
	move    t9, t5                  ; Zangief -> Anita
	j       xp_mv_apply
	li      t2, 5
@@down1:
	j       xp_mv_apply             ; Dan -> Akuma -> Devilot
	addiu   t2, t2, -1
@@alts:
	li      v0, 4
	bne     t2, v0, @@anita
	and     v1, t7, t5
	beqz    v1, @@vanilla           ; plain Hsien-Ko
	nop
	j       xp_mv_apply             ; Mei-Ling -> Dan
	li      t2, ZG_CHAR
@@anita:
	li      v0, 5
	bne     t2, v0, @@vanilla
	and     v1, t8, t5
	beqz    v1, @@vanilla           ; plain Donovan
	nop
	move    t3, t5                  ; Anita -> Mei-Ling
	j       xp_mv_apply
	li      t2, 4
@@cell:
	j       xp_mv_cell
	nop
@@vanilla:
	j       xp_mv_updown
	nop

; branch target for xp_move (zangief.asm is out of branch range)
xp_zg_anita_t:
	j       xp_zg_anita
	nop

.align 4
xp_stg_setting:
	.byte   1                       ; +0 setting (0 NORMAL, 1 RANDOM, 2+ stage)
	.byte   0xFF                    ; +1 setting on screen
	.byte   0xFF                    ; +2 stage of the previous match
	.byte   0
	.word   0x2F6B1D35              ; +4 random state
xp_stg_line:
	.ascii  "L1 < STAGE: ........ > R1"
	.byte   0
xp_stg_names:                           ; 8 characters each, centred
	.ascii  " NORMAL  RANDOM MORRIGANCHUN-LI "
	.ascii  "  RYU     KEN   HSIEN-KODONOVAN "
	.ascii  "FELICIA  SAKURA DEVILOT  AKUMA  "
.if ZG_HAVE
	.ascii  "ZANGIEF "
.endif
.endarea
