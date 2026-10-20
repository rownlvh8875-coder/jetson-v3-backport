/*
 * Exact uint8 -> IEEE binary16 LUT conversion, CPU only.
 * Adapted from tjdgus200/openpilot third_party/jetlink/jetlink/input_cast.c
 * commit a890f6df1bd3eb0478754c68d8b5f92f15e8b722 (2026-10-20 review).
 * No SIMD/architecture assumptions.
 *
 * MIT License
 * Copyright (c) 2026 Zeph Leggett
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */
#include <stddef.h>
#include <stdint.h>

void jetlink_u8_f16(const uint8_t *restrict src, uint16_t *restrict dst,
                    const uint16_t *restrict table, size_t n) {
  for (size_t i = 0; i < n; ++i) dst[i] = table[src[i]];
}
