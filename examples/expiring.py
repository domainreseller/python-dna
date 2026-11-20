"""Expiring: list every domain that expires within N days, across all pages.

    python examples/expiring.py --days 30
"""

import argparse

import domainnameapi as dna


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=30, help="show domains expiring within this many days")
    args = parser.parse_args()

    # Read-only: this program cannot change anything, even by mistake.
    client = dna.Client.from_env(read_only=True)

    count = 0
    for d in client.domains.all(statuses=[dna.DomainStatus.ACTIVE]):
        if d.remaining_days <= args.days:
            count += 1
            expires = d.expiration_date.date().isoformat() if d.expiration_date else "-"
            print("%-40s %s  %3d days  renewal: %s" % (d.domain_name, expires, d.remaining_days, d.renewal_mode))
    print("%d domain(s) expire within %d days" % (count, args.days))


if __name__ == "__main__":
    main()
