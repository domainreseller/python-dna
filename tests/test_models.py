"""Models, enums and the forgiving decoding of API responses."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from helpers import TestCase, dna, sample_contact

from domainnameapi.model import (
    Model,
    Page,
    attributes,
    integer,
    model_list,
    paginate,
    parse_time,
    text,
)
from domainnameapi.request import Validator


class TimeTest(TestCase):
    def test_parse_time(self):
        utc = timezone.utc
        cases = {
            "2024-03-15T10:20:30": datetime(2024, 3, 15, 10, 20, 30, tzinfo=utc),
            "2024-03-15T10:20:30Z": datetime(2024, 3, 15, 10, 20, 30, tzinfo=utc),
            "2024-03-15T10:20:30.1234567Z": datetime(2024, 3, 15, 10, 20, 30, 123456, tzinfo=utc),
            "2024-03-15T10:20:30+03:00": datetime(2024, 3, 15, 7, 20, 30, tzinfo=utc),
            "2024-03-15 10:20:30-0130": datetime(2024, 3, 15, 11, 50, 30, tzinfo=utc),
            "2024-03-15T10:20": datetime(2024, 3, 15, 10, 20, tzinfo=utc),
            "2024-03-15": datetime(2024, 3, 15, tzinfo=utc),
            " 2024-03-15 ": datetime(2024, 3, 15, tzinfo=utc),
        }
        for value, want in cases.items():
            self.assertEqual(parse_time(value), want, value)
        for value in ("", "0001-01-01T00:00:00", "not a date", "2024-13-45", None, 123):
            self.assertIsNone(parse_time(value), value)
        naive = datetime(2024, 1, 2, 3, 4, 5)
        self.assertEqual(parse_time(naive), naive.replace(tzinfo=utc))


class DecodingTest(TestCase):
    def test_forgiving_decoding(self):
        @dataclass
        class Sample(Model):
            name: str = text("name")
            count: int = integer("count")
            attrs: dict = attributes("attrs")
            hosts: list = model_list("hosts", dna.Host)

        s = Sample.from_api({"NAME": 42, "count": "7", "attrs": [], "hosts": None, "extra": True})
        self.assertEqual(s.name, "42")
        self.assertEqual(s.count, 7)
        self.assertEqual(s.attrs, {})
        self.assertEqual(s.hosts, [])
        self.assertEqual(s.raw["extra"], True)
        self.assertEqual(Sample().raw, {})
        self.assertEqual(Sample.from_api(None), Sample())
        self.assertEqual(Sample.from_api({"attrs": {"a": 1, "b": None, "c": True, "d": [1]}}).attrs,
                         {"a": "1", "b": "", "c": "true", "d": "[1]"})
        self.assertEqual(Sample.from_api({"count": "x"}).count, 0)
        self.assertEqual(list(Sample.api_fields()), ["name", "count", "attrs", "hosts"])

    def test_decode_domain_info(self):
        d = dna.DomainInfo.from_api({
            "domainName": "example.com", "status": "PendingDelete", "statusCode": "ok",
            "startDate": "2020-01-01T00:00:00", "expirationDate": "0001-01-01T00:00:00", "remainingDay": 12,
            "authCode": "Xy7!", "lockStatus": True, "privacyProtectionStatus": None,
            "nameservers": ["ns1.example.net", "ns2.example.net"],
            "hosts": [{"name": "ns1.example.com", "ipAddresses": [{"ipAddress": "192.0.2.1", "ipVersion": "V4"}]}],
            "contacts": [
                {"contactType": "REGISTRANT", "firstName": "Ada", "eMail": "ada@example.com", "handle": "DNA-1"},
                {"contactType": "administrative", "firstName": "Bob"},
                {"contactType": "Something", "firstName": "Eve"},
            ],
            "additionalAttributes": [],
        })
        self.assertIs(d.status, dna.DomainStatus.PENDING_DELETE)
        self.assertEqual(d.start_date.year, 2020)
        self.assertIsNone(d.expiration_date)
        self.assertTrue(d.locked)
        self.assertFalse(d.privacy_protection)
        self.assertEqual(d.hosts[0].ip_addresses[0].version, dna.IPVersion.V4)
        self.assertEqual(d.contact(dna.ContactType.REGISTRANT).email, "ada@example.com")
        self.assertEqual(d.contact("admin").first_name, "Bob")
        self.assertIsNone(d.contact("billing"))
        self.assertEqual(d.contacts[2].type, "Something")  # unknown roles are kept as sent
        self.assertEqual(d.additional_attributes, {})

    def test_page_and_paginate(self):
        page = Page([1, 2, 3], 10)
        self.assertEqual(list(page), [1, 2, 3])
        self.assertEqual(len(page), 3)
        self.assertEqual(page[1], 2)

        calls = []

        def fetch(skip, limit):
            calls.append((skip, limit))
            data = list(range(5))
            return Page(data[skip:skip + limit], 5)

        self.assertEqual(list(paginate(fetch, 0, 2)), [0, 1, 2, 3, 4])
        self.assertEqual(calls, [(0, 2), (2, 2), (4, 2)])

        calls.clear()

        def no_total(skip, limit):
            calls.append(skip)
            return Page(list(range(skip, min(skip + limit, 3))), 0)

        self.assertEqual(list(paginate(no_total, 0, 2)), [0, 1, 2])
        self.assertEqual(calls, [0, 2])
        self.assertEqual(list(paginate(lambda s, n: Page([], 99), 0, 2)), [])


class EnumTest(TestCase):
    INT_ENUMS = (
        dna.DomainStatus, dna.DNSSECMode, dna.DocumentType, dna.DocumentStatus, dna.DocumentOperationType,
        dna.DNSSECStatus, dna.DNSSECOperationType, dna.DSRecordStatus, dna.DNSSECAlgorithm, dna.DSDigestType,
        dna.TransactionType, dna.TransactionStatus, dna.ChargeType, dna.ProductType, dna.OrderType, dna.OrderStatus,
        dna.OrderProductStatus,
    )

    def test_every_int_enum(self):
        for cls in self.INT_ENUMS:
            for member in cls:
                with self.subTest("%s.%s" % (cls.__name__, member.name)):
                    self.assertTrue(member.label)
                    self.assertEqual(str(member), member.label)
                    self.assertEqual("%s" % member, member.label)
                    self.assertEqual(f"{member}", member.label)
                    self.assertIs(cls.parse(member.label.lower()), member)
                    self.assertIs(cls.parse(member.name), member)
                    self.assertIs(cls.parse(str(int(member))), member)
                    self.assertIs(cls.parse(int(member)), member)
                    self.assertIs(cls.from_api(member.label), member)
                    self.assertIs(cls.from_api(int(member)), member)
                    self.assertTrue(member.is_known)

    def test_lenient_decoding(self):
        unknown = dna.DomainStatus.from_api(42)
        self.assertEqual(unknown, 42)
        self.assertFalse(unknown.is_known)
        self.assertEqual(str(unknown), "DomainStatus(42)")
        named = dna.DomainStatus.from_api("SomethingNew")
        self.assertEqual(named, -1)
        self.assertEqual(str(named), "SomethingNew")
        self.assertIsNone(dna.DomainStatus.from_api(None))
        self.assertIsNone(dna.DomainStatus.from_api(""))
        self.assertIs(dna.DomainStatus.from_api(7.0), dna.DomainStatus.PENDING_DELETE)
        self.assertIs(dna.DomainStatus.parse("pending_delete"), dna.DomainStatus.PENDING_DELETE)
        with self.assertRaises(ValueError) as ctx:
            dna.DomainStatus.parse("nope")
        self.assertIn("PendingDelete", str(ctx.exception))
        with self.assertRaises(ValueError):
            dna.DomainStatus(42)

    def test_int_enums_compare_and_serialise_as_numbers(self):
        import json

        self.assertEqual(dna.DomainStatus.PENDING_DELETE, 7)
        self.assertEqual(json.dumps({"s": dna.DomainStatus.PENDING_DELETE}), '{"s": 7}')

    def test_contact_type(self):
        for value, want in (("registrant", "Registrant"), ("OWNER", "Registrant"), ("Administrative", "Admin"),
                            ("technical", "Tech"), (" billing ", "Billing"), ("ADMIN", "Admin")):
            self.assertEqual(dna.ContactType.parse(value).value, want, value)
        with self.assertRaises(ValueError):
            dna.ContactType.parse("nobody")
        self.assertEqual(str(dna.ContactType.TECH), "Tech")

    def test_record_type_case(self):
        self.assertIs(dna.RecordType.parse("txt"), dna.RecordType.TXT)
        self.assertEqual(dna.RecordType.parse("dnskey").value, "DNSKey")
        self.assertEqual(dna.RecordType.parse("nsec3param").value, "NSEC3Param")
        with self.assertRaises(ValueError):
            dna.RecordType.parse("SPF")

    def test_string_enums(self):
        self.assertIs(dna.ForwardType.parse("frame"), dna.ForwardType.FRAME)
        self.assertIs(dna.AuthenticationType.parse("CNAME"), dna.AuthenticationType.CNAME)
        self.assertIs(dna.WebServerType.parse("iis"), dna.WebServerType.IIS)
        self.assertEqual("%s" % dna.IPVersion.V6, "v6")


class ContactTest(TestCase):
    def test_normalisation(self):
        c = dna.Contact(first_name=" Ada ", email=" ada@example.com ", country=" tr ",
                        phone_country_code="+90", phone="+90 (555) 123-45-67", fax="0212 123 45 67", handle=" DNA-1 ")
        n = c.normalized()
        self.assertEqual((n.first_name, n.email, n.country), ("Ada", "ada@example.com", "TR"))
        self.assertEqual((n.phone_country_code, n.phone, n.fax), ("90", "905551234567", "02121234567"))
        self.assertEqual(n.handle, "DNA-1")
        self.assertEqual(c.first_name, " Ada ", "normalized() changed the original")

    def test_to_api(self):
        api = sample_contact(company_name="", fax="", fax_country_code="", disclose_flag=None).to_api(
            dna.ContactType.ADMIN)
        self.assertEqual(api, {
            "firstName": "Ada", "lastName": "Lovelace", "eMail": "ada@example.com", "address": "1 Example Street",
            "city": "Istanbul", "state": "Istanbul", "postalCode": "34000", "country": "TR",
            "phoneCountryCode": "90", "phone": "5551234567", "contactType": "Admin",
        })
        self.assertEqual(sample_contact().to_api()["discloseFlag"], False)

    def test_validation(self):
        v = Validator()
        dna.Contact(email="nope", country="Turkey", phone_country_code="9000", phone="1" * 17).validate(v, "c.")
        fields = {e.field for e in v.errors}
        for f in ("c.first_name", "c.last_name", "c.email", "c.address", "c.city", "c.state", "c.postal_code",
                  "c.country", "c.phone_country_code", "c.phone"):
            self.assertIn(f, fields)
        v = Validator()
        sample_contact().validate(v)
        self.assertEqual(v.errors, [])

    def test_handles_and_contacts(self):
        self.assertEqual(dna.ContactHandles.same("DNA-1").to_api(), [
            {"contactType": "Registrant", "handle": "DNA-1"}, {"contactType": "Admin", "handle": "DNA-1"},
            {"contactType": "Tech", "handle": "DNA-1"}, {"contactType": "Billing", "handle": "DNA-1"}])
        self.assertEqual(dna.ContactHandles(admin=" DNA-2 ", tech="").items(), [(dna.ContactType.ADMIN, "DNA-2")])
        self.assertEqual(dna.ContactHandles.coerce("X"), dna.ContactHandles.same("X"))
        c = sample_contact()
        self.assertEqual([x["contactType"] for x in dna.DomainContacts.same(c).to_api()],
                         ["Registrant", "Admin", "Tech", "Billing"])
        self.assertEqual(dna.DomainContacts.coerce(c), dna.DomainContacts.same(c))
        self.assertEqual(dna.DomainContacts(billing=c).to_api()[0]["contactType"], "Billing")


class DNSModelTest(TestCase):
    def test_fqdn(self):
        for name, want in (("www", "www.example.com."), ("", "example.com."), ("@", "example.com."),
                           ("example.com", "example.com."), ("WWW.Example.com.", "www.example.com."),
                           ("a.b", "a.b.example.com.")):
            self.assertEqual(dna.fqdn("Example.com.", name), want, name)

    def test_record_set(self):
        s = dna.RecordSet.from_api({"name": "www.example.com.", "type": "TXT", "ttl": 300,
                                    "records": [{"content": "\"a\""}, {"content": "\"b\"", "disabled": True}]})
        self.assertEqual(s.values, ['"a"', '"b"'])
        self.assertTrue(s.records[1].disabled)
        self.assertTrue(s.matches("example.com", "www", "txt"))
        self.assertTrue(s.matches("example.com", "www.example.com.", dna.RecordType.TXT))
        self.assertFalse(s.matches("example.com", "@", "TXT"))
        self.assertFalse(s.matches("example.com", "www", "A"))

    def test_parse_ds(self):
        ds = dna.DS.parse("2371 13 2 1f987cc6 583e92df")
        self.assertEqual((ds.key_tag, ds.algorithm, ds.digest_type, ds.digest),
                         (2371, dna.DNSSECAlgorithm.ECDSAP256SHA256, dna.DSDigestType.SHA256, "1F987CC6583E92DF"))
        self.assertEqual(str(ds), "2371 13 2 1F987CC6583E92DF")
        line = dna.DS.parse("example.com. 3600 IN DS 2371 EcdsaP256Sha256 sha256 ABCD")
        self.assertEqual(line.to_api(), {"keyTag": 2371, "algorithm": 13, "digestType": 2, "digest": "ABCD"})
        for bad in ("", "2371 13 2", "x 13 2 AB", "2371 99 2 AB", "2371 13 9 AB"):
            with self.assertRaises(ValueError, msg=bad):
                dna.DS.parse(bad)


class HelperTest(TestCase):
    def test_account_balance(self):
        a = dna.Account.from_api({"usdBalance": 12.5, "tryBalance": "400.25"})
        self.assertEqual(a.balance("usd"), 12.5)
        self.assertEqual(a.balance("TL"), 400.25)
        self.assertIsNone(a.balance("EUR"))

    def test_transaction_change(self):
        t = dna.Transaction.from_api({"amount": 0, "balance": 88.0, "oldBalance": 99.99, "type": 2})
        self.assertEqual(t.change, -11.99)
        self.assertIs(t.type, dna.TransactionType.RENEW)

    def test_availability(self):
        self.assertTrue(dna.Availability.from_api({"status": "available"}).available)
        self.assertFalse(dna.Availability.from_api({"status": "NOTAVAILABLE"}).available)

    def test_certificate_chain(self):
        c = dna.CertificateContent(certificate="CERT\n", intermediate1=" INT1 ", intermediate2="", root="ROOT")
        self.assertEqual(c.chain, "CERT\nINT1\n")

    def test_tld_prices(self):
        tld = dna.TLD.from_api({"name": "com", "prices": [{"priceGroup": "default",
                                                           "register": [{"period": 1, "price": 9.5, "currency": "USD"}],
                                                           "renew": [{"period": 2, "price": 20, "currency": "USD"}],
                                                           "restore": {"period": 1, "price": 80, "currency": "USD"}}],
                                "attributes": [{"key": "lang", "isRequired": True}, {"key": "x"}]})
        self.assertEqual(str(tld.register_price(1)), "9.50 USD")
        self.assertEqual(tld.renew_price(2).price, 20.0)
        self.assertIsNone(tld.transfer_price(1))
        self.assertEqual(tld.prices[0].restore.price, 80.0)
        self.assertIsNone(tld.prices[0].refund)
        self.assertEqual([a.key for a in tld.required_attributes], ["lang"])

    def test_hosting_status(self):
        self.assertTrue(dna.HostingStatus.from_api({"status": "active"}).active)
        self.assertTrue(dna.HostingStatus.from_api({"status": "Failed"}).failed)
        plan = dna.ServicePlan.from_api({"name": "Starter", "diskQuotaMb": 1024, "maxDomains": None})
        self.assertEqual(plan.disk_quota_mb, 1024)
        self.assertIsNone(plan.max_domains, "None means unlimited")

    def test_document_from_file(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "id.pdf")
            with open(path, "wb") as fh:
                fh.write(b"%PDF-1.4")
            d = dna.DocumentUpload.from_file(dna.DocumentType.IDENTITY_CARD, path)
        self.assertEqual((d.file_name, d.content, d.type), ("id.pdf", b"%PDF-1.4", dna.DocumentType.IDENTITY_CARD))
        with self.assertRaises(OSError):
            dna.DocumentUpload.from_file(dna.DocumentType.IDENTITY_CARD, path + ".missing")

    def test_validator(self):
        v = Validator()
        self.assertTrue(v.between("years", 0, 1, 10))
        self.assertFalse(v.between("years", 0, 1, 10, optional=False))
        self.assertFalse(v.between("years", True, 1, 10, optional=False))
        self.assertFalse(v.required_list("names", [" ", None]))
        self.assertTrue(v.required_list("names", "one"))
        self.assertFalse(v.max_length("s", "abcd", 3))
        self.assertTrue(v.enum("e", None, dna.DomainStatus))
        self.assertFalse(v.enum("e", 42, dna.DomainStatus))
        self.assertTrue(bool(v))
        with self.assertRaises(dna.InputError):
            v.raise_if_invalid("R")

    def test_utc_dates_in_queries(self):
        req = dna.AccountTransactionsRequest(since=datetime(2026, 1, 1, 3, 0, tzinfo=timezone(timedelta(hours=3))),
                                             until=datetime(2026, 2, 1))
        q = dict(req.query())
        self.assertEqual(q["StartDate"], "2026-01-01T00:00:00Z")
        self.assertEqual(q["EndDate"], "2026-02-01T00:00:00Z")
