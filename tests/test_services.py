"""Service methods: what they send and how they read the answers."""

import uuid
from datetime import datetime, timezone

from helpers import CERT_ID, Reply, TestCase, api_error, dna, fake, ok, sample_contact, sample_ssl_contact

#: The id of the certificate that renews CERT_ID.
RENEWAL_ID = "0b1e7a52-9c3d-4f6a-8e21-5d4c3b2a1f00"


class AccountTest(TestCase):
    def test_get(self):
        transport, client = fake(ok({"resellerId": "r-1", "resellerName": "Acme", "tryBalance": 100.5,
                                     "usdBalance": 12}))
        a = client.account.get()
        self.assertEqual((a.reseller_id, a.reseller_name, a.balance("TRY"), a.balance("usd")),
                         ("r-1", "Acme", 100.5, 12.0))
        self.assertEqual((transport.last.method, transport.last.path), ("GET", "/api/v1/deposit/accounts/me"))

    def test_profile(self):
        reseller_id = "7c9e6679-7425-40de-944b-e07fc1f90ae7"
        transport, client = fake(
            ok({"id": reseller_id, "resellerAutoId": 4711, "name": "Acme", "companyName": "Acme Ltd",
                "resellerGroupName": "Gold", "accountCurrency": 2, "status": 0, "isSubReseller": False,
                "isBalanceSuspended": True, "isMcpEnabled": True}),
            ok({"accountCurrency": "try", "status": "WaitingForCompletionWizard"}),
            ok({"accountCurrency": 9, "status": 7}),
        )
        p = client.account.profile()
        r = transport.last
        self.assertEqual((r.method, r.path, r.query, r.body), ("GET", "/api/v1/resellers/me", {}, b""))
        self.assertEqual((p.id, p.reseller_auto_id, p.name, p.company_name, p.reseller_group_name),
                         (reseller_id, 4711, "Acme", "Acme Ltd", "Gold"))
        self.assertIs(p.account_currency, dna.AccountCurrency.USD)
        self.assertEqual(str(p.account_currency), "USD")
        self.assertIs(p.status, dna.ResellerStatus.ACTIVE)
        self.assertEqual((p.is_sub_reseller, p.is_balance_suspended, p.is_mcp_enabled), (False, True, True))

        p = client.account.profile()
        self.assertIs(p.account_currency, dna.AccountCurrency.TRY)
        self.assertIs(p.status, dna.ResellerStatus.WAITING_FOR_COMPLETION_WIZARD)
        self.assertEqual((p.id, p.reseller_auto_id, p.is_mcp_enabled), ("", 0, False))

        p = client.account.profile()  # values this package does not know yet never fail
        self.assertEqual((int(p.account_currency), p.account_currency.is_known), (9, False))
        self.assertEqual((int(p.status), p.status.is_known), (7, False))

        self.assertIs(dna.AccountProfileRequest().endpoint().safety, dna.Safety.READ)
        _, client = fake(ok({"name": "Acme"}), read_only=True)
        self.assertEqual(client.account.profile().name, "Acme")

    def test_transactions(self):
        transport, client = fake(
            ok({"totalCount": 3, "items": [{"traceId": "t1", "type": 2, "status": 1, "chargeType": 1,
                                            "balance": 88, "oldBalance": 99.99, "creationTime": "2026-11-01T10:00:00"},
                                           {"traceId": "t2", "type": "Renew"}]}),
            ok({"totalCount": 3, "items": [{"traceId": "t3"}]}),
        )
        since = datetime(2026, 11, 1, tzinfo=timezone.utc)
        txs = list(client.account.all_transactions(transaction_types=["renew", dna.TransactionType.REGISTER],
                                                   charge_type=dna.ChargeType.SUBTRACT, since=since, page_size=2))
        self.assertEqual([t.trace_id for t in txs], ["t1", "t2", "t3"])
        self.assertIs(txs[0].type, dna.TransactionType.RENEW)
        self.assertIs(txs[1].type, dna.TransactionType.RENEW)
        self.assertEqual(txs[0].change, -11.99)
        first, second = transport.requests
        self.assertEqual(first.query["TransactionTypes"], ["2", "1"])
        self.assertEqual(first.param("ChargeType"), "1")
        self.assertEqual(first.param("StartDate"), "2026-11-01T00:00:00Z")
        self.assertEqual(first.param("MaxResultCount"), "2")
        self.assertIsNone(first.param("SkipCount"))
        self.assertEqual(second.param("SkipCount"), "2")

        with self.assertRaises(dna.InputError):
            client.account.transactions(since=since, until=datetime(2026, 1, 1, tzinfo=timezone.utc))
        with self.assertRaises(dna.InputError):
            client.account.transactions(transaction_types=["nope"])

    def test_charge_type_add_is_sent(self):
        transport, client = fake(ok({"items": []}))
        client.account.transactions(charge_type="add")
        self.assertEqual(transport.last.param("ChargeType"), "0")


class ContactsTest(TestCase):
    def test_create(self):
        transport, client = fake(ok({"handle": "DNA-77", "operationMessage": "ok", "isSuccess": True}),
                                 ok({"handle": None, "operationMessage": "E-mail is invalid", "isSuccess": False}))
        c = sample_contact(phone="+90 555 123 45 67", country="tr", disclose_flag=None)
        self.assertEqual(client.contacts.create(c), "DNA-77")
        body = transport.last.json()["contact"]
        self.assertEqual((body["phone"], body["country"]), ("905551234567", "TR"))
        self.assertNotIn("contactType", body)
        self.assertNotIn("discloseFlag", body)
        with self.assertRaises(dna.OperationError) as ctx:
            client.contacts.create(c)
        self.assertEqual(ctx.exception.message, "E-mail is invalid")
        with self.assertRaises(dna.InputError):
            client.contacts.create(dna.Contact(first_name="Ada"))
        self.assertEqual(len(transport.requests), 2)

    def test_get_update_and_verification(self):
        transport, client = fake(
            ok({"contact": {"handle": "DNA-1", "firstName": "Ada"},
                "verificationObjects": [{"fieldType": "Email", "isUserVerified": True}]}),
            ok({"handle": "DNA-1", "contactUpdateSuccess": True, "stats": {"totalDomainCount": 2, "successCount": 2},
                "affectedDomains": [{"domainName": "example.com", "newHandle": "DNA-9"}]}),
            ok({"results": [{"fieldValue": "ada@example.com", "isUserVerified": False}]}),
            api_error(400, dna.ErrorCode.VERIFICATION_ALREADY_DONE, "already verified"),
            api_error(404, "x", "nope"),
        )
        details = client.contacts.get("DNA 1")
        self.assertEqual(details.contact.first_name, "Ada")
        self.assertTrue(details.verifications[0].verified)
        self.assertEqual(transport.last.path, "/api/v1/contacts/DNA%201")
        res = client.contacts.update("DNA-1", sample_contact())
        self.assertEqual(res.stats.total_domain_count, 2)
        self.assertEqual(res.affected_domains[0].new_handle, "DNA-9")
        self.assertEqual(transport.last.method, "PUT")
        v = client.contacts.verification("DNA-1")
        self.assertEqual(v[0].field_value, "ada@example.com")
        self.assertEqual(transport.last.param("HandleCode"), "DNA-1")
        client.contacts.resend_verification("DNA-1")  # already verified: no error
        self.assertJSON(transport.last.body, {"handleCode": "DNA-1"})
        with self.assertRaises(dna.NotFoundError):
            client.contacts.resend_verification("DNA-1")

    def test_update_failure(self):
        _, client = fake(ok({"contactUpdateSuccess": False}))
        with self.assertRaises(dna.OperationError):
            client.contacts.update("DNA-1", sample_contact())


