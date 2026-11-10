"""Install the project Skill and thin entry points; never creates jobs or credentials."""
import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def install(repo, home, force=False, dry_run=False):
    repo, home = repo.resolve(), home.expanduser().resolve()
    files = {home / 'skills/intel-shelf-maintain/SKILL.md':
             (repo / 'skills/intel-shelf-maintain/SKILL.md').read_text(encoding='utf-8')}
    for name in ('intel-shelf-watch.py', 'intel-shelf-weekly.py', 'intel-shelf-report.py'):
        source = repo / 'ops/hermes' / name
        if not source.is_file():
            raise ValueError('Missing project entry point: ' + name)
        files[home / 'scripts' / name] = ('#!/usr/bin/env python3\nimport runpy\n'
                                        + 'runpy.run_path(' + repr(str(source)) + ', run_name="__main__")\n')
    # Check all destinations before writing any file. Explicit force is needed for an update.
    for path, body in files.items():
        if path.is_symlink():
            raise ValueError('Refusing a symlink destination: ' + str(path))
        if path.exists() and path.read_text(encoding='utf-8') != body and not force:
            raise ValueError('Existing file differs; inspect it before using --force: ' + str(path))
    for path, body in files.items():
        print(('Would install ' if dry_run else 'Install ') + str(path))
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('w', encoding='utf-8', newline='\n') as stream:
                stream.write(body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--hermes-home', type=Path,
                        default=Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes'))))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--force', action='store_true', help='Replace inspected project entry points and Skill')
    args = parser.parse_args()
    install(args.repo, args.hermes_home, args.force, args.dry_run)


if __name__ == '__main__':
    main()
