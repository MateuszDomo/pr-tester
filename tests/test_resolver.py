from pr_test_runner.resolver import filter_test_files, path_to_module


def test_filter_keeps_nested_test_files():
    files = ["accounts/tests/test_models.py", "accounts/tests/test_views.py"]
    assert filter_test_files(files) == files


def test_filter_excludes_non_test_python_files():
    files = ["accounts/models.py", "accounts/views.py", "accounts/tests/test_models.py"]
    assert filter_test_files(files) == ["accounts/tests/test_models.py"]


def test_filter_excludes_test_files_not_under_tests_dir():
    files = ["test_something.py", "accounts/test_models.py"]
    assert filter_test_files(files) == []


def test_filter_excludes_init_files_in_tests_dir():
    files = ["accounts/tests/__init__.py", "accounts/tests/test_models.py"]
    assert filter_test_files(files) == ["accounts/tests/test_models.py"]


def test_path_to_module_converts_slashes_and_strips_extension():
    assert path_to_module("accounts/tests/test_models.py") == "accounts.tests.test_models"


def test_path_to_module_handles_deep_nesting():
    assert path_to_module("apps/billing/tests/test_invoices.py") == "apps.billing.tests.test_invoices"