class DomainSearchTest(TestCase):
    def test_search(self):
        transport, client = fake(
            ok({"operationMessage": "Command completed successfully", "code": "1000", "success": True,
                "info": {"domainName": "example.com", "tld": "COM", "isPremium": None, "currency": "TRY",
                         "period": 1, "price": 399.9, "status": "AVAILABLE"}}),
            ok({"operationMessage": "Unsupported TLD", "code": "2306", "reason": "TLD not supported",
                "success": False, "info": None}),
            currency="try",
        )
        a = client.domains.search(" example.com ")
        self.assertTrue(a.available)
        self.assertEqual((a.price, a.currency, a.is_premium), (399.9, "TRY", False))
        self.assertJSON(transport.last.body, {"domainName": "example.com", "currency": "TRY"})
        with self.assertRaises(dna.OperationError) as ctx:
            client.domains.search("example.invalid")
        self.assertEqual(ctx.exception.code, "2306")
        self.assertIs(ctx.exception.kind, dna.ErrorKind.REJECTED)
        self.assertIn("TLD not supported", str(ctx.exception))
        transport.replies = [ok({"success": True, "info": {}})]
        client.domains.search("example.com", currency="")
        self.assertJSON(transport.last.body, {"domainName": "example.com"})

    def test_bulk_search_splits_long_lists(self):
        transport, client = fake(ok({"success": True, "infos": [{"domainName": "a", "status": "AVAILABLE"}]}))
        names = ["name%d.com" % i for i in range(65)]
        self.assertEqual(len(client.domains.bulk_search(names)), 3)
        self.assertEqual([len(r.json()) for r in transport.requests], [30, 30, 5])
        self.assertEqual(transport.requests[2].json()[0], {"domainName": "name60.com"})
        with self.assertRaises(dna.InputError):
            client.domains.bulk_search([" "])
        client.domains.bulk_search("single.com")
        self.assertEqual(transport.last.json(), [{"domainName": "single.com"}])

    def test_bulk_search_failure(self):
        _, client = fake(ok({"success": False, "code": "2400", "operationMessage": "bad", "infos": []}))
        with self.assertRaises(dna.OperationError):
            client.domains.bulk_search(["a.com"])


class DomainListTest(TestCase):
    def test_list_and_all(self):
        transport, client = fake(
            ok({"totalCount": 0, "items": [
                {"domainName": "a.com", "status": 0, "expirationDate": "2027-01-01T00:00:00", "lockStatus": True,
                 "contacts": {"Registrant": "DNA-1"}, "nameservers": [{"name": "ns1.x.net",
                                                                       "isChildnameServer": False}]},
                {"domainName": "b.com", "status": 7}]}),
            ok({"totalCount": 0, "items": [{"domainName": "c.com", "status": 12}]}),
        )
        got = ["%s=%s" % (d.domain_name, d.status) for d in client.domains.all(
            statuses=[dna.DomainStatus.ACTIVE, "PendingDelete"], page_size=2)]
        self.assertEqual(got, ["a.com=Active", "b.com=PendingDelete", "c.com=PendingHold"])
        first, second = transport.requests
        self.assertEqual(first.param("StatusIds"), "0,7")
        self.assertEqual(second.param("SkipCount"), "2")

        transport.replies = [ok({"totalCount": 1, "items": [{"domainName": "a.com", "contacts": {"Registrant": "DNA-1"},
                                                             "nameservers": [{"name": "ns1.x.net"}]}]})]
        page = client.domains.list(domain_name="a", limit=10, sort="expirationDate desc")
        self.assertEqual(page.total_count, 1)
        self.assertEqual(page.items[0].contacts, {"Registrant": "DNA-1"})
        self.assertEqual(page.items[0].name_servers[0].name, "ns1.x.net")
        self.assertEqual(transport.last.param("Sorting"), "expirationDate desc")

    def test_all_stops_on_error(self):
        _, client = fake(api_error(500, "x", "boom"), retries=0)
        with self.assertRaises(dna.ServerError):
            list(client.domains.all())

    def test_invalid_status(self):
        _, client = fake()
        with self.assertRaises(dna.InputError):
            client.domains.list(statuses=["nope"])


class DomainRegisterTest(TestCase):
    def test_register(self):
        transport, client = fake(
            ok({"success": True, "message": "ok", "domainId": "6f1c", "status": "Active",
                "expirationDate": "2027-11-19T00:00:00"}),
            ok({"success": False, "message": "Domain is not available for registration", "domainId": None}),
        )
        handles = dna.ContactHandles(registrant="DNA-1", admin="DNA-2", tech="DNA-2", billing="DNA-3")
        res = client.domains.register("example.com", handles=handles, years=2,
                                      name_servers=["NS1.example.net", " ns2.example.net "],
                                      tld_attributes={"lang": "en", "flag": True})
        self.assertEqual((res.domain_id, res.expiration_date.year), ("6f1c", 2027))
        self.assertJSON(transport.last.body, {
            "domainName": "example.com", "period": 2, "nameServers": ["NS1.example.net", "ns2.example.net"],
            "handles": [{"contactType": "Registrant", "handle": "DNA-1"}, {"contactType": "Admin", "handle": "DNA-2"},
                        {"contactType": "Tech", "handle": "DNA-2"}, {"contactType": "Billing", "handle": "DNA-3"}],
            "tldAttributes": {"lang": "en", "flag": "true"},
        })
        with self.assertRaises(dna.OperationError) as ctx:
            client.domains.register("example.com", handles="DNA-1", name_servers=["ns1.x.net"])
        self.assertEqual(ctx.exception.message, "Domain is not available for registration")
        self.assertEqual(ctx.exception.path, "/api/v1/domains/register")
        self.assertEqual(len(transport.last.json()["handles"]), 4, "a handle string is used for every role")

        with self.assertRaises(dna.InputError) as ctx:
            client.domains.register("example.com", handles=dna.ContactHandles(registrant="DNA-1"),
                                    name_servers=["ns1.x.net"])
        self.assertIn("every role", str(ctx.exception))
        self.assertEqual(len(transport.requests), 2, "an invalid request was sent")

    def test_register_with_contacts(self):
        transport, client = fake(ok({"success": True}))
        c = sample_contact()
        client.domains.register_with_contacts("example.com", contacts=c, name_servers=["ns1.x.net"])
        contacts = transport.last.json()["contacts"]
        self.assertEqual([x["contactType"] for x in contacts], ["Registrant", "Admin", "Tech", "Billing"])
        self.assertTrue(all("handle" not in x for x in contacts))

        with self.assertRaises(dna.InputError) as ctx:
            client.domains.register_with_contacts("example.com", contacts=dna.DomainContacts(registrant=c),
                                                  name_servers=["ns1.x.net"])
        self.assertIn("contacts.admin: is required", str(ctx.exception))

        client.domains.register_with_contacts("example.de", name_servers=["ns1.x.net"], use_trustee_contact=True)
        self.assertJSON(transport.last.body, {"domainName": "example.de", "period": 1, "nameServers": ["ns1.x.net"],
                                              "useTrusteeContact": True})

    def test_renew_and_balance(self):
        transport, client = fake(
            api_error(400, "Dna.DepositService:Deposit:10002", "Insufficient balance."),
            ok({"renewabilityStatus": True, "renewalLock": False, "isPremium": True, "premiumPrice": 120,
                "premiumCurrency": "USD"}),
            ok({"success": True, "expirationDate": "2028-01-01T00:00:00"}),
        )
        with self.assertRaises(dna.InsufficientBalanceError):
            client.domains.renew("example.com", 1)
        rc = client.domains.renew_check("example.com")
        self.assertTrue(rc.renewable)
        self.assertEqual(rc.premium_price, 120.0)
        self.assertJSON(transport.last.body, {"domainName": "example.com"})
        self.assertEqual(client.domains.renew("example.com", 3).expiration_date.year, 2028)
        self.assertJSON(transport.last.body, {"domainName": "example.com", "period": 3})

    def test_restore(self):
        transport, client = fake(ok(""))
        self.assertIsNone(client.domains.restore("example.com"))
        self.assertEqual(transport.last.path, "/api/v1/domains/restore")


