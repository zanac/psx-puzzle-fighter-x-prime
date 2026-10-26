#!/bin/sh
# Build the instrumented pcsx_rearmed libretro core used for research.
# usage: emu/build.sh            (clones into emu/pcsx_rearmed)
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
REV=c8816799b50388e61cfe237fe2cdbb7d8175f20a
cd "$HERE"
if [ ! -d pcsx_rearmed ]; then
	git clone https://github.com/libretro/pcsx_rearmed.git
	cd pcsx_rearmed
	git checkout "$REV"
	git submodule update --init --depth 1
	git apply "$HERE/pcsx_rearmed-xdbg.patch"
else
	cd pcsx_rearmed
fi
make -f Makefile.libretro -j"$(nproc 2>/dev/null || echo 2)"
echo "built: $HERE/pcsx_rearmed/pcsx_rearmed_libretro.so"
