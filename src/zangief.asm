; ============================================================================
; ZANGIEF (hidden character, Versus and Arcade)
; Zangief is Dan's slot (10) plus his own per-player bit in XP_ZBITS, the
; same way Mei-Ling / Anita are Hsien-Ko / Donovan plus a bit. He is only
; real in Versus and Arcade: every test also checks the game mode, through
; XP_ZOK / XP_ZOKN (3 when MODE / MODE_NEXT is Versus or Arcade, set every
; frame by xp_frame; Street Puzzle, which is MODE 1 as Arcade, is excluded).
;   select:  his own icon, cursor position 8 above Chun-Li (select.asm)
;   pattern: "Siberian Bear" (XP_ZPATTERN), via the pattern lookup 0x801350E4
;   damage:  index 11 in DMGTAB (send 90 %, receive 90 %), via xp_zchar
; Code space: 0x80163CDC, a 684-byte function with no references that never
; runs (coverage over boot, menus, Versus, Arcade, Street Puzzle).
; ============================================================================

; (ZG_CHAR, P1_STRUCT, ZG_MAGIC are defined at the top of xprime.asm)

; step 6: his stage and music (new file ids after PL0B_OBJ / SE_PL0B, build.sh)
ZG_STFILE equ 0x58              ; his stage (tools/pf_stage.py)
ZG_XAFILE equ 0x59              ; his music (pf_stage.py music)
ZG_SONG   equ 47                ; song id = XA player entry
ZG_XA_CHAN equ 6                ; Pocket Fighter's XA00 channel 6
ZG_XA_LEN equ 3376              ; its sectors
; step 7: the staff roll figure
ZG_ENDFILE equ 0x5A                     ; ZG_END.EMI (build.sh)
END_BLOCK  equ 0x800A1000               ; figure banks of the ENDING files
END_RECS   equ 0x800B1000
END_MAGIC  equ 0x444E475A               ; 'ZGND' at +0x7C (build_end)
ZH_GFX     equ 0x80070000               ; HARD finale: his file, in the
ZH_REC     equ 0x80082000               ; ENDING leftovers
ZH_DELAY   equ 260                      ; frames before he appears (the others: 1-240;
                                        ; + 42 of fade-in, it must end before the
                                        ; common landing timer, 336)
ZH_X       equ 184                      ; the back row's middle gap, under the logo
ZH_Y       equ 80                       ; back row (his frames: feet at 256 - y)
ZH_FACE    equ 0
ZH_PRIO    equ 11                       ; behind everyone (lower = in front)

.org 0x80163CDC
.area 684, 0

; xp_zbit: v1 = this player's Zangief bit in Versus / Arcade, else 0.
; In: t5 = player bit. Leaf, v1 only.
xp_zbit:
	lui     v1, hi(XP_ZOKN)
	lbu     v1, lo(XP_ZOKN)(v1)
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

; Anita, Down: the cell character.
; (experimental-arcade: Zangief has his own icon, select.asm; Anita -> cell)
xp_zg_anita:
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
	lui     t8, hi(XP_ZOK)
	lbu     t8, lo(XP_ZOK)(t8)
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
	lui     t7, hi(XP_ZOK)
	lbu     t7, lo(XP_ZOK)(t7)
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

; ---- Zangief's stage (step 6): index 11 ----
; The four per-stage tables (11 entries each: load, set-up, per-frame,
; stage objects) and the stage -> song table are copied here with a 12th
; entry; their readers are repointed (hooks at the end of this file).
; Zangief's stage loads its own file and otherwise works like Ken's (a
; still picture, no objects).
.align 4
xp_stg_load:                            ; 0x80166728
	.incbin IN, 0x80166728 - 0x80100000 + 0x800, 11 * 4
	.word   xp_zstg_load
xp_stg_init:                            ; 0x80166754
	.incbin IN, 0x80166754 - 0x80100000 + 0x800, 11 * 4
	.word   0x80108EE0              ; Ken's
xp_stg_frame:                           ; 0x80166780
	.incbin IN, 0x80166780 - 0x80100000 + 0x800, 11 * 4
	.word   0x80108F2C              ; Ken's (nothing)
xp_stg_objs:                            ; 0x8016A29C
	.incbin IN, 0x8016A29C - 0x80100000 + 0x800, 11 * 4
	.word   0x8016A1AC              ; Ken's (empty list)
xp_stg_song:                            ; 0x8016D474 (halfwords)
	.incbin IN, 0x8016D474 - 0x80100000 + 0x800, 11 * 2
	.halfword ZG_SONG

xp_zstg_load:
	addiu   sp, sp, -0x18
	sw      ra, 0x10(sp)
	jal     0x801043C0
	li      a0, ZG_STFILE
	lw      ra, 0x10(sp)
	addiu   sp, sp, 0x18            ; (load delay: not jr right after lw)
	jr      ra
	nop

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
	lui     t1, hi(XP_ZOKN)
	lbu     t1, lo(XP_ZOKN)(t1)
	li      t2, 3
	beq     t1, t2, @@vs            ; select screen
	nop
	bnez    t1, @@ret
	lui     t1, hi(XP_ZOK)            ; VS screen: MODE_NEXT is 0, MODE 3
	lbu     t1, lo(XP_ZOK)(t1)
	nop
	bne     t1, t2, @@ret
