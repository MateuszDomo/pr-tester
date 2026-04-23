import fnmatch


def filter_test_files(files: list[str]) -> list[str]:
    patterns = [
        "*/tests/test_*.py",
        "*/tests/*.py",
        "tests/test_*.py",
        "tests/*.py",
    ]
    return [
        f for f in files
        if any(fnmatch.fnmatch(f, p) for p in patterns)
        and not f.endswith("__init__.py")
    ]


def path_to_module(file_path: str) -> str:
    return file_path.replace("/", ".").removesuffix(".py")
