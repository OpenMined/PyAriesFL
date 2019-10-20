import asyncio
import json
import logging
import os
import random
import sys
import base64
import binascii
from urllib.parse import urlparse
from uuid import uuid4
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa

from runners.support.agent import DemoAgent, default_genesis_txns
from runners.support.utils import (
    log_json,
    log_msg,
    log_status,
    log_timer,
    prompt,
    prompt_loop,
    require_indy,
)

CRED_PREVIEW_TYPE = (
    "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/issue-credential/1.0/credential-preview"
)

LOGGER = logging.getLogger(__name__)


class CoordinatorAgent(DemoAgent):
    def __init__(self, http_port: int, admin_port: int, **kwargs):
        super().__init__(
            "Coordinator Agent",
            http_port,
            admin_port,
            seed=None,
            prefix="Coordinator",
            extra_args=["--auto-accept-invites", "--auto-accept-requests", "--auto-store-credential"],
            **kwargs,
        )
        self.nhsheadoffice_did = "DukExq9foGb5DjDoRXx8G8"
        self.active_connection_id = None
        self.connection_list = []
        self.trusted_connection_ids = []
        self.trusted_hospitals = []
        self._connection_ready = asyncio.Future()
        self.cred_state = {}
        # TODO define a dict to hold credential attributes
        # based on credential_definition_id
        self.cred_attrs = {}

    async def detect_connection(self):
        await self._connection_ready

    @property
    def connection_ready(self):
        return self._connection_ready.done() and self._connection_ready.result()

    async def handle_connections(self, message):
        # self.log("Handle connections", message, self.connections_list)
        if message["connection_id"] == self.active_connection_id:
            if message["state"] == "active" and not self._connection_ready.done():
                self.log("Connected")
                self._connection_ready.set_result(True)
                log_status("#20 Request proof of degree from alice")
                req_attrs = [
                    {"name": "date", "restrictions": [{"issuer_did": self.nhsheadoffice_did}]},
                ]
                indy_proof_request = {
                    "name": "Proof of Verified Hospital",
                    "version": "1.0",
                    "nonce": str(uuid4().int),
                    "requested_attributes": {
                        f"0_{req_attr['name']}_uuid": req_attr for req_attr in req_attrs
                    },
                    "requested_predicates": {
                    },
                }
                print("Asking for this proof: ", indy_proof_request)
                proof_request_web_request = {
                    "connection_id": self.active_connection_id,
                    "proof_request": indy_proof_request,
                }
                await self.admin_POST(
                    "/present-proof/send-request", proof_request_web_request
                )

    async def handle_issue_credential(self, message):
        state = message["state"]
        credential_exchange_id = message["credential_exchange_id"]
        prev_state = self.cred_state.get(credential_exchange_id)
        if prev_state == state:
            return  # ignore
        self.cred_state[credential_exchange_id] = state

        self.log(
            "Credential: state =",
            state,
            ", credential_exchange_id =",
            credential_exchange_id,
        )

        if state == "request_received":
            log_status("#17 Issue credential to X")
            # issue credentials based on the credential_definition_id
            cred_attrs = self.cred_attrs[message["credential_definition_id"]]
            cred_preview = {
                "@type": CRED_PREVIEW_TYPE,
                "attributes": [
                    {"name": n, "value": v} for (n, v) in cred_attrs.items()
                ],
            }
            await self.admin_POST(
                f"/issue-credential/records/{credential_exchange_id}/issue",
                {
                    "comment": f"Issuing credential, exchange {credential_exchange_id}",
                    "credential_preview": cred_preview,
                },
            )

        if state == "offer_received":
            log_status("#15 After receiving credential offer, send credential request")
            await self.admin_POST(
                "/issue-credential/records/" f"{credential_exchange_id}/send-request"
            )

        elif state == "stored":
            # elif state == "credential_received": ??
            self.log("Storing credential in wallet")
            cred_id = message["credential_id"]
            log_status(f"#18.1 Stored credential {cred_id} in wallet")
            resp = await self.admin_GET(f"/credential/{cred_id}")
            log_json(resp, label="Credential details:")
            log_json(
                message["credential_request_metadata"],
                label="Credential request metadata:",
            )
            self.log("credential_id", message["credential_id"])
            self.log("credential_definition_id", message["credential_definition_id"])
            self.log("schema_id", message["schema_id"])


    async def handle_present_proof(self, message):
        state = message["state"]
        presentation_request = message["presentation_request"]
        presentation_exchange_id = message["presentation_exchange_id"]

        self.log(
            "Presentation: state =",
            state,
            ", presentation_exchange_id =",
            presentation_exchange_id,
        )

        if state == "presentation_received":
            log_status("#27 Process the proof provided by X")
            log_status("#28 Check if proof is valid")
            proof = await self.admin_POST(
                f"/present-proof/records/{presentation_exchange_id}/"
                "verify-presentation"
            )
            self.log("Proof =", proof["verified"])
            if proof["verified"]:
                hospital = {"connection_id" : message["connection_id"]}
                self.log(hospital)
                for attribute in presentation_request['requested_attributes']:
                    self.log(attribute)
                    attribute_name = presentation_request['requested_attributes'][attribute]["name"]
                    self.log("Attribute name: ",  presentation_request['requested_attributes'][attribute]["name"])
                    # self.log(attribute.name)
                    self.log("Attribte value", proof["presentation"]["requested_proof"]["revealed_attrs"][attribute]['raw'])
                    hospital[attribute_name] = proof["presentation"]["requested_proof"]["revealed_attrs"][attribute]['raw']
                self.log(hospital)

                # self.log(proof)
                # self.log(presentation_request)
                self.trusted_connection_ids.append(message["connection_id"])
                self.trusted_hospitals.append(hospital)

        elif state == "request_received":
            log_status(
                "#24 Query for credentials in the wallet that satisfy the proof request"
            )

            # include self-attested attributes (not included in credentials)
            credentials_by_reft = {}
            revealed = {}
            self_attested = {}
            predicates = {}
            log_msg("Get Credentials to Satisfy proof")
            # select credentials to provide for the proof
            credentials = await self.admin_GET(
                f"/present-proof/records/{presentation_exchange_id}/credentials"
            )
            self.log("Got cred", credentials)

            if credentials:
                for row in credentials:
                    for referent in row["presentation_referents"]:
                        if referent not in credentials_by_reft:
                            credentials_by_reft[referent] = row

            for referent in presentation_request["requested_attributes"]:
                if referent in credentials_by_reft:
                    revealed[referent] = {
                        "cred_id": credentials_by_reft[referent]["cred_info"][
                            "referent"
                        ],
                        "revealed": True,
                    }
                else:
                    self_attested[referent] = "my self-attested value"

            for referent in presentation_request["requested_predicates"]:
                if referent in credentials_by_reft:
                    predicates[referent] = {
                        "cred_id": credentials_by_reft[referent]["cred_info"][
                            "referent"
                        ],
                        "revealed": True,
                    }

            log_status("#25 Generate the proof")
            request = {
                "requested_predicates": predicates,
                "requested_attributes": revealed,
                "self_attested_attributes": self_attested,
            }
            log_status(request)
            log_status("#26 Send the proof to X")
            await self.admin_POST(
                (
                    "/present-proof/records/"
                    f"{presentation_exchange_id}/send-presentation"
                ),
                request,
            )

    async def handle_basicmessages(self, message):
        self.log("Received message:", message["content"])
        self.log(message)