class DomainTransferTest(TestCase):
    def test_transfer(self):
        transport, client = fake(
            ok({"messageKey": "TransferAvailable", "authCodeIsRequired": True, "authCodeIsValid": True,
                "transferLock": False, "transferAvailabilityStatus": True, "domainStatuses": ["ok"],
                "additionalAttributes": [], "premiumPrice": 0}),
            ok({"success": True, "status": "WaitingForIncomingTransfer"}),
            ok({"domainName": "example.com", "status": "pending", "requestedDate": "2026-11-19"}),
        )
        tc = client.domains.transfer_check("example.com", " Xy7!kP2q")
        self.assertTrue(tc.transferable and tc.auth_code_valid)
        self.assertEqual(tc.domain_statuses, ["ok"])
        self.assertJSON(transport.last.body, {"domainName": "example.com", "authCode": " Xy7!kP2q"})
        self.assertEqual(client.domains.transfer("example.com", "Xy7!kP2q", years=1).status,
                         "WaitingForIncomingTransfer")
        self.assertJSON(transport.last.body, {"domainName": "example.com", "authCode": "Xy7!kP2q", "period": 1})
        self.assertEqual(client.domains.transfer_status("example.com").status, "pending")


class DomainSettingsTest(TestCase):
    def test_settings(self):
        transport, client = fake(ok(""), ok(""), ok({"domainName": "example.com", "authCode": "New!Code1"}),
                                 ok(""), ok(""), ok(""), ok(""), ok(""))
        client.domains.set_privacy("example.com", False)
        self.assertJSON(transport.last.body, {"domainName": "example.com", "privacyStatus": False})
        client.domains.lock("example.com")
        self.assertEqual(transport.last.path, "/api/v1/domains/lock")
        self.assertEqual(client.domains.update_auth_code("example.com"), "New!Code1")
        self.assertEqual(transport.last.method, "PUT")

        client.domains.set_name_servers("example.com", ["NS1.Example.net", " ", "ns2.example.net"],
                                        dnssec_mode="disable")
        self.assertJSON(transport.last.body, {"domainName": "example.com",
                                              "nameServers": ["ns1.example.net", "ns2.example.net"], "dnssecMode": 2})

        client.domains.add_host("example.com", "ns1.example.com", ["192.0.2.10", "2001:db8::10"])
        self.assertJSON(transport.last.body, {"domainName": "example.com", "hostName": "ns1.example.com",
                                              "ipAddresses": [{"ipAddress": "192.0.2.10", "ipVersion": "v4"},
                                                              {"ipAddress": "2001:db8::10", "ipVersion": "v6"}]})
        client.domains.update_host("example.com", "ns1.example.com", "192.0.2.20", new_host_name="ns3.example.com")
        self.assertEqual(transport.last.json()["newHostName"], "ns3.example.com")
        client.domains.delete_host("example.com", "ns1.example.com")
        self.assertEqual((transport.last.method, transport.last.param("HostName")), ("DELETE", "ns1.example.com"))
        client.domains.unlock("example.com")

        with self.assertRaises(dna.InputError) as ctx:
            client.domains.add_host("example.com", "ns1.example.com", ["300.1.1.1"])
        self.assertIn("300.1.1.1 is not an IP address", str(ctx.exception))
        with self.assertRaises(dna.InputError):
            client.domains.set_name_servers("example.com", [])
        with self.assertRaises(dna.InputError):
            client.domains.set_name_servers("example.com", ["ns1.x"], dnssec_mode=7)

    def test_domain_contacts(self):
        transport, client = fake(ok(""), ok(""))
        client.domains.set_contact_handles("example.com", dna.ContactHandles(admin="DNA-2", tech="DNA-2"))
        self.assertJSON(transport.last.body, {"domainName": "example.com", "handleItems": [
            {"contactType": "Admin", "handle": "DNA-2"}, {"contactType": "Tech", "handle": "DNA-2"}]})
        client.domains.update_contacts("example.com", dna.DomainContacts(billing=sample_contact()))
        contacts = transport.last.json()["contacts"]
        self.assertEqual([c["contactType"] for c in contacts], ["Billing"])
        with self.assertRaises(dna.InputError):
            client.domains.update_contacts("example.com", dna.DomainContacts())
        with self.assertRaises(dna.InputError):
            client.domains.set_contact_handles("example.com", dna.ContactHandles())


class DomainDocumentsTest(TestCase):
    def test_documents(self):
        transport, client = fake(
            ok({"uploaded": [{"name": "id.pdf", "size": 8, "type": 1}], "duplicates": [], "failed": [],
                "totalDocumentCount": 1}),
            ok({"totalCount": 1, "items": [{"name": "id.pdf", "type": 1, "status": 2, "operationType": 1}]}),
        )
        doc = dna.DocumentUpload(dna.DocumentType.IDENTITY_CARD, "id.pdf", b"%PDF-1.4")
        res = client.domains.upload_documents("example.com.tr", doc)
        self.assertIs(res.uploaded[0].type, dna.DocumentType.IDENTITY_CARD)
        self.assertJSON(transport.last.body, {"domainName": "example.com.tr", "documents": [
            {"documentType": 1, "fileName": "id.pdf", "fileContent": "JVBERi0xLjQ="}]})
        page = client.domains.documents("example.com.tr", types=["IdentityCard", 2])
        self.assertIs(page.items[0].status, dna.DocumentStatus.PENDING)
        self.assertEqual(transport.last.param("DocumentTypes"), "1,2")

        for bad, message in (
            (dna.DocumentUpload(1, "id.exe", b"x"), "must be a PDF"),
            (dna.DocumentUpload(1, "id.pdf", b""), "is empty"),
            (dna.DocumentUpload(1, "id.pdf", b"x" * (dna.MAX_DOCUMENT_SIZE + 1)), "larger than 10 MB"),
            (dna.DocumentUpload(77, "id.pdf", b"x"), "documents[0].type"),
        ):
            with self.assertRaises(dna.InputError) as ctx:
                client.domains.upload_documents("example.com.tr", bad)
            self.assertIn(message, str(ctx.exception))


