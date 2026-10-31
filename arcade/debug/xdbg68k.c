/* debug hooks for the test harness (not part of the core) */
#include "driver.h"
#include "cpu/m68000/m68k.h"
#define NBP 32
static unsigned bps[NBP]; static int nbp;
typedef struct { unsigned pc, frame; unsigned d[8], a[8]; } hit_t;
static hit_t hits[256]; static int nhits; static unsigned curframe;
void xdbg_set_frame(unsigned f) { curframe = f; }
unsigned xdbg_r8(unsigned a) { return cpunum_read_byte(0, a); }
void xdbg_w8(unsigned a, unsigned v) { cpunum_write_byte(0, a, v); }
void xdbg_rbytes(unsigned a, unsigned char *out, unsigned n) { unsigned i; for (i = 0; i < n; i++) out[i] = cpunum_read_byte(0, a + i); }
int xdbg_add_bp(unsigned pc) { if (nbp < NBP) bps[nbp++] = pc; return nbp; }
void xdbg_clear(void) { nbp = 0; nhits = 0; }
int xdbg_hits(void) { return nhits; }
void *xdbg_hit(int i) { return &hits[i]; }
void xdbg_clear_hits(void) { nhits = 0; }
void xdbg_m68k_hook(unsigned pc)
{
	int i;
	if (!nbp || cpu_getactivecpu() != 0) return;
	for (i = 0; i < nbp; i++) if (bps[i] == pc) {
		if (nhits < 256) {
			hit_t *h = &hits[nhits++]; int r;
			h->pc = pc; h->frame = curframe;
			for (r = 0; r < 8; r++) { h->d[r] = m68k_get_reg(NULL, M68K_REG_D0 + r); h->a[r] = m68k_get_reg(NULL, M68K_REG_A0 + r); }
		}
		return;
	}
}
