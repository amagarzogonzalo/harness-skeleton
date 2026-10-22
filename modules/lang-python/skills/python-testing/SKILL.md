---
name: python-testing
description: pytest patterns for Python changes. Trigger when adding or fixing Python tests, fixtures, async tests, or coverage gaps.
---

# Python testing

## Layout

```
tests/
  conftest.py          # shared fixtures only
  test_<module>.py     # mirrors src/<package>/<module>.py
```

Test behavior through the public function or the HTTP boundary. Do not import
private helpers just to test them.

## Commands

```bash
uv run pytest tests/test_x.py::test_y -q       # one test
uv run pytest tests/test_x.py -q               # one file
uv run pytest tests/ -q                        # the suite
uv run pytest tests/ -q -k "not slow"          # skip the slow marker
```

## Fixtures

- Use `tmp_path` for files, `monkeypatch` for env vars and attributes, and a
  factory fixture for repeated objects.
- A fixture with a `yield` must put cleanup after the `yield`, not only in the
  success path.
- No fixture that performs network I/O in a unit test. Fake the client at the
  boundary.
- Prefer explicit fixtures over `autouse=True`; hidden setup makes failures hard
  to read.

## Parametrization

```python
@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, "zero"), (1, "one"), (-1, "negative")],
)
def test_label(value, expected):
    assert label(value) == expected
```

Use `pytest.param(..., id="...")` when the default id is unreadable. Do not
parametrize unrelated behaviors into one test.

## Async

```python
async def test_fetch(client):
    result = await client.fetch("x")
    assert result.status == "ok"
```

Use the project's async plugin (`pytest-asyncio` or `anyio`), not a manual event
loop. Do not call `asyncio.run` inside a test. Ensure background tasks are
cancelled at the end of the test.

## Exceptions

```python
with pytest.raises(ValueError, match="must be positive"):
    parse("-1")
```

Assert the exception type and the message that identifies the failure. Do not
assert only `Exception`.

## Determinism

- No `time.sleep`; use a fake clock or poll with a deadline.
- No real network, no real database, no dependence on test order.
- Freeze time when the behavior depends on "now".
- A flaky test is a bug: fix it or delete it.

## Coverage and properties

- Coverage is a smoke detector, not a goal. Do not write assertion-free tests to
  raise a number.
- Hypothesis is optional and best for pure parsers, encoders, and numeric code.
  Put it behind a `hypothesis` marker if the suite is otherwise fast.

## Stop conditions

- The test passes before the change: the test is wrong.
- The test needs six mocks: it is at the wrong level. Move it to the boundary.
- The test is slower than one second: mark it `slow` and move it to the nightly
  job, or make the dependency fakeable.