class DomainForwardingTest(TestCase):
    def test_forwarding(self):
        transport, client = fake(
            ok({"redirectAlias": "https://www.example.org", "redirectType": "Frame"}),
            api_error(404, dna.ErrorCode.FORWARDING_NOT_FOUND, "Redirect information not found"),
            ok({"redirectAlias": "", "redirectType": None}),
            ok(""),
            api_error(404, dna.ErrorCode.FORWARDING_NOT_FOUND, "Redirect information not found"),
            api_error(404, dna.ErrorCode.DOMAIN_NOT_FOUND, "Domain not found"),
            ok(""),
        )
        f = client.domains.forwarding("example.com")
        self.assertEqual((f.url, f.type), ("https://www.example.org", dna.ForwardType.FRAME))
        self.assertEqual(transport.last.param("domainName"), "example.com")
        self.assertIsNone(client.domains.forwarding("example.com"))
        self.assertIsNone(client.domains.forwarding("example.com"))
        client.domains.delete_forwarding("example.com")
        self.assertEqual(transport.last.param("DomainName"), "example.com")
        client.domains.delete_forwarding("example.com")  # had none: no error
        with self.assertRaises(dna.NotFoundError):
            client.domains.delete_forwarding("nope.com")
        client.domains.set_forwarding("example.com", "https://www.example.org", "frame")
        self.assertJSON(transport.last.body, {"domainName": "example.com", "redirectAddress": "https://www.example.org",
                                              "forwardType": "Frame"})
        for url, kind in (("www.example.org", "standard"), ("https://x.org", "masked"), ("", "standard")):
            with self.assertRaises(dna.InputError):
                client.domains.set_forwarding("example.com", url, kind)


class DNSTest(TestCase):
    def test_zone(self):
        transport, client = fake(
            ok(""),
            ok(""),
            ok(""),
            ok([{"name": "example.com.", "type": "A", "ttl": 600, "records": [{"content": "192.0.2.10"}]},
                {"name": "www.example.com.", "type": "CNAME", "ttl": 3600,
                 "records": [{"content": "example.com."}]}]),
            ok({"nameServersChanged": True, "previousNameServers": ["ns1.other.net"],
                "currentNameServers": ["ns1.domainnameapi.com"]}),
        )
        client.dns.add("example.com", "www", "a", "192.0.2.10", ttl=600)
        self.assertEqual(transport.last.param("domainName"), "example.com")
        self.assertJSON(transport.last.body, {"zoneStruct": {"name": "www", "type": "A", "ttl": 600,
                                                             "contents": ["192.0.2.10"]}})
        client.dns.update("example.com", "www", dna.RecordType.TXT, ["v=spf1 -all"], name="@")
        self.assertEqual(transport.last.param("recordName"), "www")
        self.assertJSON(transport.last.body, {"zoneStruct": {"name": "", "type": "TXT", "ttl": 3600,
                                                             "contents": ["v=spf1 -all"]}})
        client.dns.delete("example.com", "@", "mx", "10 mail.example.com")
        r = transport.last
        self.assertEqual((r.method, r.param("Name"), r.param("RecordType"), r.param("Record")),
                         ("DELETE", "", "MX", "10 mail.example.com"))
        sets = client.dns.list("example.com")
        self.assertEqual([s.values for s in sets], [["192.0.2.10"], ["example.com."]])
        res = client.dns.apply("example.com")
        self.assertTrue(res.name_servers_changed)
        self.assertEqual(res.current_name_servers, ["ns1.domainnameapi.com"])

    def test_find(self):
        _, client = fake(ok([{"name": "www.example.com.", "type": "A", "records": [{"content": "192.0.2.1"}]}]))
        self.assertEqual(client.dns.find("example.com", "www", "A").values, ["192.0.2.1"])
        self.assertIsNone(client.dns.find("example.com", "www", "AAAA"))

    def test_validation(self):
        transport, client = fake()
        cases = [
            (("example.com", "@", "CNAME", "target.example.net"), "a CNAME cannot be at the apex"),
            (("example.com", "www", "CNAME", "192.0.2.1"), "not an IP address"),
            (("example.com", "@", "MX", "mail.example.com"), "PRIORITY HOST"),
            (("example.com", "@", "CAA", "issue letsencrypt.org"), "3 parts"),
            (("example.com", "www", "A", "2001:db8::1"), "not an IPv4 address"),
            (("example.com", "www", "AAAA", "192.0.2.1"), "not an IPv6 address"),
            (("example.com", "www", "SPF", "v=spf1"), "not a DNS record type"),
            (("example.com", "@www", "A", "192.0.2.1"), "must not start with @"),
            (("example.com", "www", "A", []), "values: needs at least one value"),
        ]
        for args, message in cases:
            with self.subTest(message):
                with self.assertRaises(dna.InputError) as ctx:
                    client.dns.add(*args)
                self.assertIn(message, str(ctx.exception))
        with self.assertRaises(dna.InputError):
            client.dns.add("example.com", "www", "A", "192.0.2.1", ttl=90000)
        with self.assertRaises(dna.InputError):
            client.dns.delete("example.com", "www", "A", "")
        self.assertEqual(transport.requests, [])


class DNSSECTest(TestCase):
    def test_dnssec(self):
        transport, client = fake(
            ok({"items": [{"keyTag": 2371, "operationType": 0, "isSuccess": False, "isPending": True}]}),
            ok({"domainName": "example.com", "isDnssecAvailable": True, "status": 2,
                "dsRecords": [{"keyTag": 2371, "algorithm": 13, "digestType": 2, "digest": "1F98", "status": 1}],
                "allowedAlgorithms": [8, 13], "allowedDigestTypes": [2]}),
            ok({"keyTag": 2371, "operationType": 1, "isSuccess": True}),
            ok({"operationType": 2, "isSuccess": False, "isPending": False, "resultMessage": "Registry refused"}),
        )
        results = client.dnssec.add("example.com", "2371 13 2 1f98 abcd")
        self.assertTrue(results[0].pending)
        self.assertJSON(transport.last.body, {"domainName": "example.com", "records": [
            {"keyTag": 2371, "algorithm": 13, "digestType": 2, "digest": "1F98ABCD"}]})
        info = client.dnssec.get("example.com")
        self.assertIs(info.status, dna.DNSSECStatus.SIGNED)
        self.assertEqual(info.allowed_algorithms, [dna.DNSSECAlgorithm.RSASHA256, dna.DNSSECAlgorithm.ECDSAP256SHA256])
        self.assertIs(info.ds_records[0].status, dna.DSRecordStatus.ACTIVE)
        res = client.dnssec.remove("example.com", dna.DS(2371, 13, 2, "1F98"))
        self.assertIs(res.operation_type, dna.DNSSECOperationType.REMOVE)
        r = transport.last
        self.assertEqual((r.param("KeyTag"), r.param("Algorithm"), r.param("DigestType"), r.param("Digest")),
                         ("2371", "13", "2", "1F98"))
        with self.assertRaises(dna.OperationError) as ctx:
            client.dnssec.disable("example.com")
        self.assertEqual(ctx.exception.message, "Registry refused")
        with self.assertRaises(dna.InputError):
            client.dnssec.add("example.com", "not a ds record")
        with self.assertRaises(dna.InputError):
            client.dnssec.add("example.com", [])


