import fnmatch


def filter_test_files(files: list[str]) -> list[str]:
    return [
        f for f in files
        if (fnmatch.fnmatch(f, "*/tests/test_*.py") or fnmatch.fnmatch(f, "*/tests/*.py"))
        and not f.endswith("__init__.py")
    ]


def path_to_module(file_path: str) -> str:
    return file_path.replace("/", ".").removesuffix(".py")
