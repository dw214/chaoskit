#!/usr/bin/env python3
"""
PyPI Publishing Script for Chaos SDK
Usage: python scripts/publish.py [test|prod] [--skip-checks] [--auto-tag]
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def print_step(step: int, total: int, message: str) -> None:
    """Print a formatted step message"""
    print(f"{Colors.GREEN}[{step}/{total}] {message}{Colors.RESET}")


def print_success(message: str) -> None:
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_warning(message: str) -> None:
    """Print a warning message"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_error(message: str) -> None:
    """Print an error message"""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message: str) -> None:
    """Print an info message"""
    print(f"{Colors.BLUE}{message}{Colors.RESET}")


def run_command(
    cmd: list[str],
    check: bool = True,
    capture_output: bool = False,
    cwd: Optional[Path] = None
) -> subprocess.CompletedProcess:
    """Run a shell command and handle errors"""
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True,
            cwd=cwd
        )
        return result
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {' '.join(cmd)}")
        if e.stderr:
            print(e.stderr)
        raise


def get_version() -> Tuple[str, str]:
    """Extract version from pyproject.toml and __init__.py"""
    project_root = Path(__file__).parent.parent
    
    # Get version from pyproject.toml
    toml_version = None
    try:
        # Try using tomllib (Python 3.11+)
        try:
            import tomllib
        except ImportError:
            # Fallback to tomli for older Python versions
            try:
                import tomli as tomllib
            except ImportError:
                tomllib = None
        
        if tomllib:
            toml_path = project_root / "pyproject.toml"
            with open(toml_path, 'rb') as f:
                data = tomllib.load(f)
                toml_version = data.get('project', {}).get('version')
        else:
            # Fallback to regex parsing
            toml_path = project_root / "pyproject.toml"
            with open(toml_path, 'r') as f:
                for line in f:
                    if line.strip().startswith('version'):
                        match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', line)
                        if match:
                            toml_version = match.group(1)
                            break
    except Exception as e:
        print_error(f"Failed to read version from pyproject.toml: {e}")
    
    # Get version from __init__.py
    init_version = None
    try:
        init_path = project_root / "chaos_sdk" / "__init__.py"
        with open(init_path, 'r') as f:
            content = f.read()
            match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                init_version = match.group(1)
    except Exception as e:
        print_error(f"Failed to read version from __init__.py: {e}")
    
    if not toml_version:
        print_error("Could not extract version from pyproject.toml")
        sys.exit(1)
    
    if toml_version != init_version:
        print_warning(f"Version mismatch: pyproject.toml={toml_version}, __init__.py={init_version}")
    
    return toml_version, init_version


def check_dependencies() -> None:
    """Check if required build tools are installed"""
    print_step(2, 9, "Checking dependencies...")
    
    required = ['build', 'twine']
    missing = []
    
    for package in required:
        result = run_command(
            [sys.executable, '-m', 'pip', 'show', package],
            check=False,
            capture_output=True
        )
        if result.returncode != 0:
            missing.append(package)
    
    if missing:
        print_info(f"Installing missing packages: {', '.join(missing)}")
        for package in missing:
            run_command([sys.executable, '-m', 'pip', 'install', '--upgrade', package])
    
    print_success("Dependencies ready")
    print()


def clean_build_artifacts(project_root: Path) -> None:
    """Remove old build artifacts"""
    print_step(3, 9, "Cleaning old builds...")
    
    patterns = ['dist', 'build', '*.egg-info', 'chaos_sdk.egg-info']
    
    for pattern in patterns:
        if '*' in pattern:
            for path in project_root.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path)
                    print_info(f"Removed {path.name}/")
                else:
                    path.unlink()
                    print_info(f"Removed {path.name}")
        else:
            path = project_root / pattern
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                    print_info(f"Removed {pattern}/")
                else:
                    path.unlink()
                    print_info(f"Removed {pattern}")
    
    print_success("Cleaned build artifacts")
    print()


def build_package(project_root: Path) -> None:
    """Build the package"""
    print_step(4, 9, "Building package...")
    
    run_command([sys.executable, '-m', 'build'], cwd=project_root)
    
    print_success("Package built successfully")
    print()


