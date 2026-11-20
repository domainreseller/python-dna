"""Custom request: send a request class of your own through the client.

Every operation of the package is a request class derived from
dna.BaseRequest. Yours can do the same: set method, path and safety, override
query, body or validate when needed, and send it with client.send(). You get
the client's credentials, retries, pacing, error handling and tracing.

    python examples/custom_request.py example.com
"""

import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import domainnameapi as dna
from domainnameapi.model import Model, integer, text, timestamp


@dataclass
class Expiry(Model):
    """The part of the domain record this program needs."""

    domain_name: str = text("domainName")
    expiration_date: Optional[datetime] = timestamp("expirationDate")
    remaining_days: int = integer("remainingDay")


@dataclass
class ExpiryRequest(dna.BaseRequest):
    """Read only the expiry fields of a domain."""

    method = "GET"
    path = "/api/v1/domains/info"
    safety = dna.Safety.READ
    response = Expiry

    domain_name: str = ""

    def query(self):
        return {"DomainName": self.domain_name}

    def validate(self, v: dna.Validator) -> None:
        v.required("domain_name", self.domain_name)


def show(event: dna.TraceEvent) -> None:
    if event.kind == "response":
        print("%s %s -> %d in %.3fs" % (event.method, event.url, event.status_code, event.duration), file=sys.stderr)


def main() -> None:
    domain = sys.argv[1] if len(sys.argv) > 1 else "example.com"
    client = dna.Client.from_env(trace=show)

    resp = client.send_with_response(ExpiryRequest(domain))
    expiry: Expiry = resp.value
    print("%s expires %s (%d days); correlation ID %s" % (expiry.domain_name, expiry.expiration_date,
                                                         expiry.remaining_days, resp.correlation_id))


if __name__ == "__main__":
    main()