async def generate_new_connection(agent):
    # handle new invitation
    with log_timer("Generate invitation duration:"):
        # Generate an invitation
        log_status(
            "#5 Create a connection to alice and print out the invite details"
        )
        connection = await agent.admin_POST("/connections/create-invitation")

    agent.active_connection_id = connection["connection_id"]
    agent.connection_list.append(connection["connection_id"])
    log_msg("all connections :", agent.connection_list)
    log_json(connection, label="Invitation response:")
    log_msg("*****************")
    log_msg(json.dumps(connection["invitation"]), label="Invitation:", color=None)
    log_msg("*****************")

    log_msg("Waiting for connection...")
    await agent.detect_connection()



async def input_invitation(agent):
    async for details in prompt_loop("Invite details: "):
        b64_invite = None
        try:
            url = urlparse(details)
            query = url.query
            if query and "c_i=" in query:
                pos = query.index("c_i=") + 4
                b64_invite = query[pos:]
            else:
                b64_invite = details
        except ValueError:
            b64_invite = details

        if b64_invite:
            try:
                invite_json = base64.urlsafe_b64decode(b64_invite)
                details = invite_json.decode("utf-8")
            except binascii.Error:
                pass
            except UnicodeDecodeError:
                pass

        if details:
            try:
                json.loads(details)
                break
            except json.JSONDecodeError as e:
                log_msg("Invalid invitation:", str(e))

    with log_timer("Connect duration:"):
        connection = await agent.admin_POST("/connections/receive-invitation", details)
        agent.active_connection_id = connection["connection_id"]
        log_json(connection, label="Invitation response:")
        agent._connection_ready = asyncio.Future()

        await agent.detect_connection()