def check_package(project_root: Path) -> None:
    """Validate the package with twine"""
    print_step(5, 9, "Checking package...")
    
    dist_dir = project_root / 'dist'
    dist_files = list(dist_dir.glob('*'))
    
    if not dist_files:
        print_error("No distribution files found in dist/")
        sys.exit(1)
    
    run_command(['twine', 'check'] + [str(f) for f in dist_files])
    
    print_success("Package validation passed")
    print()
    
    print_info("Package contents:")
    for f in dist_files:
        size = f.stat().st_size
        size_str = f"{size / 1024:.1f}K" if size < 1024*1024 else f"{size / (1024*1024):.1f}M"
        print(f"  {f.name} ({size_str})")
    print()


def upload_to_testpypi(project_root: Path, version: str) -> None:
    """Upload package to TestPyPI"""
    print_step(6, 9, "Uploading to TestPyPI...")
    print_info("Repository: https://test.pypi.org")
    print()
    
    dist_dir = project_root / 'dist'
    dist_files = list(dist_dir.glob('*'))
    
    run_command(
        ['twine', 'upload', '--repository', 'testpypi'] + [str(f) for f in dist_files]
    )
    
    print()
    print_success("Successfully uploaded to TestPyPI!")
    print()
    print_info("To install from TestPyPI:")
    print(f"  pip install --index-url https://test.pypi.org/simple/ \\")
    print(f"              --extra-index-url https://pypi.org/simple/ \\")
    print(f"              chaoskit=={version}")
    print()
    print_info("View on TestPyPI:")
    print(f"  https://test.pypi.org/project/chaoskit/{version}/")
    print()


