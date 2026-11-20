"""Register: create a contact handle and register a domain with it.

Registration charges the balance, so the program only previews the request
unless you pass --yes. Use the test environment (DNA_ENV=ote).

    python examples/register.py my-test-domain-123.com
    python examples/register.py my-test-domain-123.com --yes
"""

import argparse
import sys

import domainnameapi as dna


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("domain")
    parser.add_argument("--years", type=int, default=1)
    parser.add_argument("--yes", action="store_true", help="really register (charges the balance)")
    args = parser.parse_args()

    client = dna.Client.from_env()

    result = client.domains.search(args.domain)
    if not result.available:
        sys.exit("%s is not available: %s" % (args.domain, result.reason))
    print("%s costs %.2f %s" % (args.domain, result.price, result.currency))

    owner = dna.Contact(
        first_name="Ada", last_name="Lovelace", company_name="Example Ltd", email="ada@example.com",
        address="1 Example Street", city="Istanbul", state="Istanbul", postal_code="34000", country="TR",
        phone_country_code="+90", phone="555 123 45 67",  # tidied to digits for you
    )
    name_servers = ["ns1.domainnameapi.com", "ns2.domainnameapi.com"]

    if not args.yes:
        # Preview the exact request without sending it.
        preview = client.prepare(dna.DomainRegisterRequest(args.domain, "DNA-HANDLE", name_servers, args.years))
        print("would send %s %s\n%s" % (preview.method, preview.url, preview.body.decode()))
        print("run again with --yes to register")
        return

    handle = client.contacts.create(owner)
    try:
        res = client.domains.register(args.domain, handles=handle, name_servers=name_servers, years=args.years)
    except dna.InsufficientBalanceError:
        sys.exit("the balance is too low")
    except dna.OperationError as refused:
        sys.exit("the registry refused: %s" % refused.message)
    except dna.DomainNameAPIError as err:
        if err.outcome_unknown:
            sys.exit("the registration may have gone through; check client.domains.info() before retrying: %s"
                     % err)
        raise
    print("registered %s: status %s, expires %s" % (args.domain, res.status, res.expiration_date))


if __name__ == "__main__":
    main()
