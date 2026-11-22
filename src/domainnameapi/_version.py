"""Library version (single source of truth, also read by hatchling)."""

__version__ = "2.1.0"

#: Sent with every request (see ``Client(user_agent=...)``). The API sits behind
#: Cloudflare, which rejects requests without a descriptive agent.
USER_AGENT = "DomainNameAPI-Python/" + __version__ + " (+https://github.com/domainreseller/python-dna)"