def upload_to_pypi(project_root: Path, version: str) -> None:
    """Upload package to production PyPI"""
    print_step(6, 9, "Uploading to PRODUCTION PyPI...")
    print_error("WARNING: This action cannot be undone!")
    print_error("Version numbers cannot be reused.")
    print_info(f"Version: {version}")
    print()
    
    confirm = input("Are you sure you want to continue? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print_warning("Upload cancelled.")
        sys.exit(0)
    
    dist_dir = project_root / 'dist'
    dist_files = list(dist_dir.glob('*'))
    
    run_command(['twine', 'upload'] + [str(f) for f in dist_files])
    
    print()
    print_success("Successfully uploaded to PyPI!")
    print()
    print_info("To install:")
    print(f"  pip install chaoskit=={version}")
    print()
    print_info("View on PyPI:")
    print(f"  https://pypi.org/project/chaoskit/{version}/")
    print()


def verify_package(version: str) -> None:
    """Display package verification info"""
    print_step(7, 9, "Verification")
    print(f"Package name: chaoskit")
    print(f"Version: {version}")
    print()


def handle_git_tag(version: str, auto_tag: bool, project_root: Path) -> None:
    """Create git tag if requested"""
    print_step(8, 9, "Git tagging")
    
    tag_name = f"v{version}"
    
    # Check if tag exists
    result = run_command(
        ['git', 'rev-parse', tag_name],
        check=False,
        capture_output=True,
        cwd=project_root
    )
    
    tag_exists = result.returncode == 0
    
    if tag_exists:
        print_warning(f"Tag {tag_name} already exists")
        if auto_tag:
            print_warning("Skipping tag creation (--auto-tag with existing tag)")
    else:
        if auto_tag:
            print_info(f"Creating tag {tag_name}...")
            run_command(
                ['git', 'tag', '-a', tag_name, '-m', f'Release version {version}'],
                cwd=project_root
            )
            print_success(f"Tag {tag_name} created")
            print_info(f"Push with: git push origin {tag_name}")
        else:
            print_info(f"To create tag: git tag -a {tag_name} -m \"Release version {version}\"")
            print_info("Or run with --auto-tag next time")
    
    print()


def print_next_steps(mode: str, version: str, auto_tag: bool) -> None:
    """Print next steps for the user"""
    print_step(9, 9, "Next steps:")
    
    print("1. Test installation in a clean environment:")
    if mode == 'test':
        print(f"   pip install --index-url https://test.pypi.org/simple/ \\")
        print(f"               --extra-index-url https://pypi.org/simple/ \\")
        print(f"               chaoskit=={version}")
    else:
        print(f"   pip install chaoskit=={version}")
    
    print("2. Verify imports: python -c 'import chaos_sdk; print(chaos_sdk.__version__)'")
    print("3. Update CHANGELOG.md if not already done")
    
    tag_name = f"v{version}"
    if not auto_tag:
        print(f"4. Create and push git tag: git tag -a {tag_name} -m \"Release {version}\" && git push origin {tag_name}")
    else:
        # Check if tag was created (not existing)
        result = run_command(
            ['git', 'rev-parse', tag_name],
            check=False,
            capture_output=True
        )
        if result.returncode == 0:
            print(f"4. Push git tag: git push origin {tag_name}")
    
    print()
    print_success("Done!")


def run_pre_publish_checks(project_root: Path) -> None:
    """Run pre-publish checks script if available"""
    print_step(1, 9, "Running pre-publish checks...")
    
    check_script = project_root / "scripts" / "pre-publish-check.sh"
    
    if not check_script.exists():
        print_warning("pre-publish-check.sh not found, skipping checks")
        print()
        return
    
    result = run_command(
        ['bash', str(check_script)],
        check=False,
        cwd=project_root
    )
    
    if result.returncode != 0:
        print_error("Pre-publish checks failed. Fix errors and try again.")
        print_warning("Or use --skip-checks to bypass (not recommended)")
        sys.exit(1)
    
    print_success("All checks passed")
    print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Publish Chaos SDK to PyPI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/publish.py test              # Upload to TestPyPI
  python scripts/publish.py prod              # Upload to PyPI
  python scripts/publish.py test --auto-tag   # Upload to TestPyPI and create git tag
  python scripts/publish.py prod --skip-checks --auto-tag  # Skip checks and auto-tag
        """
    )
    
    parser.add_argument(
        'mode',
        choices=['test', 'prod'],
        default='test',
        nargs='?',
        help='Publishing mode: test (TestPyPI) or prod (PyPI)'
    )
    parser.add_argument(
        '--skip-checks',
        action='store_true',
        help='Skip pre-publish validation checks (not recommended)'
    )
    parser.add_argument(
        '--auto-tag',
        action='store_true',
        help='Automatically create git tag for the version'
    )
    
    args = parser.parse_args()
    
    # Get project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Print header
    print()
    print(f"{Colors.YELLOW}===================================={Colors.RESET}")
    print(f"{Colors.YELLOW}   Chaos SDK Publishing Script{Colors.RESET}")
    print(f"{Colors.YELLOW}===================================={Colors.RESET}")
    print_info(f"Mode: {args.mode}")
    print()
    
    try:
        # Get and verify version
        toml_version, init_version = get_version()
        
        if toml_version != init_version:
            print_error(f"Version mismatch detected!")
            print_error(f"  pyproject.toml: {toml_version}")
            print_error(f"  __init__.py: {init_version}")
            print_error("Please fix version inconsistency before publishing.")
            sys.exit(1)
        
        version = toml_version
        print_info(f"Version: {version}")
        print()
        
        # Run pre-publish checks
        if not args.skip_checks:
            run_pre_publish_checks(project_root)
        else:
            print_warning("[1/9] Skipping pre-publish checks (--skip-checks)")
            print()
        
        # Check dependencies
        check_dependencies()
        
        # Clean old builds
        clean_build_artifacts(project_root)
        
        # Build package
        build_package(project_root)
        
        # Check package
        check_package(project_root)
        
        # Upload
        if args.mode == 'test':
            upload_to_testpypi(project_root, version)
        else:
            upload_to_pypi(project_root, version)
        
        # Verify
        verify_package(version)
        
        # Handle git tag
        handle_git_tag(version, args.auto_tag, project_root)
        
        # Print next steps
        print_next_steps(args.mode, version, args.auto_tag)
        
    except KeyboardInterrupt:
        print()
        print_warning("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
