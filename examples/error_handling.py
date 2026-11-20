"""Error handling: what each exception means and what to do about it.

    python examples/error_handling.py example.com
"""

import sys

import domainnameapi as dna


def renew(client: dna.Client, domain: str) -> None:
    try:
        res = client.domains.renew(domain, 1)
    except dna.InputError as err:
        # Validation failed before anything was sent.
        print("fix the input:", ", ".join(str(f) for f in err.fields))
    except dna.InsufficientBalanceError as err:
        print("top up the balance first:", err.message, err.data)
    except dna.NotFoundError as err:
        print("not in this account or environment:", err.hint)
    except dna.OperationError as err:
        # The API answered but refused ("success": false).
        print("refused:", err.message)
    except dna.RateLimitError as err:
        print("still rate limited after the automatic retries; retry after", err.retry_after, "s")
    except dna.DomainNameAPIError as err:
        if err.outcome_unknown:
            # A billable request failed in a way that leaves its outcome open.
            # Never repeat it blindly: check the domain first.
            info = client.domains.info(domain)
            print("check before retrying; the domain now expires", info.expiration_date)
        else:
            print("failed (%s): %s" % (err.kind, err))
            if isinstance(err, dna.APIError):
                print("code %s, correlation ID %s, hint: %s" % (err.code, err.correlation_id, err.hint))
    else:
        print("renewed; new expiration date", res.expiration_date)


if __name__ == "__main__":
    renew(dna.Client.from_env(), sys.argv[1] if len(sys.argv) > 1 else "example.com")
