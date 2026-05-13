#!/usr/bin/env python3
"""
Merge an arm64 .app bundle with x86_64 Mach-O counterparts into a
universal2 .app bundle using lipo, then ad-hoc sign the result.

Usage:
  python merge_ci.py <arm64_app> <x86_bin_dir> <output_app>

  arm64_app   – path to the arm64 .app bundle (full contents)
  x86_bin_dir – directory mirroring the .app layout but containing
                only the x86_64 Mach-O files extracted from the x86_64
                build (same relative paths as inside the bundle)
  output_app  – destination path for the universal2 .app bundle
"""

import argparse
import os
import shutil
import subprocess
import sys


def arch_of(path):
    try:
        out = subprocess.check_output(
            ['file', path], stderr=subprocess.DEVNULL
        ).decode()
        if 'universal binary' in out:
            return 'universal'
        if 'arm64' in out:
            return 'arm64'
        if 'x86_64' in out:
            return 'x86_64'
    except Exception:
        pass
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('arm64_app',   help='arm64 .app bundle')
    ap.add_argument('x86_bin_dir', help='directory with x86_64 Mach-O files (same layout as bundle)')
    ap.add_argument('output_app',  help='output universal2 .app path')
    args = ap.parse_args()

    if os.path.exists(args.output_app):
        shutil.rmtree(args.output_app)
    print(f'Copying arm64 bundle → {args.output_app}')
    shutil.copytree(args.arm64_app, args.output_app, symlinks=True)

    merged = skipped = errors = 0
    for root, _dirs, files in os.walk(args.output_app):
        for fname in files:
            out_path = os.path.join(root, fname)
            if os.path.islink(out_path):
                continue

            arch = arch_of(out_path)
            if arch == 'universal':
                continue  # already fat – nothing to do
            if arch not in ('arm64', 'x86_64'):
                continue  # not a Mach-O binary

            rel      = os.path.relpath(out_path, args.output_app)
            x86_path = os.path.join(args.x86_bin_dir, rel)
            if not os.path.exists(x86_path):
                skipped += 1
                continue

            x86_arch = arch_of(x86_path)
            if x86_arch == 'universal':
                # x86 artifact is already fat; use it as-is (best we can do)
                shutil.copy2(x86_path, out_path)
                merged += 1
                continue

            tmp = out_path + '._orig'
            shutil.copy2(out_path, tmp)
            try:
                order = [tmp, x86_path] if arch == 'arm64' else [x86_path, tmp]
                subprocess.run(
                    ['lipo', '-create'] + order + ['-output', out_path],
                    check=True, capture_output=True,
                )
                os.remove(tmp)
                merged += 1
                print(f'  lipo  {rel}')
            except subprocess.CalledProcessError as exc:
                shutil.move(tmp, out_path)
                print(f'  WARN  lipo failed for {rel}: '
                      f'{exc.stderr.decode().strip()}', file=sys.stderr)
                errors += 1

    print(f'\nMerged {merged} | skipped (no x86_64) {skipped} | errors {errors}')

    print('Ad-hoc signing...')
    subprocess.run(
        ['codesign', '--force', '--deep', '--sign', '-', args.output_app],
        check=True,
    )
    print('Signed.')


if __name__ == '__main__':
    main()
