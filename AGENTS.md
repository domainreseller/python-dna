# AGENTS.md

Guidance for people and AI coding agents working on this repository.

## What this is

`python-dna` is the Python SDK for the Domain Name API reseller REST API (PyPI package and import name
`domainnameapi`). It mirrors the [`dna` CLI](https://github.com/domainreseller/cli) and the go-dna and dotnet-dna
v2 SDKs: the same operations, the same groups, the same environment variables and the same safety classes. It has
nothing to do with php-dna or the SOAP API.

## Commands

```bash
python -m unittest discover -s tests -v   # all tests; none touches the network (pytest works too)
python -m build                            # sdist and wheel
```

## Layout

| file | content |
|---|---|
| `src/domainnameapi/client.py` | `Client`, `Environment`, `from_env`, sending, retries, pacing, tracing, correlation IDs |
| `src/domainnameapi/request.py` | `BaseRequest`, `Safety`, `Endpoint`, `Validator`, `Query`/`Body` builders |
| `src/domainnameapi/model.py` | `Model`, `Page`, the field helpers (`text`, `integer`, `timestamp`, ...) and time parsing |
| `src/domainnameapi/errors.py` | the exception hierarchy, `ErrorKind`, `ErrorCode` and the normalisation of API error responses |
| `src/domainnameapi/enums.py` | every enum, with the API's names and numbers |
| `src/domainnameapi/transport.py` | the transport protocol and the standard-library `UrllibTransport` |
| `src/domainnameapi/testing.py` | `FakeTransport` and reply helpers, public for users' tests |
| `account.py`, `contacts.py`, `domains.py`, `dns.py`, `dnssec.py`, `ssl.py`, `hosting.py`, `orders.py`, `products.py` | one module per CLI group: models, request classes, the service class |
| `tests/testdata/openapi.json` | the API's OpenAPI document, the same one the `dna` CLI embeds; the source of truth |

## Adding or changing an operation

1. Update `tests/testdata/openapi.json` from the CLI repository (see README, "Development") and run the tests.
   `test_every_operation_has_one_request_class` fails for any operation without a request class.
2. Add a request class named after the CLI command (`dna domain renew-check` → `DomainRenewCheckRequest`). It is
   a `@dataclass` deriving from `BaseRequest`; set `method`, `path`, `safety` (and `idempotent`, `response`) as
   class attributes, and override `query`, `body` and `validate` as needed. Fields are Pythonic snake_case; the
   wire format lives in `query` and `body`.
3. Add the models (`@dataclass` subclasses of `Model` with field helpers) and the service method. Required inputs
   are positional, optional ones keyword arguments. Turn `"success": false` answers into an `OperationError`.
4. Export the new names in `__init__.py` (`__all__` is static), add the case to `spec_cases()` in
   `tests/test_spec.py` (every field set), to `EveryServiceMethodTest`, and a behaviour test in
   `tests/test_services.py`.
5. New integer enums go in `enums.py` and in `test_spec_enums`.

## Rules

- **Safety class** is a product decision and matches the CLI: `BILLABLE` charges the balance, `DESTRUCTIVE`
  deletes or is hard to undo, `WRITE` is free and reversible, `READ` has no side effects even when the method is
  POST or PUT. Set `idempotent = True` only when sending the request twice is harmless.
- **Never retry a billable or non-idempotent request after a network error or a 5xx answer.** Only 429 is safe to
  retry for them. Do not weaken the retry rules in `client.py`.
- **No telemetry.** Nothing may leave the user's process except the API requests they make.
- **Standard library only**, Python 3.9 or newer: no `match`, no `X | Y` evaluated at runtime, no
  `dataclass(kw_only=...)`. Every module starts with `from __future__ import annotations`.
- **Models are forgiving:** response fields always have a default and decoding never fails on unexpected values;
  requests validate before sending.
- **Tests never call the real API.** Use `tests/helpers.py` (`fake(...)`) and `domainnameapi.testing`.
- **Public API:** every public class and method has a docstring. Error codes, `ErrorKind` values and safety
  classes are a contract.
- English for code, comments and docs. Error messages say what happened and what to do.
- `README.md` is the source; keep the eight `README-XX.md` translations in sync when it changes.
- Commits: imperative subject line. Do not add `Co-Authored-By` trailers for AI tools.
