#!/usr/bin/env python3
# Timestamp: 2026-10-13 | Version: 1.1.0
# Author & Credits: https://www.alawise.es/1-s
"""Build original 5x7 PXE glyphs locally; generation ships the prebuilt font."""
from pathlib import Path
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

GLYPHI = {
    'P': ('11110', '10001', '10001', '11110', '10000', '10000', '10000'),
    'X': ('10001', '10001', '01010', '00100', '01010', '10001', '10001'),
    'E': ('11111', '10000', '10000', '11110', '10000', '10000', '11111'),
    'greater': ('10000', '01000', '00100', '00010', '00100', '01000', '10000'),
    'underscore': ('00000', '00000', '00000', '00000', '00000', '00000', '11111'),
}


def main():
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(['.notdef', 'space', *GLYPHI])
    fb.setupCharacterMap({32: 'space', 62: 'greater', 69: 'E', 80: 'P', 88: 'X', 95: 'underscore'})
    glyphs = {}
    for name in ['.notdef', 'space', *GLYPHI]:
        pen = TTGlyphPen(None)
        for row, bits in enumerate(GLYPHI.get(name, ())):
            for col, bit in enumerate(bits):
                if bit == '1':
                    x, y = col * 100 + 50, (6 - row) * 100
                    pen.moveTo((x, y))
                    pen.lineTo((x, y + 85))
                    pen.lineTo((x + 85, y + 85))
                    pen.lineTo((x + 85, y))
                    pen.closePath()
        glyphs[name] = pen.glyph()
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({name: (600, 50) for name in glyphs})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({'familyName': 'PXE Bits', 'styleName': 'Regular',
        'uniqueFontIdentifier': '1wise-PXE-Bits-1.1.0', 'fullName': 'PXE Bits Regular',
        'psName': 'PXEBits-Regular', 'version': 'Version 1.1',
        'copyright': 'Original pixel glyphs. Author & Credits: https://www.alawise.es/1-s'})
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupPost()
    fb.setupMaxp()
    # Fixed timestamps let community rebuilds compare the same font bytes.
    fb.font['head'].created = fb.font['head'].modified = 3874694400
    fb.font.recalcTimestamp = False
    output = Path(__file__).resolve().parents[1] / 'assets/pxe-bits.ttf'
    fb.save(output)
    print(output.name)


if __name__ == '__main__':
    main()