@@vs:
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
	addiu   v1, a1, -23 * 4         ; 23/24: select-screen poses, xp_zselst
	sltiu   v1, v1, 8
	bnez    v1, @@select
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
	bnez    at, @@calm
	lw      t9, ZG_LISTOFF + 55 * 4(v1)
	nop
	addu    t9, t9, v1              ; hit scripts end
	sltu    at, t8, t9
	beqz    at, @@calm
	addu    t9, v1, a1
	lw      t9, ZG_LISTOFF + 51 * 4(t9)     ; hit tail for this state
	b       @@ret
	addu    s0, v1, t9
@@calm:                                 ; states 1/2 start with a voice cue:
	beqz    a1, @@ret               ; only from idle 0 / pinch 1
	lw      t9, ZG_LISTOFF + 56 * 4(v1)
	nop
	addu    t9, t9, v1
	sltu    at, t8, t9
	bnez    at, @@skip
	lw      t9, ZG_LISTOFF + 57 * 4(v1)
	nop
	addu    t9, t9, v1
	sltu    at, t8, t9
	bnez    at, @@ret
	nop
@@skip:
	addiu   s0, s0, 16
@@ret:
	jr      ra
	nop
@@select:
	j       xp_zselst
	nop

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

; RANDOM stage tickets (from xp_stage): t5 = 13 if a player is Zangief,
; else 11. Uses t3 (ra), t5-t8 and at.
xp_zstg_tickets:
	move    t3, ra
	li      t6, P1_STRUCT
	jal     xp_zchar
	li      t5, 13
	li      at, 11
	beq     t7, at, @@ret
	nop
	li      t6, P1_STRUCT + 0x2AC   ; P2
	jal     xp_zchar
	nop
	li      at, 11
	beq     t7, at, @@ret
	nop
	li      t5, 11
@@ret:
	jr      t3
	nop

; song -> entry of the XA player (0x801062F4; replaces 0x80106320-0x8010634C,
; a1 = song, returns v1 = entry). Zangief's song ZG_SONG is its own entry
; (47, unused) in both the original and the arranged music; the others as
; vanilla: entry = table[song (+ 24 with the arranged music)].
xp_songent:
	li      v1, ZG_SONG
	beq     a1, v1, @@ret
	lui     v0, 0x8017
	lb      v0, -0x357D(v0)         ; arranged music on
	nop
	beqz    v0, @@orig
	move    v1, a1
	addiu   v1, a1, 0x18
@@orig:
	lui     at, 0x8016
	addu    at, at, v1
	lb      v1, 0x621C(at)
@@ret:
	jr      ra
	nop
.endarea

; ============================================================================
; Select / VS portrait (step 5)
; The big portraits are "child" sprites made from a per-character list
; (table 0x8018B66C; Dan's is list 20 at 0x80189F24) by 0x80123BAC, with 10
; palettes copied per side by 0x8010773C. Both screens use the same list.
; Zangief's lists, palettes and frames are in his own file (tools/zangief.py
; portrait block, at the start of the graphics entry). On the select screen
; his file is not loaded for the match
; yet, so in Versus it is loaded into the other player's banks right after
; SELECT.EMI (those banks are free there; the "loaded file" cache byte says
; so, and the match load then skips or redoes it as usual).
; Code space: 0x80152C14 (332 bytes) and 0x8015515C-0x801554C4 (872
; bytes), functions with no references that never run (coverage: boot,
; menus, Versus select, VS, match).
; ============================================================================
CACHE_P1  equ 0x801BF115        ; "loaded file" cache bytes (P2 at +1)
DAN_PLIST equ 0x80189F24        ; Dan's portrait list

.org 0x80152C14
.area 0x14C, 0

; select screen loader (0x8012BF7C): SELECT.EMI (a0 = 0x39), then in Versus
; Zangief's file is queued for the banks SELECT.EMI did not take (cache byte
; 0xFF marks the side SELECT.EMI went to). Loads are asynchronous: the select
; scene waits for the loader (0x80128768), see xp_zselbusy.
xp_zselload:
	addiu   sp, sp, -0x18
	sw      ra, 0x10(sp)
	la      at, XP_ZEND
	sb      zero, 0(at)
	jal     0x801043C0
	nop
	lui     v0, hi(XP_ZOK)          ; Versus / Arcade (an Arcade challenge's
	lbu     at, lo(XP_ZOK)(v0)      ; select has MODE_NEXT 0: XP_ZOKN 0)
	lbu     v0, lo(XP_ZOKN)(v0)
	nop
	or      v0, v0, at
	li      at, 3
	bne     v0, at, @@done
	lui     at, hi(CACHE_P1)
	lb      v0, lo(CACHE_P1)(at)
	li      at, -1
	beq     v0, at, @@side
	li      v1, 2                   ; SELECT.EMI in P1's banks: use P2's
	li      v1, 1
@@side:
	la      at, XP_ZPEND
	sb      v1, 0(at)               ; 1 + player
@@done:
	lw      ra, 0x10(sp)
	nop
	jr      ra
	addiu   sp, sp, 0x18

