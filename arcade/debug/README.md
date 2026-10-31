# Test core for the arcade set

The test scripts (`tools/cps2emu.py`) drive a mame2003-plus libretro core built
with a small debug hook: 68000 memory access and PC breakpoints for the
harness. It is not part of the set and not part of the PR to mame2003-plus.

To build it, in a copy of mame2003-plus-libretro:

1. copy `xdbg68k.c` to `src/mame2003/`;
2. in `Makefile.common`, add `$(CORE_DIR)/mame2003/xdbg68k.c \` after `mame2003.c`;
3. in `src/cpu/m68000/m68kmame.h`, replace
   `#define M68K_INSTRUCTION_CALLBACK() CALL_MAME_DEBUG` with
   `extern void xdbg_m68k_hook(unsigned pc);` and
   `#define M68K_INSTRUCTION_CALLBACK() xdbg_m68k_hook(REG_PC)`;
4. in `link.T`, export `xdbg_*` next to `retro_*`;
5. `make`, then point `LR_CORE` at `mame2003_plus_libretro.so`.
