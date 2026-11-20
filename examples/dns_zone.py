"""DNS: add, replace, list and delete zone records.

The test environment answers every zone call with HTTP 500, so run this in
production against a domain you do not mind changing.

    python examples/dns_zone.py example.com
"""

import argparse

import domainnameapi as dna


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("domain", help="domain whose zone to change")
    args = parser.parse_args()

    client = dna.Client.from_env()
    domain = args.domain

    # Add a value to the "test" A record set (the set is created if needed).
    client.dns.add(domain, "test", dna.RecordType.A, "192.0.2.10", ttl=600)

    # Replace every value of the set.
    client.dns.update(domain, "test", dna.RecordType.A, ["192.0.2.20", "192.0.2.21"], ttl=300)

    for s in client.dns.list(domain):
        print("%-30s %-6s %6d  %s" % (s.name, s.type, s.ttl, ", ".join(s.values)))

    # Remove the values again, one by one.
    for value in ("192.0.2.20", "192.0.2.21"):
        client.dns.delete(domain, "test", dna.RecordType.A, value)

    # Records resolve publicly only on the platform nameservers. apply() switches
    # the domain to them (and away from any other DNS provider):
    #
    #     client.dns.apply(domain)


if __name__ == "__main__":
    main()
