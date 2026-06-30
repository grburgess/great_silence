---
name: run-tests
description: Run the pytest suite in the galaticbot micromamba environment with the required addopts override. Use when the user wants to run tests, a specific test file, or a specific test.
disable-model-invocation: true
---

# Run Tests

Run pytest inside the `galaticbot` micromamba environment. The `--override-ini="addopts="`
flag is required to disable the default coverage/options that otherwise interfere with
targeted runs.

## Usage

`$ARGUMENTS` may be empty (run everything), a test file, or a `file::Class::test` selector.

```bash
# All tests
micromamba run -n galaticbot python -m pytest tests/ -x -q --override-ini="addopts="

# A specific file or selector (when $ARGUMENTS is provided)
micromamba run -n galaticbot python -m pytest tests/$ARGUMENTS -x -q --override-ini="addopts="
```

If `$ARGUMENTS` already starts with `tests/`, use it verbatim instead of prefixing.

Report failures with the captured output. Do not modify tests to make them pass — fix the
implementation (see the python-test-guardian agent).
