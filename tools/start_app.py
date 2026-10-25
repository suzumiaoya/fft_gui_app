"""Prepare an isolated environment from pyproject.toml and run the GUI."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / '.venv'
ENV_PYTHON = ENV / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
if os.name == 'nt' and (ENV / 'python.exe').is_file():
    ENV_PYTHON = ENV / 'python.exe'  # Conda environments use a different layout.


def project_config():
    if sys.version_info < (3, 11):
        raise RuntimeError('Python 3.11+ is needed to read pyproject.toml; this app requires 3.13+.')
    import tomllib

    with (ROOT / 'pyproject.toml').open('rb') as stream:
        return tomllib.load(stream)['project']


def check_python(project):
    # The project's bootstrap requirement is a simple minimum version.
    # Fail explicitly if that format changes rather than silently accepting it.
    requirement = project['requires-python']
    match = re.fullmatch(r'>=\s*(\d+(?:\.\d+){1,2})', requirement.strip())
    if not match:
        raise RuntimeError(f'Unsupported bootstrap Python requirement: {requirement}')
    minimum = tuple(int(part) for part in match[1].split('.'))
    if sys.version_info[:len(minimum)] < minimum:
        raise RuntimeError(f'Python {sys.version.split()[0]} does not satisfy {requirement}.')
    print(f'Python {sys.version.split()[0]} satisfies {requirement}.', flush=True)


def run(arguments):
    subprocess.run(arguments, cwd=ROOT, check=True)


def prepare_and_launch(check_only):
    project = project_config()
    check_python(project)
    if Path(sys.prefix).resolve() != ENV.resolve():
        if not ENV_PYTHON.is_file():
            print(f'Creating virtual environment: {ENV}', flush=True)
            run([sys.executable, '-m', 'venv', str(ENV)])
        arguments = [str(ENV_PYTHON), str(Path(__file__).resolve())]
        if check_only:
            arguments.append('--check-only')
        return subprocess.call(arguments, cwd=ROOT)

    # Tk is supplied by Python, not by pip. Check it before downloading packages.
    try:
        import tkinter
    except ImportError as error:
        raise RuntimeError('Tcl/Tk is unavailable. Repair Python and install Tcl/Tk support.') from error
    try:
        tkinter.Tcl()
    except tkinter.TclError as error:
        raise RuntimeError('Tcl/Tk is unavailable. Repair Python and install Tcl/Tk support.') from error

    if subprocess.call([sys.executable, '-m', 'pip', '--version'], cwd=ROOT) != 0:
        run([sys.executable, '-m', 'ensurepip', '--upgrade'])

    # pip bundles the PEP 440/508 parser, so no extra bootstrap dependency is needed.
    from importlib.metadata import PackageNotFoundError, version
    from pip._vendor.packaging.requirements import Requirement

    missing = []
    for specification in project.get('dependencies', []):
        requirement = Requirement(specification)
        if requirement.marker and not requirement.marker.evaluate():
            continue
        try:
            installed = version(requirement.name)
        except PackageNotFoundError:
            installed = None
        if installed is None or not requirement.specifier.contains(installed):
            missing.append(specification)

    if missing:
        print('Installing missing or incompatible dependencies: ' + ', '.join(missing), flush=True)
        # Let pip resolve the entire declared dependency set together.
        run([sys.executable, '-m', 'pip', 'install', *project['dependencies']])
    else:
        print('All declared dependencies are already satisfied.', flush=True)
    run([sys.executable, '-m', 'pip', 'check'])
    # Metadata alone cannot detect a broken native library or Tk integration.
    run([sys.executable, '-c',
         'import tkinter, customtkinter, numpy, pandas, scipy; '
         'from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg'])
    if check_only:
        print('Environment check passed. GUI was not opened.', flush=True)
        return 0
    print('Starting FFT GUI App...', flush=True)
    return subprocess.call([sys.executable, '-m', 'fft_gui_app'], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true', help='Only check Python compatibility.')
    parser.add_argument('--check-only', action='store_true', help='Prepare dependencies without opening the GUI.')
    args = parser.parse_args()
    try:
        if args.probe:
            check_python(project_config())
            return 0
        return prepare_and_launch(args.check_only)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f'Startup failed: {error}', file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