class SSLTest(TestCase):
    def test_flow(self):
        transport, client = fake(
            ok({"csr": "-----BEGIN CERTIFICATE REQUEST-----", "privateKey": "-----BEGIN PRIVATE KEY-----"}),
            ok({"success": True, "certificateId": CERT_ID, "status": "WaitingForInstall"}),
            ok({"success": True, "certificateId": CERT_ID, "status": "WaitingForValidation",
                "dcvDetails": "CNAME _abc"}),
            ok({"certificateId": CERT_ID, "domainName": "example.com", "status": "Active", "isIssued": True,
                "certificateExpiresAt": "2027-11-20T00:00:00"}),
            ok({"certificateId": CERT_ID, "certificate": "CERT", "intermediateCertificate1": "INT1",
                "rootCertificate": "ROOT"}),
            ok({"certificateId": CERT_ID, "domainName": "example.com", "status": "Active",
                "packageCode": "PositiveSSL", "subscription": {"expiresAt": "2027-11-20T00:00:00"}}),
            ok({"success": True, "certificateId": CERT_ID, "csr": "NEW CSR", "privateKey": "NEW KEY"}),
            ok({"success": False, "message": "Already revoked"}),
        )
        csr = client.ssl.generate_csr("example.com", country="tr", state="Istanbul", locality="Istanbul",
                                      organization="Example Ltd", organization_unit="IT")
        self.assertEqual(transport.last.json()["country"], "TR")
        self.assertNotIn("alternativeNames", transport.last.json())

        order = client.ssl.initialize("example.com", "PositiveSSL")
        self.assertEqual(order.certificate_id, CERT_ID)
        self.assertEqual(transport.last.json(), {"domainName": "example.com", "packageCode": "PositiveSSL"})

        res = client.ssl.configure(order.certificate_id, csr=csr.csr,
                                   contact=sample_ssl_contact(phone="+90 555 123 4567"),
                                   approver_mail="admin@example.com", authentication_type="email",
                                   web_server_type=dna.WebServerType.APACHE, san_list=["a.example.com",
                                                                                       "b.example.com"])
        self.assertEqual(res.dcv_details, "CNAME _abc")
        body = transport.last.json()
        self.assertEqual(body["certificateId"], CERT_ID)
        self.assertNotIn("domainName", body)
        self.assertEqual((body["authenticationType"], body["webServerType"], body["sanList"]),
                         ("Email", "Apache", "a.example.com,b.example.com"))
        self.assertEqual(body["contact"]["phone"], "905551234567")
        self.assertNotIn("wildcardList", body)

        st = client.ssl.status(CERT_ID)
        self.assertTrue(st.is_issued)
        self.assertEqual((st.certificate_id, st.domain_name, st.expires_at.year), (CERT_ID, "example.com", 2027))
        r = transport.last
        self.assertEqual((r.method, r.path, r.json()), ("PUT", "/api/v1/ssls/check-status",
                                                        {"certificateId": CERT_ID}))

        content = client.ssl.content(CERT_ID)
        self.assertEqual((content.certificate_id, content.chain), (CERT_ID, "CERT\nINT1\n"))
        self.assertEqual(transport.last.query, {"CertificateId": [CERT_ID]})

        cert = client.ssl.get(CERT_ID)
        self.assertEqual((cert.certificate_id, cert.package_code, cert.subscription.expires_at.year),
                         (CERT_ID, "PositiveSSL", 2027))
        self.assertEqual(transport.last.query, {"CertificateId": [CERT_ID]})

        reissued = client.ssl.reissue(CERT_ID, approver_mail="admin@example.com")
        self.assertEqual((reissued.csr, reissued.private_key), ("NEW CSR", "NEW KEY"))
        self.assertEqual(transport.last.json(), {"certificateId": CERT_ID, "approverMail": "admin@example.com"})

        with self.assertRaises(dna.OperationError):
            client.ssl.revoke(CERT_ID)
        r = transport.last
        self.assertEqual((r.method, r.path, r.query, r.body), ("DELETE", "/api/v1/ssls/revoke",
                                                               {"CertificateId": [CERT_ID]}, b""))

    def test_renew(self):
        transport, client = fake(
            ok({"success": True, "certificateId": RENEWAL_ID, "status": "WaitingForInstall",
                "message": "SSL certificate renewal initialized successfully. Waiting for installation."}),
            ok({"success": True, "certificateId": RENEWAL_ID, "status": "WaitingForValidation"}),
            ok({"success": False, "message": "Renewal is not open yet"}),
        )
        res = client.ssl.renew(CERT_ID)
        self.assertEqual((res.certificate_id, res.status), (RENEWAL_ID, "WaitingForInstall"))
        r = transport.last
        self.assertEqual((r.method, r.path, r.json()), ("POST", "/api/v1/ssls/renew", {"certificateId": CERT_ID}))

        # The renewal is a new certificate: it is configured with the id renew returned.
        client.ssl.configure(res.certificate_id, csr="csr", contact=sample_ssl_contact())
        self.assertEqual(transport.last.json()["certificateId"], RENEWAL_ID)

        with self.assertRaises(dna.OperationError) as ctx:
            client.ssl.renew(CERT_ID)
        self.assertEqual(ctx.exception.message, "Renewal is not open yet")

    def test_renew_is_billable(self):
        """renew has the safety class of initialize: never repeated blindly, blocked by a read-only client."""
        renew = dna.SSLRenewRequest(CERT_ID).endpoint()
        initialize = dna.SSLInitializeRequest("example.com", "PositiveSSL").endpoint()
        self.assertIs(renew.safety, dna.Safety.BILLABLE)
        self.assertEqual((renew.safety, renew.idempotent), (initialize.safety, initialize.idempotent))
        self.assertFalse(renew.idempotent)

        transport, client = fake(Reply(503), ok({"success": True}))
        with self.assertRaises(dna.ServerError):
            client.ssl.renew(CERT_ID)
        self.assertEqual(len(transport.requests), 1, "a billable request was repeated")

        transport, client = fake(dna.TransportError("connection reset by peer"), ok({"success": True}))
        with self.assertRaises(dna.NetworkError) as ctx:
            client.ssl.renew(CERT_ID)
        self.assertEqual(len(transport.requests), 1, "a billable request was repeated")
        self.assertTrue(ctx.exception.outcome_unknown)

        transport, client = fake(Reply(429, "", {"Retry-After": "1"}), ok({"success": True}))
        client.ssl.renew(CERT_ID)  # a 429 is rejected before anything happens, so it is retried
        self.assertEqual(len(transport.requests), 2)

        transport, client = fake(ok({"success": True}), read_only=True)
        with self.assertRaises(dna.ReadOnlyError):
            client.ssl.renew(CERT_ID)
        self.assertEqual(transport.requests, [])

        _, client = fake(api_error(402, "Dna.SslService:Ssl:10045", "Insufficient balance"))
        with self.assertRaises(dna.InsufficientBalanceError):
            client.ssl.renew(CERT_ID)

    def test_list(self):
        transport, client = fake(
            ok({"totalCount": 3, "items": [
                {"certificateId": RENEWAL_ID, "domainName": "example.com", "packageCode": "PositiveSSL",
                 "packageName": "Positive SSL", "status": "WaitingForInstall", "statusReason": "None",
                 "isConfigured": False, "isIssued": False, "purchasedAt": "2026-11-20T10:00:00",
                 "subscriptionExpiresAt": "2027-11-20T10:00:00", "certificateExpiresAt": None,
                 "renewedFromCertificateId": CERT_ID},
                {"certificateId": CERT_ID, "domainName": "example.com", "status": "Active", "isConfigured": True,
                 "isIssued": True, "certificateExpiresAt": "2026-12-01T00:00:00Z",
                 "renewedFromCertificateId": None}]}),
            ok({"totalCount": 0, "items": []}),
        )
        page = client.ssl.list(domain_name=" example.com ", limit=2)
        self.assertEqual((page.total_count, len(page)), (3, 2))
        r = transport.last
        self.assertEqual((r.method, r.path), ("GET", "/api/v1/ssls"))
        self.assertEqual(r.query, {"DomainName": ["example.com"], "MaxResultCount": ["2"]})
        first, second = page
        self.assertEqual((first.certificate_id, first.domain_name, first.package_code, first.package_name),
                         (RENEWAL_ID, "example.com", "PositiveSSL", "Positive SSL"))
        self.assertEqual((first.status, first.status_reason, first.is_configured, first.is_issued),
                         ("WaitingForInstall", "None", False, False))
        self.assertEqual((first.purchased_at.year, first.subscription_expires_at.year), (2026, 2027))
        self.assertIsNone(first.certificate_expires_at)
        self.assertEqual(first.renewed_from_certificate_id, CERT_ID)
        self.assertEqual((second.is_issued, second.certificate_expires_at.month, second.renewed_from_certificate_id),
                         (True, 12, ""))

        client.ssl.list(skip=2, limit=2)
        self.assertEqual(transport.last.query, {"SkipCount": ["2"], "MaxResultCount": ["2"]})
        self.assertEqual(len(client.ssl.list()), 0)
        self.assertEqual(transport.last.query, {})
        with self.assertRaises(dna.InputError):
            client.ssl.list(skip=-1)
        with self.assertRaises(dna.InputError):
            client.ssl.list(limit=-1)
        self.assertEqual(len(transport.requests), 3)

    def test_all_fetches_every_page(self):
        transport, client = fake(
            ok({"totalCount": 3, "items": [{"certificateId": CERT_ID}, {"certificateId": RENEWAL_ID}]}),
            ok({"totalCount": 3, "items": [{"certificateId": "c-3"}]}),
        )
        ids = [c.certificate_id for c in client.ssl.all(domain_name="example.com", page_size=2)]
        self.assertEqual(ids, [CERT_ID, RENEWAL_ID, "c-3"])
        first, second = transport.requests
        self.assertEqual(first.query, {"DomainName": ["example.com"], "MaxResultCount": ["2"]})
        self.assertEqual(second.query, {"DomainName": ["example.com"], "SkipCount": ["2"], "MaxResultCount": ["2"]})

    def test_approvers(self):
        mails = ["admin@example.com", "hostmaster@example.com"]
        transport, client = fake(ok({"mails": mails}))
        # An existing certificate.
        self.assertEqual(client.ssl.approvers(certificate_id=CERT_ID), mails)
        r = transport.last
        self.assertEqual((r.method, r.path, r.query), ("GET", "/api/v1/ssls/approvers", {"CertificateId": [CERT_ID]}))
        # Before a purchase.
        self.assertEqual(client.ssl.approvers(domain_name="example.com", package_code="PositiveSSL"), mails)
        self.assertEqual(transport.last.query, {"DomainName": ["example.com"], "PackageCode": ["PositiveSSL"]})

        _, client = fake(ok(None))
        self.assertEqual(client.ssl.approvers(certificate_id=CERT_ID), [])

    def test_approvers_validation(self):
        transport, client = fake()
        with self.assertRaises(dna.InputError) as ctx:
            client.ssl.approvers(domain_name="example.com")
        self.assertEqual([f.field for f in ctx.exception.fields], ["package_code"])
        self.assertIn("package_code: is required with domain_name", str(ctx.exception))
        for kwargs in ({}, {"package_code": "PositiveSSL"}, {"certificate_id": " ", "domain_name": " "}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(dna.InputError) as ctx:
                    client.ssl.approvers(**kwargs)
                self.assertIn("pass certificate_id (an existing certificate), or domain_name and package_code",
                              str(ctx.exception))
        with self.assertRaises(dna.InputError) as ctx:
            client.ssl.approvers(certificate_id="example.com")
        self.assertIn("must be a certificate id (GUID)", str(ctx.exception))
        with self.assertRaises(TypeError):
            client.ssl.approvers("example.com")  # keyword-only: the old positional domain name is refused
        self.assertEqual(transport.requests, [])

    def test_certificate_id_guard(self):
        """A domain name passed where the API now wants a certificate id never reaches the API."""
        transport, client = fake(ok({"success": True}))
        calls = {
            "SSLConfigureRequest": lambda value: client.ssl.configure(value, csr="csr", contact=sample_ssl_contact()),
            "SSLStatusRequest": client.ssl.status,
            "SSLGetRequest": client.ssl.get,
            "SSLContentRequest": client.ssl.content,
            "SSLReissueRequest": client.ssl.reissue,
            "SSLRevokeRequest": client.ssl.revoke,
            "SSLRenewRequest": client.ssl.renew,
        }
        not_ids = ("example.com", "*.example.com", "c-1", CERT_ID[:-1], CERT_ID + "0", "{%s}" % CERT_ID,
                   CERT_ID.replace("-", ""), CERT_ID.replace("a", "g"))
        for name, call in calls.items():
            for bad in not_ids:
                with self.subTest(request=name, value=bad):
                    with self.assertRaises(dna.InputError) as ctx:
                        call(bad)
                    err = ctx.exception
                    self.assertEqual((err.request, [f.field for f in err.fields]), (name, ["certificate_id"]))
                    self.assertIs(err.kind, dna.ErrorKind.INVALID_INPUT)
                    text = str(err)
                    self.assertIn("certificate_id: must be a certificate id (GUID), got %r" % bad, text)
                    self.assertIn("no longer addressed by domain name", text)
                    self.assertIn("ssl.initialize or ssl.renew", text)
                    self.assertIn("client.ssl.list(domain_name=...)", text)
            for blank in ("", "   ", None):
                with self.subTest(request=name, value=blank):
                    with self.assertRaises(dna.InputError) as ctx:
                        call(blank)
                    self.assertIn("certificate_id: is required", str(ctx.exception))
        self.assertEqual(transport.requests, [], "an invalid certificate id was sent")

    def test_certificate_id_is_trimmed_and_any_case(self):
        transport, client = fake(ok({"certificateId": CERT_ID}))
        client.ssl.status("  %s\n" % CERT_ID.upper())
        self.assertEqual(transport.last.json(), {"certificateId": CERT_ID.upper()})
        client.ssl.get(uuid.UUID(CERT_ID))
        self.assertEqual(transport.last.query, {"CertificateId": [CERT_ID]})

    def test_validation(self):
        transport, client = fake()
        with self.assertRaises(dna.InputError) as ctx:
            client.ssl.configure(CERT_ID, csr="", contact=dna.SSLContact(), approver_mail="nope")
        fields = {f.field for f in ctx.exception.fields}
        self.assertTrue({"csr", "approver_mail", "contact.first_name", "contact.company_name"} <= fields)
        self.assertNotIn("certificate_id", fields)
        with self.assertRaises(dna.InputError):
            client.ssl.generate_csr("example.com", country="Turkey", state="", locality="", organization="",
                                    organization_unit="")
        self.assertEqual(transport.requests, [])


class HostingTest(TestCase):
    def test_wait(self):
        transport, client = fake(
            ok({"serviceId": "HST-1", "status": "Provisioning"}),
            ok({"serviceId": "HST-1", "status": "Provisioning"}),
            ok({"serviceId": "HST-1", "status": "Active", "panelAddress": "https://panel", "username": "u",
                "password": "p"}),
        )
        st = client.hosting.wait("HST-1")
        self.assertEqual((st.panel_address, st.username, st.password), ("https://panel", "u", "p"))
        self.assertEqual(client.slept, [5.0, 5.0])
        self.assertEqual(transport.last.param("ServiceId"), "HST-1")

    def test_wait_failure_and_timeout(self):
        _, client = fake(ok({"status": "Failed", "failureReason": "No capacity"}))
        with self.assertRaises(dna.OperationError) as ctx:
            client.hosting.wait("HST-1")
        self.assertEqual((ctx.exception.code, ctx.exception.message), ("Failed", "No capacity"))

        _, client = fake(ok({"status": "Provisioning"}))
        now = [0.0]
        client._clock = lambda: now[0]

        def sleep(seconds):
            now[0] += seconds

        client._sleep = sleep
        with self.assertRaises(dna.WaitTimeoutError) as ctx:
            client.hosting.wait("HST-1", timeout=200)
        self.assertEqual(ctx.exception.last.status, "Provisioning")
        self.assertLessEqual(now[0], 200)

    def test_lookups(self):
        transport, client = fake(
            ok([{"name": "Linux", "servicePlans": [{"servicePlan": "Linux-Starter", "operatingSystem": "Linux"}]}]),
            ok([{"name": "Starter", "diskQuotaMb": 1024, "maxDomains": None}]),
            ok({"serviceId": "HST-1", "status": "Provisioning", "token": "tok"}),
            ok({"hostingId": "6f1c", "serviceId": "HST-1", "expiredOn": "2027-01-01T00:00:00"}),
            ok({"serviceId": "HST-1"}),
        )
        packages = client.hosting.packages()
        self.assertEqual(packages[0].service_plans[0].service_plan, "Linux-Starter")
        plans = client.hosting.plans("6f1c")
        self.assertEqual(transport.last.param("hostingId"), "6f1c")
        self.assertIsNone(plans[0].max_domains)
        self.assertEqual(client.hosting.create("example.com", "Linux-Starter").token, "tok")
        h = client.hosting.get(domain_name="example.com")
        self.assertEqual(h.expires_on.year, 2027)
        self.assertEqual(transport.last.param("domainName"), "example.com")
        client.hosting.get_by_token("tok")
        self.assertEqual(transport.last.param("token"), "tok")
        with self.assertRaises(dna.InputError):
            client.hosting.get(service_id="HST-1", domain_name="example.com")
        with self.assertRaises(dna.InputError):
            client.hosting.status()


class OrdersAndProductsTest(TestCase):
    def test_order(self):
        transport, client = fake(ok({"orderCode": "ORD-1", "status": 1, "amount": 9.99, "products": [
            {"productCode": "com", "productType": 1, "orderType": 2, "status": 1, "period": 1}]}))
        order = client.orders.get("ORD-1")
        self.assertIs(order.status, dna.OrderStatus.ACTIVE)
        self.assertIs(order.products[0].order_type, dna.OrderType.RENEW)
        self.assertEqual(transport.last.path, "/api/v1/order/ORD-1")

    def test_products(self):
        transport, client = fake(
            ok({"totalCount": 1, "items": [{"id": "p1", "productName": ".com", "productType": 1}]}),
            ok({"productName": "com", "sellingPrice": 19.5, "sellingCurrency": "USD", "subproducts": []}),
            ok({"totalCount": 2, "items": [{"name": "com.tr"}, {"name": "tr"}]}),
            ok({"totalCount": 1, "items": [{"name": "PositiveSSL", "productCode": "PositiveSSL"}]}),
            currency="usd",
        )
        page = client.products.list(product_type="domain", limit=10)
        self.assertIs(page.items[0].product_type, dna.ProductType.DOMAIN)
        self.assertEqual(transport.last.param("ProductType"), "1")
        info = client.products.info(".com", "renew", 2)
        self.assertEqual(info.selling_price, 19.5)
        r = transport.last
        self.assertEqual((r.param("ProductName"), r.param("OrderType"), r.param("Period")), ("com", "2", "2"))
        tld = client.products.tld(".TR")
        self.assertEqual(tld.name, "tr")
        self.assertEqual((transport.last.param("FilterText"), transport.last.param("Currency")), ("tr", "USD"))
        client.products.ssls(is_wildcard=False, vendor_name="Sectigo")
        self.assertEqual((transport.last.param("IsWildcard"), transport.last.param("VendorName")),
                         ("false", "Sectigo"))
        self.assertIsNone(transport.last.param("IsMultiDomain"))
        with self.assertRaises(dna.InputError):
            client.products.info("com", "nope", 1)
        with self.assertRaises(dna.InputError):
            client.products.info("com", dna.OrderType.REGISTER, 0)

    def test_tld_not_found(self):
        _, client = fake(ok({"totalCount": 1, "items": [{"name": "com.tr"}]}))
        self.assertIsNone(client.products.tld("tr"))


class EveryServiceMethodTest(TestCase):
    """Every service method sends its request to the right place with the right safety class."""

    def test_table(self):
        c = sample_contact()
        cases = [
            ("account.get", lambda cl: cl.account.get(), "GET", "/api/v1/deposit/accounts/me"),
            ("account.profile", lambda cl: cl.account.profile(), "GET", "/api/v1/resellers/me"),
            ("account.transactions", lambda cl: cl.account.transactions(), "GET", "/api/v1/deposit/transactions"),
            ("contacts.get", lambda cl: cl.contacts.get("DNA-1"), "GET", "/api/v1/contacts/DNA-1"),
            ("contacts.create", lambda cl: cl.contacts.create(c), "POST", "/api/v1/contacts"),
            ("contacts.update", lambda cl: cl.contacts.update("DNA-1", c), "PUT", "/api/v1/contacts/DNA-1"),
            ("contacts.verification", lambda cl: cl.contacts.verification("DNA-1"), "GET",
             "/api/v1/contacts/verification/check"),
            ("contacts.resend_verification", lambda cl: cl.contacts.resend_verification("DNA-1"), "POST",
             "/api/v1/contacts/verification/request"),
            ("domains.search", lambda cl: cl.domains.search("example.com"), "POST", "/api/v1/domains/search"),
            ("domains.bulk_search", lambda cl: cl.domains.bulk_search(["example.com"]), "POST",
             "/api/v1/domains/bulk-search"),
            ("domains.list", lambda cl: cl.domains.list(), "GET", "/api/v1/domains"),
            ("domains.info", lambda cl: cl.domains.info("example.com"), "GET", "/api/v1/domains/info"),
            ("domains.register", lambda cl: cl.domains.register("example.com", handles="DNA-1",
                                                                name_servers=["ns1.x.net"]),
             "POST", "/api/v1/domains/register"),
            ("domains.register_with_contacts", lambda cl: cl.domains.register_with_contacts(
                "example.com", contacts=c, name_servers=["ns1.x.net"]), "POST",
             "/api/v1/domains/register-with-contacts"),
            ("domains.renew", lambda cl: cl.domains.renew("example.com", 1), "POST", "/api/v1/domains/renew"),
            ("domains.renew_check", lambda cl: cl.domains.renew_check("example.com"), "POST",
             "/api/v1/domains/renew/check"),
            ("domains.restore", lambda cl: cl.domains.restore("example.com"), "POST", "/api/v1/domains/restore"),
            ("domains.transfer", lambda cl: cl.domains.transfer("example.com", "code"), "POST",
             "/api/v1/domains/transfer"),
            ("domains.transfer_check", lambda cl: cl.domains.transfer_check("example.com", "code"), "POST",
             "/api/v1/domains/transfers/check"),
            ("domains.transfer_status", lambda cl: cl.domains.transfer_status("example.com"), "POST",
             "/api/v1/domains/transfers/query"),
            ("domains.lock", lambda cl: cl.domains.lock("example.com"), "POST", "/api/v1/domains/lock"),
            ("domains.unlock", lambda cl: cl.domains.unlock("example.com"), "POST", "/api/v1/domains/unlock"),
            ("domains.set_privacy", lambda cl: cl.domains.set_privacy("example.com", True), "POST",
             "/api/v1/domains/privacy"),
            ("domains.update_auth_code", lambda cl: cl.domains.update_auth_code("example.com"), "PUT",
             "/api/v1/domains/auth"),
            ("domains.set_name_servers", lambda cl: cl.domains.set_name_servers("example.com", ["ns1.x.net"]),
             "PUT", "/api/v1/domains/dns/name-server"),
            ("domains.add_host", lambda cl: cl.domains.add_host("example.com", "ns1.example.com", "192.0.2.1"),
             "POST", "/api/v1/domains/dns/host"),
            ("domains.update_host", lambda cl: cl.domains.update_host("example.com", "ns1.example.com",
                                                                      "192.0.2.1"), "PUT", "/api/v1/domains/dns/host"),
            ("domains.delete_host", lambda cl: cl.domains.delete_host("example.com", "ns1.example.com"), "DELETE",
             "/api/v1/domains/dns/host"),
            ("domains.update_contacts", lambda cl: cl.domains.update_contacts("example.com", dna.DomainContacts(
                admin=c)), "PUT", "/api/v1/domains/contacts/update"),
            ("domains.set_contact_handles", lambda cl: cl.domains.set_contact_handles("example.com", "DNA-1"), "PUT",
             "/api/v1/domains/contacts/update-with-handle"),
            ("domains.documents", lambda cl: cl.domains.documents("example.com.tr"), "GET",
             "/api/v1/domains/documents"),
            ("domains.upload_documents", lambda cl: cl.domains.upload_documents(
                "example.com.tr", dna.DocumentUpload(1, "id.pdf", b"x")), "POST", "/api/v1/domains/documents"),
            ("domains.forwarding", lambda cl: cl.domains.forwarding("example.com"), "GET", "/api/v1/domains/forwards"),
            ("domains.set_forwarding", lambda cl: cl.domains.set_forwarding("example.com", "https://x.org"), "POST",
             "/api/v1/domains/forwards"),
            ("domains.delete_forwarding", lambda cl: cl.domains.delete_forwarding("example.com"), "DELETE",
             "/api/v1/domains/forwards"),
            ("dns.list", lambda cl: cl.dns.list("example.com"), "GET", "/api/v1/domains/zones"),
            ("dns.add", lambda cl: cl.dns.add("example.com", "www", "A", "192.0.2.1"), "POST",
             "/api/v1/domains/zones"),
            ("dns.update", lambda cl: cl.dns.update("example.com", "www", "A", "192.0.2.1"), "PUT",
             "/api/v1/domains/zones"),
            ("dns.delete", lambda cl: cl.dns.delete("example.com", "www", "A", "192.0.2.1"), "DELETE",
             "/api/v1/domains/zones"),
            ("dns.apply", lambda cl: cl.dns.apply("example.com"), "POST", "/api/v1/domains/zones/apply"),
            ("dnssec.get", lambda cl: cl.dnssec.get("example.com"), "GET", "/api/v1/domains/dns/dnssec"),
            ("dnssec.add", lambda cl: cl.dnssec.add("example.com", "1 13 2 AB"), "POST", "/api/v1/domains/dns/dnssec"),
            ("dnssec.remove", lambda cl: cl.dnssec.remove("example.com", "1 13 2 AB"), "DELETE",
             "/api/v1/domains/dns/dnssec"),
            ("dnssec.disable", lambda cl: cl.dnssec.disable("example.com"), "POST",
             "/api/v1/domains/dns/dnssec/disable"),
            ("ssl.generate_csr", lambda cl: cl.ssl.generate_csr("example.com", country="TR", state="I", locality="I",
                                                                organization="O", organization_unit="U"),
             "POST", "/api/v1/ssls/generate-csr"),
            ("ssl.check_csr", lambda cl: cl.ssl.check_csr("csr"), "POST", "/api/v1/ssls/check-csr"),
            ("ssl.initialize", lambda cl: cl.ssl.initialize("example.com", "PositiveSSL"), "POST",
             "/api/v1/ssls/initialize"),
            ("ssl.renew", lambda cl: cl.ssl.renew(CERT_ID), "POST", "/api/v1/ssls/renew"),
            ("ssl.configure", lambda cl: cl.ssl.configure(CERT_ID, csr="csr", contact=sample_ssl_contact()),
             "PUT", "/api/v1/ssls/configure"),
            ("ssl.status", lambda cl: cl.ssl.status(CERT_ID), "PUT", "/api/v1/ssls/check-status"),
            ("ssl.get", lambda cl: cl.ssl.get(CERT_ID), "GET", "/api/v1/ssls/certificate"),
            ("ssl.content", lambda cl: cl.ssl.content(CERT_ID), "GET", "/api/v1/ssls/certificate-content"),
            ("ssl.list", lambda cl: cl.ssl.list(), "GET", "/api/v1/ssls"),
            ("ssl.reissue", lambda cl: cl.ssl.reissue(CERT_ID), "POST", "/api/v1/ssls/reissue"),
            ("ssl.approvers", lambda cl: cl.ssl.approvers(certificate_id=CERT_ID), "GET", "/api/v1/ssls/approvers"),
            ("ssl.revoke", lambda cl: cl.ssl.revoke(CERT_ID), "DELETE", "/api/v1/ssls/revoke"),
            ("hosting.packages", lambda cl: cl.hosting.packages(), "GET", "/api/v1/hostings/packages"),
            ("hosting.plans", lambda cl: cl.hosting.plans(), "GET", "/api/v1/hostings/plans"),
            ("hosting.create", lambda cl: cl.hosting.create("example.com", "Linux-Starter"), "POST",
             "/api/v1/hostings/create"),
            ("hosting.get", lambda cl: cl.hosting.get(service_id="HST-1"), "GET", "/api/v1/hostings"),
            ("hosting.get_by_token", lambda cl: cl.hosting.get_by_token("tok"), "GET", "/api/v1/hostings/by-token"),
            ("hosting.status", lambda cl: cl.hosting.status(service_id="HST-1"), "GET",
             "/api/v1/hostings/check-status"),
            ("orders.get", lambda cl: cl.orders.get("ORD-1"), "GET", "/api/v1/order/ORD-1"),
            ("products.list", lambda cl: cl.products.list(), "GET", "/api/v1/products"),
            ("products.info", lambda cl: cl.products.info("com", dna.OrderType.REGISTER, 1), "GET",
             "/api/v1/products/info"),
            ("products.tlds", lambda cl: cl.products.tlds(), "GET", "/api/v1/products/tlds"),
            ("products.ssls", lambda cl: cl.products.ssls(), "GET", "/api/v1/products/ssls"),
        ]
        answer = {"success": True, "isSuccess": True, "contactUpdateSuccess": True, "handle": "DNA-1",
                  "status": "Active"}
        for name, call, method, path in cases:
            with self.subTest(name):
                transport, client = fake(ok(answer))
                try:
                    call(client)
                except dna.DomainNameAPIError as err:  # answers that do not fit the operation are fine here
                    if isinstance(err, (dna.InputError, dna.ReadOnlyError)):
                        raise
                self.assertEqual((transport.last.method, transport.last.path), (method, path))