; select scene "loader busy?" (0x80128768, replaces jal 0x80104354): once
; SELECT.EMI is in, start Zangief's load and report busy until it is done;
; then put the load destinations back.
xp_zselbusy:
	addiu   sp, sp, -0x18
	sw      ra, 0x10(sp)
	jal     0x80104354
	nop
	bnez    v0, @@ret
	la      t0, XP_ZPEND
	lb      a0, 0(t0)
	nop
	beqz    a0, @@ret               ; nothing queued (v0 = 0)
	li      at, 3
	beq     a0, at, @@finish
	addiu   a0, a0, -1              ; player
	sll     v0, a0, 3
	la      at, 0x80169E44          ; per player: graphics, record bank
	addu    at, at, v0
	lw      v0, 0(at)
	lw      v1, 4(at)
	lui     at, 0x801C
	lw      t1, -0x7E80(at)         ; keep the current destinations
	lw      t2, -0x7E7C(at)
	sw      t1, 4(t0)
	sw      t2, 8(t0)
	sw      v0, -0x7E80(at)         ; load destinations (as 0x8010BA90)
	sw      v1, -0x7E7C(at)
	la      at, CACHE_P1
	addu    at, at, a0
	li      v0, ZG_GROUP
	sb      v0, 0(at)
	li      v0, 3
	sb      v0, 0(t0)               ; in progress
	jal     0x801043C0
	li      a0, ZG_FILE
	b       @@ret
	li      v0, 1
@@finish:
	sb      zero, 0(t0)
	lw      t1, 4(t0)
	lw      t2, 8(t0)
	lui     at, 0x801C
	sw      t1, -0x7E80(at)
	sw      t2, -0x7E7C(at)
	move    v0, zero
@@ret:
	lw      ra, 0x10(sp)
	nop
	jr      ra
	addiu   sp, sp, 0x18

.align 4
XP_ZPEND:
	.word   0, 0, 0                 ; state (0 idle, 1/2 queued for P1/P2, 3 loading), saved destinations
.endarea

.org 0x8015515C
.area 0x801554C4 - 0x8015515C, 0         ; three never-run functions

