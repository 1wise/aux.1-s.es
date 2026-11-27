#!/usr/bin/env python3
# Timestamp: 2026-11-27 | Version: 8.0.1-beta.7
# Author & Credits: https://www.alawise.es/1-s
"""Use the shared ISO finisher, including the Excalibur WAN boot entry."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('aux_iso_finish', Path(__file__).resolve().parents[1] / 'iso-assist/finish.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
configura = mod.configura
main = mod.main

if __name__ == '__main__':
    main()
