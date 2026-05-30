import json
import unittest
from typing import Any

from agentbox import (
    AgentBoxApiError,
    AgentBoxClient,
    bootstrap_agentbox_agent,
    client_for_grant,
    create_private_box_with_resources,
    create_scoped_read_grant,
    discover_agentbox,
)
from agentbox.client import AgentBoxHttpResponse


class FakeTransport:
    def __init__(self, payload: Any = None, status: int = 200, reason: str = "OK") -> None:
        self.calls = []
        self.payload = payload if payload is not None else {"ok": True, "data": [], "error": None, "audit_id": None}
        self.status = status
        self.reason = reason

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": None if body is None else json.loads(body.decode("utf-8")),
                "timeout": timeout,
            }
        )
        return AgentBoxHttpResponse(self.status, self.reason, json.dumps(self.payload).encode("utf-8"))


class QueueTransport:
    def __init__(self, payloads: list[Any]) -> None:
        self.calls = []
        self.payloads = payloads

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": None if body is None else json.loads(body.decode("utf-8")),
                "timeout": timeout,
            }
        )
        payload = self.payloads.pop(0)
        return AgentBoxHttpResponse(200, "OK", json.dumps(payload).encode("utf-8"))


class AgentBoxClientTests(unittest.TestCase):
    def test_sends_legacy_auth_headers_and_admin_intent(self) -> None:
        transport = FakeTransport()
        client = AgentBoxClient(
            base_url="http://agentbox.example",
            actor="ops-agent",
            token="admin-token",
            transport=transport,
        )

        client.list_agents(admin=True)

        self.assertEqual(transport.calls[0]["method"], "GET")
        self.assertEqual(transport.calls[0]["url"], "http://agentbox.example/v1/agents")
        self.assertEqual(
            transport.calls[0]["headers"],
            {
                "accept": "application/json",
                "authorization": "Bearer admin-token",
                "x-agentbox-actor": "ops-agent",
                "x-agentbox-admin": "true",
            },
        )

    def test_updates_known_agent_status(self) -> None:
        transport = FakeTransport(
            {
                "ok": True,
                "data": {
                    "identity_key": 'idk_v1_Cs4xjTTHauWmSUjdhrzojsUg4SbkBVeeF9wsFaYxvJg',
                    "identity": {
                        "scheme": "oidc",
                        "issuer": "https://accounts.google.com",
                        "subject": "agent-sub",
                    },
                    "display_name": "Blocked Agent",
                    "agent_card_url": None,
                    "capabilities": [],
                    "status": "blocked",
                    "metadata": None,
                    "first_seen_at": "2026-05-21T00:00:00.000Z",
                    "last_seen_at": "2026-05-21T00:00:00.000Z",
                },
                "error": None,
                "audit_id": None,
            }
        )
        client = AgentBoxClient(
            base_url="http://agentbox.example",
            actor="ops-agent",
            token="admin-token",
            transport=transport,
        )

        client.update_agent_status(
            {
                "identity_key": 'idk_v1_Cs4xjTTHauWmSUjdhrzojsUg4SbkBVeeF9wsFaYxvJg',
                "status": "blocked",
            },
            admin=True,
        )

        self.assertEqual(transport.calls[0]["method"], "PATCH")
        self.assertEqual(
            transport.calls[0]["url"],
            "http://agentbox.example/v1/agents/idk_v1_Cs4xjTTHauWmSUjdhrzojsUg4SbkBVeeF9wsFaYxvJg/status",
        )
        self.assertEqual(transport.calls[0]["body"], {"status": "blocked"})
        self.assertEqual(transport.calls[0]["headers"]["x-agentbox-admin"], "true")

    def test_sends_oidc_identity_and_grant_tokens_separately(self) -> None:
        transport = FakeTransport()
        client = AgentBoxClient(
            base_url="http://agentbox.example",
            identity_token="oidc.jwt.token",
            grant_token="abx_grant_token",
            auth_scheme="google",
            transport=transport,
        )

        client.get_item({"box_id": "box_oidc", "key": "research/summary"})

        headers = transport.calls[0]["headers"]
        self.assertEqual(headers["authorization"], "Bearer oidc.jwt.token")
        self.assertEqual(headers["x-agentbox-auth-scheme"], "google")
        self.assertEqual(headers["x-agentbox-grant-token"], "abx_grant_token")
        self.assertNotIn("x-agentbox-actor", headers)

    def test_keeps_auth_modes_exclusive_when_deriving_clients(self) -> None:
        transport = FakeTransport()
        admin = AgentBoxClient(
            base_url="http://agentbox.example",
            actor="ops-agent",
            token="admin-token",
            transport=transport,
        )

        oidc = admin.with_auth(identity_token="oidc.jwt.token")
        oidc.list_boxes()

        first_headers = transport.calls[0]["headers"]
        self.assertEqual(first_headers["authorization"], "Bearer oidc.jwt.token")
        self.assertNotIn("x-agentbox-grant-token", first_headers)
        self.assertNotIn("x-agentbox-actor", first_headers)

        legacy = oidc.with_auth(actor="writer-agent", token="writer-token")
        legacy.list_boxes()

        second_headers = transport.calls[1]["headers"]
        self.assertEqual(second_headers["authorization"], "Bearer writer-token")
        self.assertEqual(second_headers["x-agentbox-actor"], "writer-agent")
        self.assertNotIn("x-agentbox-grant-token", second_headers)

    def test_inherits_actor_when_refreshing_token_auth(self) -> None:
        transport = FakeTransport()
        client = AgentBoxClient(
            base_url="http://agentbox.example",
            actor="ops-agent",
            token="old-token",
            transport=transport,
        )

        refreshed = client.with_auth(token="new-token")
        refreshed.list_boxes()

        headers = transport.calls[0]["headers"]
        self.assertEqual(headers["authorization"], "Bearer new-token")
        self.assertEqual(headers["x-agentbox-actor"], "ops-agent")

    def test_rejects_invalid_auth_modes(self) -> None:
        with self.assertRaises(TypeError):
            AgentBoxClient(base_url="http://agentbox.example", actor="ops-agent", token="a", identity_token="b")
        with self.assertRaises(TypeError):
            AgentBoxClient(base_url="http://agentbox.example", token="token")

        client = AgentBoxClient(base_url="http://agentbox.example", actor="ops-agent", token="token")
        with self.assertRaises(TypeError):
            client.with_auth(token="a", identity_token="b")
        with self.assertRaises(TypeError):
            client.with_auth(identity_token="oidc.jwt.token").with_auth(token="writer-token")

    def test_encodes_paths_queries_and_request_bodies(self) -> None:
        transport = FakeTransport({"ok": True, "data": {"key": "research/a b"}, "error": None, "audit_id": None})
        client = AgentBoxClient(
            base_url="http://agentbox.example/api",
            actor="research-agent",
            token="admin-token",
            transport=transport,
        )

        client.put_item(
            {
                "box_id": "box one",
                "key": "research/a b",
                "value": "Readable",
                "expected_version": 0,
            }
        )
        client.list_items({"box_id": "box one", "prefix": "research/", "tags": ["alpha", "beta"]})

        self.assertEqual(transport.calls[0]["url"], "http://agentbox.example/api/v1/boxes/box%20one/items/research/a%20b")
        self.assertEqual(transport.calls[0]["body"], {"value": "Readable", "expected_version": 0})
        self.assertEqual(
            transport.calls[1]["url"],
            "http://agentbox.example/api/v1/boxes/box%20one/items?prefix=research%2F&tags=alpha%2Cbeta",
        )

    def test_raises_structured_api_errors(self) -> None:
        transport = FakeTransport(
            {
                "ok": False,
                "data": None,
                "error": {
                    "code": "invalid_input",
                    "message": "Name is required.",
                    "target": "name",
                    "request_id": "req_test",
                },
                "audit_id": "aud_test",
            },
            status=400,
            reason="Bad Request",
        )
        client = AgentBoxClient(base_url="http://agentbox.example", actor="ops-agent", token="admin-token", transport=transport)

        with self.assertRaises(AgentBoxApiError) as raised:
            client.create_box({"name": ""})

        self.assertEqual(raised.exception.code, "invalid_input")
        self.assertEqual(raised.exception.status, 400)
        self.assertEqual(raised.exception.target, "name")
        self.assertEqual(raised.exception.request_id, "req_test")
        self.assertEqual(raised.exception.audit_id, "aud_test")

    def test_health_is_public(self) -> None:
        transport = FakeTransport({"ok": True, "data": {"status": "ok"}, "error": None, "audit_id": None})
        client = AgentBoxClient(base_url="http://agentbox.example", actor="ops-agent", token="admin-token", transport=transport)

        result = client.health()

        self.assertEqual(result["data"]["status"], "ok")
        self.assertNotIn("authorization", transport.calls[0]["headers"])

    def test_discovers_agentbox_from_agent_card_and_creates_clients(self) -> None:
        transport = FakeTransport(
            {
                "protocolVersion": "0.3.0",
                "name": "AgentBox",
                "description": "Identity-bound shared workspace boxes.",
                "url": "https://agentbox.example/a2a",
                "securitySchemes": {
                    "google": {
                        "type": "openIdConnect",
                    }
                },
                "skills": [
                    {
                        "id": "agentbox.workspace",
                    }
                ],
            }
        )

        discovery = discover_agentbox(base_url="https://agentbox.example", transport=transport)

        self.assertEqual(transport.calls[0]["method"], "GET")
        self.assertEqual(transport.calls[0]["url"], "https://agentbox.example/.well-known/agent-card.json")
        self.assertEqual(discovery.base_url, "https://agentbox.example")
        self.assertEqual(discovery.a2a_url, "https://agentbox.example/a2a")
        self.assertEqual(discovery.rest_api_base_url, "https://agentbox.example/v1")
        self.assertEqual(discovery.security_schemes["google"]["type"], "openIdConnect")

        transport.payload = {"ok": True, "data": {"status": "ok"}, "error": None, "audit_id": None}
        client = discovery.create_client(actor="research-agent", token="admin-token", auth_scheme="agentboxAdmin")
        client.list_boxes()

        self.assertEqual(transport.calls[1]["url"], "https://agentbox.example/v1/boxes")
        self.assertEqual(transport.calls[1]["headers"]["x-agentbox-auth-scheme"], "agentboxAdmin")

    def test_bootstrap_workflow_discovers_and_registers_agent(self) -> None:
        transport = QueueTransport(
            [
                {
                    "protocolVersion": "0.3.0",
                    "name": "AgentBox",
                    "url": "https://agentbox.example/a2a",
                },
                {
                    "ok": True,
                    "data": {
                        "identity_key": "idk_v1_test",
                        "identity": {"scheme": "dev", "subject": "research-agent"},
                        "display_name": "Research Agent",
                        "agent_card_url": None,
                        "capabilities": ["research"],
                        "status": "active",
                        "metadata": None,
                        "first_seen_at": "2026-05-25T00:00:00.000Z",
                        "last_seen_at": "2026-05-25T00:00:00.000Z",
                    },
                    "error": None,
                    "audit_id": "aud_test",
                },
            ]
        )

        session = bootstrap_agentbox_agent(
            base_url="https://agentbox.example",
            client={"actor": "research-agent", "token": "admin-token", "auth_scheme": "agentboxAdmin"},
            registration={"display_name": "Research Agent", "capabilities": ["research"]},
            transport=transport,
        )

        self.assertEqual(session.discovery.base_url, "https://agentbox.example")
        self.assertEqual(session.agent["display_name"], "Research Agent")
        self.assertEqual(transport.calls[1]["url"], "https://agentbox.example/v1/agents/register")
        self.assertEqual(transport.calls[1]["headers"]["x-agentbox-auth-scheme"], "agentboxAdmin")

    def test_private_box_and_grant_workflow_helpers(self) -> None:
        transport = QueueTransport(
            [
                {
                    "ok": True,
                    "data": {
                        "box": {
                            "box_id": "box_test",
                            "name": "Workflow box",
                            "status": "open",
                            "created_by": "research-agent",
                            "owner_identity": {"scheme": "dev", "subject": "research-agent"},
                            "created_at": "2026-05-25T00:00:00.000Z",
                            "updated_at": "2026-05-25T00:00:00.000Z",
                            "expires_at": None,
                            "metadata": None,
                        },
                        "manifest_uri": "agentbox://boxes/box_test/manifest",
                    },
                    "error": None,
                    "audit_id": "aud_create",
                },
                {
                    "ok": True,
                    "data": {"box_id": "box_test", "key": "research/summary", "version": 1},
                    "error": None,
                    "audit_id": "aud_item",
                },
                {
                    "ok": True,
                    "data": {
                        "event_id": "evt_test",
                        "box_id": "box_test",
                        "stream": "activity",
                        "seq": 1,
                        "type": "summary_ready",
                    },
                    "error": None,
                    "audit_id": "aud_event",
                },
                {
                    "ok": True,
                    "data": {"artifact_id": "art_test", "box_id": "box_test", "name": "public-brief.md"},
                    "error": None,
                    "audit_id": "aud_artifact",
                },
                {
                    "ok": True,
                    "data": {"box_id": "box_test", "items": [{"key": "research/summary"}], "streams": [], "artifacts": []},
                    "error": None,
                    "audit_id": "aud_manifest",
                },
                {
                    "ok": True,
                    "data": {
                        "grant": {
                            "grant_id": "gr_test",
                            "box_id": "box_test",
                            "subject": "writer-agent",
                            "permissions": ["read"],
                        },
                        "access_token": "abx_grant_test",
                    },
                    "error": None,
                    "audit_id": "aud_grant",
                },
                {
                    "ok": True,
                    "data": [],
                    "error": None,
                    "audit_id": None,
                },
            ]
        )
        client = AgentBoxClient(
            base_url="https://agentbox.example",
            actor="research-agent",
            token="admin-token",
            auth_scheme="agentboxAdmin",
            transport=transport,
        )

        workspace = create_private_box_with_resources(
            client,
            {
                "name": "Workflow box",
                "items": [{"key": "research/summary", "value": "Readable", "expected_version": 0}],
                "events": [{"stream": "activity", "type": "summary_ready"}],
                "artifacts": [
                    {
                        "name": "public-brief.md",
                        "content_type": "text/markdown",
                        "content_base64": "cHVibGlj",
                    }
                ],
            },
        )
        grant = create_scoped_read_grant(
            client,
            {
                "box_id": workspace["box"]["box_id"],
                "subject": "writer-agent",
                "key_prefixes": ["research/"],
                "ttl_seconds": 60,
            },
        )
        writer = client_for_grant(client, grant)
        writer.list_boxes()

        self.assertEqual(workspace["box"]["box_id"], "box_test")
        self.assertEqual(transport.calls[1]["url"], "https://agentbox.example/v1/boxes/box_test/items/research/summary")
        self.assertEqual(transport.calls[5]["body"]["permissions"], ["read"])
        self.assertEqual(transport.calls[6]["headers"]["authorization"], "Bearer abx_grant_test")
        self.assertEqual(transport.calls[6]["headers"]["x-agentbox-auth-scheme"], "agentboxGrant")
        self.assertEqual(transport.calls[6]["headers"]["x-agentbox-actor"], "writer-agent")


if __name__ == "__main__":
    unittest.main()
