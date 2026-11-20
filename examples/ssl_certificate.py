"""SSL: generate a CSR, buy a certificate, configure it and wait until it is issued.

Buying charges the balance, so the program stops after listing the packages
unless you pass --package and --yes.

    python examples/ssl_certificate.py example.com
    python examples/ssl_certificate.py example.com --package PositiveSSL --approver admin@example.com --yes
"""

import argparse
import os
import time

import domainnameapi as dna


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("domain")
    parser.add_argument("--package", default="", help="SSL package code (see the list)")
    parser.add_argument("--approver", default="", help="approver e-mail address")
    parser.add_argument("--yes", action="store_true", help="really buy (charges the balance)")
    args = parser.parse_args()

    client = dna.Client.from_env()
    domain = args.domain

    if not args.package or not args.yes:
        for p in client.products.ssls():
            price = str(p.prices[0].create[0]) if p.prices and p.prices[0].create else ""
            print("%-24s %-12s wildcard=%-5s %s" % (p.product_code, p.validation_type, p.is_wildcard, price))
        print("pass --package CODE --approver MAIL --yes to buy one")
        return

    csr = client.ssl.generate_csr(domain, country="TR", state="Istanbul", locality="Istanbul",
                                  organization="Example Ltd", organization_unit="IT")
    with open(domain + ".key", "w") as fh:
        fh.write(csr.private_key)
    os.chmod(domain + ".key", 0o600)

    client.ssl.initialize(domain, args.package)  # charges the balance
    client.ssl.configure(
        domain, csr=csr.csr, private_key=csr.private_key, approver_mail=args.approver,
        authentication_type=dna.AuthenticationType.EMAIL, web_server_type=dna.WebServerType.APACHE,
        contact=dna.SSLContact(
            first_name="Ada", last_name="Lovelace", company_name="Example Ltd", email=args.approver,
            address="1 Example Street", city="Istanbul", postal_code="34000", country="TR",
            phone_country_code="90", phone="5551234567",
        ),
    )

    while True:
        st = client.ssl.status(domain)
        print("status:", st.status, st.status_message)
        if st.is_issued:
            break
        time.sleep(60)

    cert = client.ssl.content(domain)
    with open(domain + ".crt", "w") as fh:
        fh.write(cert.chain)
    print("wrote %s.crt and %s.key" % (domain, domain))


if __name__ == "__main__":
    main()
