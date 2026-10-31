/* debug hooks for the test harness (not part of the core):
   68000 memory access, PC breakpoints and memory watchpoints on CPU 0 */
#include "driver.h"
#include "cpu/m68000/m68k.h"
#include "cpu/m68000/m68kmame.h"
#define NBP 32
#define NW 8
static unsigned bps[NBP]; static int nbp;
static unsigned wlo[NW], whi[NW], wkind[NW]; static int nw;
typedef struct { unsigned kind, pc, frame, addr, value, size; unsigned d[8], a[8]; } hit_t;
static hit_t hits[1024]; static int nhits; static unsigned curframe;
static struct m68k_memory_interface orig; static int hooked;
void xdbg_set_frame(unsigned f) { curframe = f; }
unsigned xdbg_r8(unsigned a) { return cpunum_read_byte(0, a); }
void xdbg_w8(unsigned a, unsigned v) { cpunum_write_byte(0, a, v); }
void xdbg_rbytes(unsigned a, unsigned char *out, unsigned n) { unsigned i; for (i = 0; i < n; i++) out[i] = cpunum_read_byte(0, a + i); }
int xdbg_add_bp(unsigned pc) { if (nbp < NBP) bps[nbp++] = pc; return nbp; }
int xdbg_add_watch(unsigned lo, unsigned hi, unsigned kind) { if (nw < NW) { wlo[nw] = lo; whi[nw] = hi; wkind[nw] = kind; nw++; } return nw; }
void xdbg_clear(void) { nbp = 0; nw = 0; nhits = 0; }
int xdbg_hits(void) { return nhits; }
void *xdbg_hit(int i) { return &hits[i]; }
void xdbg_clear_hits(void) { nhits = 0; }

static void rec(unsigned kind, unsigned pc, unsigned addr, unsigned value, unsigned size)
{
	hit_t *h; int r;
	if (nhits >= 1024) return;
	h = &hits[nhits++];
	h->kind = kind; h->pc = pc; h->frame = curframe; h->addr = addr; h->value = value; h->size = size;
	for (r = 0; r < 8; r++) { h->d[r] = m68k_get_reg(NULL, M68K_REG_D0 + r); h->a[r] = m68k_get_reg(NULL, M68K_REG_A0 + r); }
}
static void chk(unsigned kind, unsigned addr, unsigned value, unsigned size)
{
	int i;
	if (cpu_getactivecpu() != 0) return;
	addr &= 0xffffff;
	for (i = 0; i < nw; i++)
		if ((wkind[i] & kind) && addr + size > wlo[i] && addr <= whi[i])
			{ rec(kind, m68k_get_reg(NULL, M68K_REG_PPC), addr, value, size); return; }
}
static data8_t  w_r8(offs_t a)  { data8_t v = orig.read8(a); chk(1, a, v, 1); return v; }
static data16_t w_r16(offs_t a) { data16_t v = orig.read16(a); chk(1, a, v, 2); return v; }
static data32_t w_r32(offs_t a) { data32_t v = orig.read32(a); chk(1, a, v, 4); return v; }
static void w_w8(offs_t a, data8_t v)   { chk(2, a, v, 1); orig.write8(a, v); }
static void w_w16(offs_t a, data16_t v) { chk(2, a, v, 2); orig.write16(a, v); }
static void w_w32(offs_t a, data32_t v) { chk(2, a, v, 4); orig.write32(a, v); }

void xdbg_m68k_hook(unsigned pc)
{
	int i;
	if (cpu_getactivecpu() != 0) return;
	if (nw && m68k_memory_intf.read8 != w_r8) {
		orig = m68k_memory_intf; hooked = 1;
		m68k_memory_intf.read8 = w_r8; m68k_memory_intf.read16 = w_r16; m68k_memory_intf.read32 = w_r32;
		m68k_memory_intf.write8 = w_w8; m68k_memory_intf.write16 = w_w16; m68k_memory_intf.write32 = w_w32;
	}
	for (i = 0; i < nbp; i++) if (bps[i] == pc) { rec(0, pc, 0, 0, 0); return; }
}