; xp_zport: is side t8 (0 P1, 1 P2) showing Zangief's portrait, and where is
; his file? (Versus only: MODE_NEXT = 3 on the select screen, MODE = 3 with
; MODE_NEXT = 0 on the VS screen.) Out: v0 = record bank holding it (0 = no:
; keep Dan's), v1 = its
; graphics buffer, t9 = 0 on the select screen (a cache byte is 0xFF), 1 on
; the VS screen. Leaf: v0, v1, at, t9.
xp_zport:
	j       xp_zportend             ; staff roll first
	nop
xp_zport_sel:
	lui     v0, hi(XP_ZOKN)
	lbu     v0, lo(XP_ZOKN)(v0)   ; select: mode being set up
	li      at, 3
	beq     v0, at, @@vs
	nop
	bnez    v0, @@no
	lui     v0, hi(XP_ZOK)            ; VS screen: MODE_NEXT is 0 again
	lbu     v0, lo(XP_ZOK)(v0)
	nop
	bne     v0, at, @@no
@@vs:
	lui     v0, hi(XP_ZBITS)
	lbu     v0, lo(XP_ZBITS)(v0)
	nop
	srlv    v0, v0, t8
	andi    v0, v0, 1
	beqz    v0, @@no
	lui     at, hi(CACHE_P1)
	lb      v0, lo(CACHE_P1)(at)
	lb      v1, lo(CACHE_P1 + 1)(at)
	li      t9, 0
	li      at, -1
	beq     v0, at, @@scr
	nop
	beq     v1, at, @@scr
	nop
	li      t9, 1
@@scr:
	beqz    t8, @@p1
	li      at, ZG_GROUP
	beq     v1, at, @@bank2         ; P2: own banks first
	nop
	beq     v0, at, @@bank1
	nop
	b       @@no
	nop
@@p1:
	beq     v0, at, @@bank1
	nop
	beq     v1, at, @@bank2
	nop
@@no:
	jr      ra
	move    v0, zero
@@bank1:
	li      v0, BANK_P1
	li      v1, 0x80024000
	jr      ra
	nop
@@bank2:
	li      v0, BANK_P2
	li      v1, 0x8006C000
	jr      ra
	nop

; portrait list (0x80123BF0, delay slot: s0 = the list): Dan's list on a
; Zangief side -> his own list (select or VS) and XP_ZK set for xp_zkid.
; s1 = the parent object (+0xB = side). Uses v0, v1, at, t7-t9.
xp_zlist:
	move    t7, ra
	li      s2, 1                   ; vanilla (replaced)
	la      at, XP_ZK
	sw      zero, 0(at)
	li      at, DAN_PLIST
	bne     s0, at, @@ret
	nop
	lbu     t8, 0xB(s1)
	jal     xp_zport
	nop
	beqz    v0, @@ret
	nop
	move    v0, v1                  ; block: start of his graphics entry
	la      at, XP_ZK
	sw      v0, 0(at)
	sw      v1, 4(at)
	sll     t9, t9, 6               ; VS list at +0x40
	addu    s0, v0, t9
@@ret:
	jr      t7
	nop

; child sprite banks (0x80123C34): a0 = the child, s1 = the parent.
xp_zkid:
	la      at, XP_ZK
	lw      v0, 0(at)
	nop
	beqz    v0, @@van
	nop
	lw      v1, 4(at)
	addiu   v0, v0, 0x300           ; Zangief's portrait records
	sw      v1, 0x10(a0)
	jr      ra
	sw      v0, 0x14(a0)
@@van:
	lw      v0, 0x4C(s1)
	nop
	sw      v0, 0x10(a0)
	lw      v0, 0x50(s1)
	jr      ra
	sw      v0, 0x14(a0)

; portrait palettes (0x8010773C entry): a0 = side, a1 = character, a2 =
; screen row. Zangief: his 10 palettes to the same two places as vanilla.
xp_zportpal:
	andi    t8, a0, 0xFF
	andi    v0, a1, 0xFF
	li      at, ZG_CHAR
	bne     v0, at, @@van
	move    t7, ra
	jal     xp_zport
	nop
	beqz    v0, @@van
	move    ra, t7
	addiu   v0, v1, 0x80
	beqz    t9, @@row
	nop
	addiu   v0, v0, 0x140           ; VS palettes
@@row:
	move    t9, v0
	li      v1, 0x60                ; P1: palettes 0x30.. (bytes / 2 * 2)
	beqz    t8, @@copy
	nop
	li      v1, 0x1A0               ; P2: 0xD0..
@@copy:
	move    t8, v1
	move    a0, t9
	la      a1, 0x801A162C
	addu    a1, a1, t8
	jal     0x8012100C
	li      a2, 0x50
	move    a0, t9
	la      a1, 0x801A2A2C
	addu    a1, a1, t8
	jal     0x8012100C
	li      a2, 0x50
	jr      t7
	nop
@@van:
	addiu   sp, sp, -0x20
	j       0x80107744
	sw      s1, 0x14(sp)

; name call on confirm (0x8013CB88 entry): a0 = character, a1 = side.
; Zangief -> sound id 0x14 (his name, put into SELECT.EMI's bank by
; tools/zangief.py name). Tail-calls the vanilla player 0x80105CC0.
; (The Zangief bits are only ever set on the Versus select screen.)
xp_zname:
	andi    a0, a0, 0xFF
	andi    a1, a1, 0xFF                ; as vanilla
	sll     v0, a0, 2
	lui     at, 0x8017
	addu    at, at, v0
	lw      v0, -0x12C(at)          ; vanilla id (table 0x8016FED4)
	li      at, ZG_CHAR
	bne     a0, at, @@go
	lui     at, hi(XP_ZBITS)
	lbu     at, lo(XP_ZBITS)(at)
	sltu    t8, zero, a1            ; side (the player tests a1 != 0 too)
	srlv    at, at, t8
	andi    at, at, 1
	beqz    at, @@go
	nop
	li      v0, 0x14
@@go:
	j       0x80105CC0
	move    a0, v0

; in-match HUD name (built once per match by 0x8014CD50): v = the name's
; row in the HUD page (table 0x8018BF38), u = 0x80.. (P1) / 0xC0.. (P2).
; ZANGIEF is MORRIGAN's P2 copy (row 48, u 0xC0; tools/labels.py), so P2
; Morrigan reads her P1 copy. In: v0 = character. Out: v0 = row; the tile's
; u byte (P1 -1(s0), P2 -1(s1)) is fixed up. Keeps v1. Uses at, t9.
xp_zhud1:                               ; 0x8014CE38
	b       xp_zhud_test
	li      t9, 1
xp_zhud2:                               ; 0x8014CE60
	bnez    v0, @@p2z                   ; P2 Morrigan: her P1 copy
	nop
	lbu     at, -1(s1)
	nop
	addiu   at, at, -0x40
	sb      at, -1(s1)
@@p2z:
	li      t9, 2
xp_zhud_test:
	li      at, ZG_CHAR
	bne     v0, at, @@tab
	lui     at, hi(XP_ZOK)
	lbu     at, lo(XP_ZOK)(at)
	nop
	xori    at, at, 3
	bnez    at, @@tab
	lui     at, hi(XP_ZBITS)
	lbu     at, lo(XP_ZBITS)(at)
	nop
	and     at, at, t9
	beqz    at, @@tab
	li      at, 1
	bne     t9, at, @@row               ; P2 already reads u 0xC0..
	nop
	lbu     at, -1(s0)
	nop
	addiu   at, at, 0x40
	sb      at, -1(s0)
@@row:
	jr      ra
	li      v0, 48
@@tab:
	lui     at, 0x8019
	addu    at, at, v0
	jr      ra
	lbu     v0, -0x40C8(at)

; WINNER screen icon palette (0x8011008C, replaces jal 0x80110828; Dan's
; own path, taken for character 10): a0 = colour set, a1 = palette slot
; code, s0 = the winner's player struct. Zangief: palette 0 of the set from
; his palette block instead of Dan's (same slot computation as 0x80110828).
xp_zwinpal:
	li      at, P1_STRUCT
	beq     s0, at, @@side
	li      t9, 1
	li      t9, 2
@@side:
	lui     at, hi(XP_ZOK)
	lbu     at, lo(XP_ZOK)(at)
	nop
	xori    at, at, 3
	bnez    at, @@van
	lui     at, hi(XP_ZBITS)
	lbu     at, lo(XP_ZBITS)(at)
	nop
	and     at, at, t9
	beqz    at, @@van
	li      at, 1
	beq     t9, at, @@p1
	lui     v0, hi(BANK_P1 + ZG_PALOFF)
	lui     v0, hi(BANK_P2 + ZG_PALOFF)
	b       @@pal
	addiu   v0, v0, lo(BANK_P2 + ZG_PALOFF)
@@p1:
	addiu   v0, v0, lo(BANK_P1 + ZG_PALOFF)
@@pal:
	sll     a0, a0, 7
	addu    a0, v0, a0
	sll     a1, a1, 24
	sra     t9, a1, 29
	srl     a1, a1, 24
	andi    a2, a1, 0x1F
	move    a3, a2
	j       0x80108C68
	addiu   a1, t9, 3
@@van:
	j       0x80110828
	nop

.align 4
XP_ZK:
	.word   0, 0                    ; portrait block, graphics (0 = Dan's)
.endarea

; ---- select-screen chibi: Zangief's own sprites ----
; The chibis are drawn from SELECT.EMI's banks (0x80136400 picks them, then
; 0x80123960 sets the object up). For Zangief, states 23/24 (choosing /
; chosen) come from his file, loaded in the other banks (xp_zselload), and
; the colour from his palette block. Code space: 0x80153AF4 (236 bytes, a
; function with no references that never runs: coverage over boot, menus,
; Versus, a whole Arcade run with its ending, Street Puzzle and the option
; menus). (0x8013BBB4, used here before, is NOT free: its second half is a
; function the Arcade calls between matches; overwriting it hung Arcade.)
.org 0x80153AF4
.area 0x80153BE0 - 0x80153AF4, 0

; from xp_zstate (state 23/24, Zangief side t8, a1 = state * 4, s1 = the
; object): only for the select-state start (0x80136430, return 0x80136438).
xp_zselst:
	li      at, 0x80136438
	bne     ra, at, @@ret
	move    t7, ra
	jal     xp_zport
	nop
	beqz    v0, @@ret
	move    ra, t7
	addu    t9, v0, a1
	lw      t9, ZG_LISTOFF(t9)
	nop
	addu    s0, v0, t9              ; his script
	la      at, XP_ZSEL
	sw      v1, 0(at)               ; graphics
	sw      v0, 4(at)               ; record bank
@@ret:
	jr      ra
	nop

; object setup (0x8013648C, replaces jal 0x80123960): a2/a3 = his banks
xp_zselbank:
	la      at, XP_ZSEL
	lw      v0, 4(at)
	nop
	beqz    v0, @@go
	nop
	lw      a2, 0(at)
	move    a3, v0
	sw      zero, 4(at)
@@go:
	j       0x80123960
	nop

; select chibi palette (0x8010789C entry): a0 = side, a1 = character, a2 =
; colour set; palette 0 of the set to bank 3, slot 5 (P1) / 12 (P2).
xp_zchibipal:
	andi    t8, a0, 0xFF
	andi    v0, a1, 0xFF
	li      at, ZG_CHAR
	bne     v0, at, @@van
	move    t7, ra
	jal     xp_zport
	nop
	beqz    v0, @@van
	move    ra, t7
	li      a3, 5
	beqz    t8, @@p1
	nop
	li      a3, 12
@@p1:
	andi    a2, a2, 0xFF
	li      at, xp_mv_ret           ; called by the cursor move (xprime.asm):
	bne     ra, at, @@set           ; not chosen yet, show his own colours
	nop
	li      a2, 0                   ; (set 0 = original, see tools/zangief.py)
@@set:
	sll     a2, a2, 7
	addu    a0, v0, a2
	addiu   a0, a0, ZG_PALOFF
	li      a1, 3
	j       0x80108C68
	move    a2, a3
@@van:
	addiu   sp, sp, -0x18
	j       0x801078A4
	sw      ra, 0x10(sp)

.align 4
XP_ZSEL:
	.word   0, 0                    ; graphics, record bank (0 = none pending)
.endarea

; hooks for his own file and Pocket Fighter assets (build.sh)
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
.org 0x8012BF7C
	jal     xp_zselload             ; (delay slot: a0 = 0x39, SELECT.EMI)
.org 0x80128768
	jal     xp_zselbusy
.org 0x80123BF0
	jal     xp_zlist
	lw      s0, 0(at)
.org 0x80123C34
	jal     xp_zkid
	nop
	nop
	nop
	sw      s4, 0x18(a0)
	nop
.org 0x8010773C
	j       xp_zportpal
	nop
.org 0x8013648C
	jal     xp_zselbank
.org 0x8010789C
	j       xp_zchibipal
	nop
.org 0x8013CB88
	j       xp_zname
	nop
.org 0x8011008C
	jal     xp_zwinpal
.org 0x8014CE38
	jal     xp_zhud1
	nop
	nop
	nop
.org 0x8014CE60
	jal     xp_zhud2
	nop
	nop
	nop
.org 0x8016EFFA                         ; Dan's voice table, unused indices 7/8
	.byte   14, 15                  ; Zangief's "in trouble" cries (ZG_EVENTS)

; ---- Zangief's stage and music (step 6) ----
; per-stage tables, repointed to the 12-entry copies
.org 0x801079A4
	lui     at, hi(xp_stg_load)
	addiu   at, at, lo(xp_stg_load)
.org 0x80107A20
	lui     at, hi(xp_stg_init)
	addiu   at, at, lo(xp_stg_init)
.org 0x80107A94
	lui     at, hi(xp_stg_frame)
	addiu   at, at, lo(xp_stg_frame)
.org 0x8010EDF4
	lui     at, hi(xp_stg_objs)
	addiu   at, at, lo(xp_stg_objs)
.org 0x8012BE6C
	lui     at, hi(xp_stg_song)
	addiu   at, at, lo(xp_stg_song)
; XA player: song -> entry
.org 0x80106320
	jal     xp_songent
	nop
	.fill   10 * 4, 0
; entry 47: file index 0xDD (its file id is read from 0x80166060 + 2 * 0xDD
; = the unused upper half of entry 47 itself), channel 6, looped length
.org 0x80166218
	.halfword (0xDD << 8) | ZG_XA_CHAN
	.halfword ZG_XAFILE
.org 0x8016606C + 47 * 4
	.word   0x80000000 | ZG_XA_LEN

; ============================================================================
; ARCADE (step 7)
; xp_frame (every frame, from the main loop's call of the loader step
; 0x8010436C): XP_ZOK = 3 if MODE is Versus (3) or Arcade (1, not Street
; Puzzle: XP_STREET), else 0; XP_ZOKN the same for MODE_NEXT. The Zangief
; tests read these instead of the mode, so they hold in both modes.
; Code space: 0x8010868C-0x80108924, six functions with no references that
; never run (coverage: boot, menus, Versus, a whole Arcade run with its
; ending, Street Puzzle, option menus, training demo).
; ============================================================================
XP_STREET equ 0x8019C3F5                ; 1 in Street Puzzle

.org 0x80102458
	jal     xp_frame                ; was jal 0x8010436C

.org 0x8010868C
.area 0x80108924 - 0x8010868C, 0
xp_frame:
	lui     t0, hi(MODE)
	lbu     t6, lo(MODE)(t0)
	lbu     t2, lo(MODE_NEXT)(t0)
	lbu     t3, lo(XP_STREET)(t0)
	la      t4, XP_ZOK
	li      t5, 3
	li      t7, 2
@@loop:
	beq     t6, t5, @@ok
	li      t8, 1
	bne     t6, t8, @@no
	nop
	beqz    t3, @@ok                ; Arcade, not Street Puzzle
	nop
@@no:
	b       @@st
	move    t9, zero
@@ok:
	li      t9, 3
@@st:
	sb      t9, 0(t4)
	addiu   t4, t4, 1
	addiu   t7, t7, -1
	bnez    t7, @@loop
	move    t6, t2                  ; second round: MODE_NEXT
	lbu     t9, -2(t4)              ; XP_ZOK
	la      t8, XP_ZEND
	bnez    t9, @@keep
	nop
	sb      zero, 0(t8)             ; out of Versus / Arcade: no staff roll
@@keep:
	j       0x8010436C
	nop

; ---- Arcade opponents ----
; The CPU's character is set at 0x8012CCD4 (first opponent of a match set-up)
; and in the delay slot of 0x8012CEB8 (next opponent); both then call
; 0x8012CDBC with a2 = the CPU's player struct. xp_zcpu sets that struct's
; Zangief bit: in Arcade, when the opponent is Dan (10, the 9th opponent of
; every run), Zangief comes instead one time in two ("challenger"), unless
; the player is Zangief himself; any other opponent clears the bit.
xp_zopp1:
	sb      a1, 0x68(s2)            ; (replaced instruction)
	j       xp_zcpu
	move    a2, s2

xp_zopp2:
	addiu   sp, sp, -0x18
	sw      ra, 0x10(sp)
	jal     xp_zcpu
	nop
	lw      ra, 0x10(sp)
	addiu   sp, sp, 0x18            ; (load delay: not j right after lw)
	j       0x8012CDBC
	nop

; a2 = the CPU's struct; leaf, t0-t9 only
xp_zcpu:
	lui     t0, hi(MODE)
	lbu     t1, lo(MODE)(t0)
	lbu     t2, lo(XP_STREET)(t0)
	li      t3, 1
	bne     t1, t3, @@ret           ; Arcade only
	nop
	bnez    t2, @@ret
	lbu     t2, 0x6C(a2)            ; 1 = played by the CPU
	nop
	beqz    t2, @@ret               ; a human (Arcade challenger): his own choice
	li      t4, P1_STRUCT
	beq     a2, t4, @@bit
	li      t4, 1
	li      t4, 2
@@bit:
	la      t5, XP_ZBITS
	lbu     t6, 0(t5)
	nor     t7, t4, zero
	and     t7, t6, t7              ; this side's bit cleared
	lbu     t8, 0x68(a2)
	li      t9, ZG_CHAR
	bne     t8, t9, @@store
	xori    t8, t4, 3
	and     t8, t6, t8
	bnez    t8, @@store             ; the player is Zangief: plain Dan
	lui     t8, 0x1F80
	lhu     t8, 0x1100(t8)          ; root counter 0: one time in two
	nop
	andi    t8, t8, 1
	beqz    t8, @@store
	nop
	or      t7, t7, t4
@@store:
	sb      t7, 0(t5)
@@ret:
	jr      ra
	nop

; ---- Zangief's Arcade order ----
; 0x8012CD18 copies the run's opponent order (one of 8 rows of 0x8016D49C)
; to 0x8019F45C; its jr ra at 0x8012CDB4 comes here. When the player is
; Zangief, Felicia (6), his rival in Pocket Fighter, is moved to the 8th
; place: the last regular opponent, before Dan and the bosses.
xp_zorder:
	la      t0, XP_ZOK
	lbu     t1, 0(t0)               ; XP_ZOK (match) or XP_ZOKN (select)
	lbu     t2, 1(t0)
	nop
	or      t1, t1, t2
	beqz    t1, @@ret
	la      t0, XP_ZBITS
	lbu     t1, 0(t0)
	lui     t2, 0x801B
	lbu     t3, -0x1A98(t2)         ; P1 character (0x801AE568)
	lbu     t4, -0x17EC(t2)         ; P2 character (0x801AE814)
	xori    t3, t3, ZG_CHAR
	sltiu   t3, t3, 1
	xori    t4, t4, ZG_CHAR
	sltiu   t4, t4, 1
	sll     t4, t4, 1
	or      t3, t3, t4
	and     t1, t1, t3
	beqz    t1, @@ret
	la      t0, 0x8019F45C
	move    t2, zero
	li      t5, 6
@@find:
	addu    t3, t0, t2
	lbu     t4, 0(t3)
	nop
	beq     t4, t5, @@swap
	addiu   t2, t2, 1
	sltiu   t4, t2, 8
	bnez    t4, @@find
	nop
	b       @@ret
	nop
@@swap:
	lbu     t4, 7(t0)
	sb      t5, 7(t0)
	sb      t4, 0(t3)
@@ret:
	jr      ra
	nop

.align 4
XP_ZOK:
	.byte   0                       ; from MODE
XP_ZOKN:
	.byte   0                       ; from MODE_NEXT
.endarea

.org 0x8012CCD4
	jal     xp_zopp1                ; was sb a1, 0x68(s2)
.org 0x8012CEB8
	jal     xp_zopp2                ; was jal 0x8012CDBC (delay: sb v0, 0x68(s2))
.org 0x8012CDB4
	j       xp_zorder               ; was jr ra

; ============================================================================
; STAFF ROLL FIGURE (step 7)
; The staff roll (0x801102D8) shows the player's character beside the
; credits: for most characters a figure script from 0x80189818, a list of
; child sprites with portrait palettes, in the figure banks every ENDINGnn
; file loads (0x800A1000 graphics, 0x800B1000 records); Dan gets a small
; single frame (0x80110364 path). For Zangief, ZG_END.EMI (tools/zangief.py
; build_end: his Pocket Fighter opening picture) is loaded over those banks
; right after the ENDING file (ending state 0 / 1 waits for the loader at
; 0x80143A78), and the figure set-up takes the regular path with a script
; whose list is Dan's portrait list 20: xp_zlist, xp_zkid and xp_zportpal
; then use the block at 0x800A1000 (xp_zport, while XP_ZEND is set).
; Code space: 0x801080BC-0x801082BC, a function with no references that
; never runs (coverage: boot, menus, Versus, a whole Arcade run with its
; ending, Street Puzzle, option menus).
; ============================================================================

.org 0x801080BC
.area 0x801082BC - 0x801080BC, 0

; v0 = 1 if the human player is Zangief (his side's bit and Dan's slot; the
; CPU's bit is cleared for any opponent but Dan). Leaf: v0, v1, at.
xp_zendme:
	la      at, XP_ZBITS
	lbu     at, 0(at)
	lui     v0, 0x801B
	lbu     v1, -0x1A98(v0)         ; P1 character
	lbu     v0, -0x17EC(v0)         ; P2 character
	xori    v1, v1, ZG_CHAR
	sltiu   v1, v1, 1
	xori    v0, v0, ZG_CHAR
	sltiu   v0, v0, 1
	sll     v0, v0, 1
	or      v0, v0, v1
	and     v0, v0, at
	jr      ra
	sltu    v0, zero, v0

; ending state 0 / 1, "loader busy?" (0x80143A78, replaces jal 0x80104354):
; once the ENDING file is in, load ZG_END.EMI over the figure banks when the
; player is Zangief, and report busy until it is in too.
xp_zendbusy:
	addiu   sp, sp, -0x18
	sw      ra, 0x10(sp)
	jal     0x80104354
	nop
	bnez    v0, @@ret
	la      t0, XP_ZEPEND
	lb      t1, 0(t0)
	nop
	bnez    t1, @@finish
	nop
	jal     xp_zendme
	nop
	beqz    v0, @@ret
	move    v0, zero
	lui     at, 0x801C
	lw      t1, -0x7E80(at)         ; keep the load destinations
	lw      t2, -0x7E7C(at)
	sw      t1, 4(t0)
	sw      t2, 8(t0)
	li      t1, END_BLOCK
	li      t2, END_RECS
	sw      t1, -0x7E80(at)
	sw      t2, -0x7E7C(at)
	li      t1, 1
	sb      t1, 0(t0)
	jal     0x801043C0
	li      a0, ZG_ENDFILE
	b       @@ret
	li      v0, 1
@@finish:
	sb      zero, 0(t0)
	lw      t1, 4(t0)
	lw      t2, 8(t0)
	lui     at, 0x801C
	sw      t1, -0x7E80(at)
	sw      t2, -0x7E7C(at)
	move    v0, zero
@@ret:
	lw      ra, 0x10(sp)
	nop
	jr      ra
	addiu   sp, sp, 0x18

; xp_zport, staff roll case: while XP_ZEND is set, Zangief's figure block
; at 0x800A1000 (v0 != 0, v1 = the block, t9 = 0: list at +0, palettes at
; +0x80).
xp_zportend:
	la      v0, XP_ZEND
	lbu     v0, 0(v0)
	nop
	bnez    v0, @@end
	lui     v1, hi(END_BLOCK)
	j       xp_zport_sel
	nop
@@end:
	addiu   v1, v1, lo(END_BLOCK)
	jr      ra
	move    t9, zero

; staff roll figure set-up, Dan test (0x80110314, was beq v0, v1, 0x80110364;
; delay slot move a0, zero): v0 = the character, v1 = 10. With Zangief's
; block in, the regular path, and XP_ZEND set for the portrait hooks.
xp_zendfig:
	bne     v0, v1, @@reg
	lui     at, hi(END_BLOCK + 0x7C)
	lw      t8, lo(END_BLOCK + 0x7C)(at)
	li      t9, END_MAGIC
	bne     t8, t9, @@dan
	li      t8, 1
	la      at, XP_ZEND
	sb      t8, 0(at)
@@reg:
	j       0x8011031C
	nop
@@dan:
	j       0x80110364
	nop

; staff roll figure script (0x801103E8, was jal 0x80123960; s0 = character
; * 4, a0 = its script): Zangief's own while XP_ZEND is set.
xp_zendscr:
	la      at, XP_ZEND
	lbu     at, 0(at)
	nop
	beqz    at, @@go
	nop
	la      a0, xp_zendscript
@@go:
	j       0x80123960
	nop

; a1 = state * 4: set that state's script of his file on s0
xp_zhscript:
	li      a3, ZH_REC
	addu    a0, a3, a1
	lw      a0, ZG_LISTOFF(a0)
	li      a2, ZH_GFX
	addu    a0, a0, a3
	j       0x80123960
	move    a1, s0

.align 4
xp_zendscript:                          ; as the others': a figure list (20)
	.word   0xC0000FFF, 20, 0, 0
	.word   0xC0000FFF, 20, 0, 0
XP_ZEPEND:
	.word   0, 0, 0                 ; state (1 = loading), saved destinations
XP_ZEND:
	.byte   0                       ; 1: staff roll figure from the block
.endarea

; ---- HARD finale ----
; On HARD, after the staff roll, HARD_END.EMI (over P1's banks) brings the
; cast in under the CAPCOM logo: 12 objects (type 0x41, index 0-11, spawned
; by 0x8011F004) that fade in one after the other (delay 0x8016C828, x / y
; 0x8016C7C8, priority / facing 0x8016C7B0, palette 0x8016C840, scripts
; 0x8016C7F8 and, on landing, 0x8016C880). Zangief is a 13th: his own file
; is loaded after HARD_END into the ENDING leftovers (free then), and index
; 12 gets his idle script, his palette, and the gap in the middle of the
; back row, under the logo; he comes last, flexes for about two seconds and
; then stays still.
; Code space: 0x80156360-0x801564B0, a function with no references that
; never runs (coverage as above, plus a whole HARD finale).
.org 0x80156360
.area 0x801564B0 - 0x80156360, 0
xp_zhbusy:                              ; 0x80144028, was jal 0x80104354
	addiu   sp, sp, -0x18
	sw      ra, 0x10(sp)
	jal     0x80104354
	nop
	bnez    v0, @@ret
	la      t0, XP_ZEPEND
	lb      t1, 0(t0)
	nop
	bnez    t1, @@finish
	lui     at, 0x801C
	lw      t1, -0x7E80(at)         ; keep the load destinations
	lw      t2, -0x7E7C(at)
	sw      t1, 4(t0)
	sw      t2, 8(t0)
	li      t1, ZH_GFX
	li      t2, ZH_REC
	sw      t1, -0x7E80(at)
	sw      t2, -0x7E7C(at)
	li      t1, 1
	sb      t1, 0(t0)
	jal     0x801043C0
	li      a0, ZG_FILE
	b       @@ret
	li      v0, 1
@@finish:
	sb      zero, 0(t0)
	lw      t1, 4(t0)
	lw      t2, 8(t0)
	sw      t1, -0x7E80(at)
	sw      t2, -0x7E7C(at)
	move    v0, zero
@@ret:
	lw      ra, 0x10(sp)
	nop
	jr      ra
	addiu   sp, sp, 0x18

; object init, after the common part (0x8011ED40, was lbu v0, 7(s0) /
; lbu a3, 3(s0)); s0 = the object, s1 / ra saved by the host
xp_zhinit:
	lbu     v0, 7(s0)
	lbu     a3, 3(s0)
	li      at, 12
	beq     a3, at, @@z
	nop
	j       0x8011ED48
	nop
@@z:
	sb      zero, 6(s0)
	addiu   v0, v0, 1
	sb      v0, 7(s0)
	li      v0, ZH_DELAY
	sh      v0, 0x10(s0)
	li      v0, ZH_PRIO
	sb      v0, 9(s0)
	li      v0, ZH_FACE
	sb      v0, 0xB(s0)
	li      v0, ZH_X - 12
	sh      v0, 0x3E(s0)
	li      v0, ZH_Y
	sh      v0, 0x42(s0)
	li      v0, 2
	sb      v0, 0x45(s0)
	sb      a3, 0xD(s0)
	li      a0, ZH_REC + ZG_PALOFF         ; his own colours (set 0)
	li      a1, 3
	jal     0x80108C68
	li      a2, 12
	li      a1, 0                   ; idle
	jal     xp_zhscript
	nop
	j       0x8011EE10
	nop

; landing (0x8011EF78, was lb v1, 3(s0) / ori v0, zero, 0xB): index 11
; keeps its script, 12 (Zangief) takes his finale script, the others the table's
xp_zhland:
	lb      v1, 3(s0)
	li      v0, 12
	beq     v1, v0, @@z
	li      v0, 0xB
	beq     v1, v0, @@keep
	nop
	j       0x8011EF88
	sll     v0, v1, 2
@@z:
	jal     xp_zhscript
	li      a1, 58 * 4              ; finale: flexes ~2 s, then still (zangief.py)
@@keep:
	j       0x8011EFB0
	nop
.endarea

.org 0x80143A78
	jal     xp_zendbusy
.org 0x80110314
	j       xp_zendfig              ; (delay slot: move a0, zero)
.org 0x801103E8
	jal     xp_zendscr              ; (delay slot: ori a3, a3, 0x1000)
.org 0x80144028
	jal     xp_zhbusy
.org 0x8011F048
	slti    v0, s0, 13              ; 12 + Zangief
.org 0x8011ED40
	j       xp_zhinit
	nop
.org 0x8011EF78
	j       xp_zhland
	nop
