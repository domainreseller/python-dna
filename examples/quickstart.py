"""Quickstart: check the credentials, show the balance and search a domain.

    export DNA_RESELLER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    export DNA_API_KEY=your-ote-api-key
    export DNA_ENV=ote
    python examples/quickstart.py example.com
"""

import sys

import domainnameapi as dna


def main() -> None:
    domain = sys.argv[1] if len(sys.argv) > 1 else "example.com"
    client = dna.Client.from_env()

    account = client.account.get()  # a wrong key or environment shows up here
    print("%s (%s): %.2f USD, %.2f TRY" % (account.reseller_name, client.environment, account.usd_balance,
                                           account.try_balance))

    result = client.domains.search(domain)
    if result.available:
        print("%s is available: %.2f %s for %d year(s)" % (result.domain_name, result.price, result.currency,
                                                           result.period))
    else:
        print("%s is not available (%s)" % (result.domain_name, result.reason))


if __name__ == "__main__":
    try:
        main()
    except dna.DomainNameAPIError as err:
        sys.exit("error: %s" % err)
