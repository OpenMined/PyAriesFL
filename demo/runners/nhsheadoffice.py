import asyncio
import json
import logging
import os
import random
import sys

from uuid import uuid4
from datetime import date

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


class NhsheadofficeAgent(DemoAgent):
    def __init__(self, http_port: int, admin_port: int, **kwargs):
        super().__init__(
            "NHS Trust",
            http_port,
            admin_port,
            seed="m88EdTmOnwVgDr08qK1zDLI0IzOyQuE5",
            prefix="Nhs Trust",
            extra_args=["--auto-accept-invites", "--auto-accept-requests"],
            **kwargs,
        )
        self.current_hospital_name = None
        self.active_connection_id = None
        self.connection_list = []
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
        if message["connection_id"] == self.active_connection_id:
            if message["state"] == "active" and not self._connection_ready.done():
                self.log("Connected")
                self._connection_ready.set_result(True)

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
                # self.log(presentation_request["requested_attributes"])
                self.log(proof)

                # self.log(proof["presentation"]["proof"]["requested_proof"])
                self.log(proof["presentation"]["requested_proof"]["self_attested_attrs"]["0_name_uuid"])

                self.current_hospital_name = proof["presentation"]["requested_proof"]["self_attested_attrs"]["0_name_uuid"]
    #
    # async def handle_basicmessages(self, message):
    #     self.log("Received message:", message["content"])


async def main(start_port: int, show_timing: bool = False):

    genesis = await default_genesis_txns()
    if not genesis:
        print("Error retrieving ledger genesis transactions")
        sys.exit(1)

    agent = None

    try:
        log_status("#1 Provision an agent and wallet, get back configuration details")
        agent = NhsheadofficeAgent(
            start_port, start_port + 1, genesis_data=genesis, timing=show_timing
        )
        await agent.listen_webhooks(start_port + 2)
        await agent.register_did()

        log_msg("HEAD OFFICE DID: ", agent.did)

        with log_timer("Startup duration:"):
            await agent.start_process()
        log_msg("Admin url is at:", agent.admin_url)
        log_msg("Endpoint url is at:", agent.endpoint)

        # Create a schema
        with log_timer("Publish schema/cred def duration:"):
            log_status("#3/4 Create a new schema/cred def on the ledger")
            version = format(
                "%d.%d.%d"
                % (
                    random.randint(1, 101),
                    random.randint(1, 101),
                    random.randint(1, 101),
                )
            )
            (
                _,  # schema id
                credential_definition_id,
            ) = await agent.register_schema_and_creddef(
                "Verified Hospital schema", version, ["date", "hospital_name"]
            )

        # TODO add an additional credential for Student ID

        with log_timer("Generate invitation duration:"):
            # Generate an invitation
            log_status(
                "#5 Create a connection to Hospital and print out the invite details"
            )
            connection = await agent.admin_POST("/connections/create-invitation")

        agent.active_connection_id = connection["connection_id"]
        agent.connection_list.append(connection["connection_id"])
        log_json(connection, label="Invitation response:")
        log_msg("*****************")
        log_msg(json.dumps(connection["invitation"]), label="Invitation:", color=None)
        log_msg("*****************")

        log_msg("Waiting for connection...")
        await agent.detect_connection()

        async for option in prompt_loop(
            "(1) Request Hospital name, (2) Issue Verified Hospital Credential, (3) Create a New Invitation, (X) Exit? [1/2/X] "
        ):
            if option is None or option in "xX":
                break

            elif option == "1":
                log_status("#20 Request Self Attested Hospital Name")
                req_attrs = [
                    {"name": "name"}
                ]
                indy_proof_request = {
                    "name": "Proof of Hospital Name",
                    "version": "1.0",
                    "nonce": str(uuid4().int),
                    "requested_attributes": {
                        f"0_{req_attr['name']}_uuid": req_attr for req_attr in req_attrs
                    },
                    "requested_predicates": {
                    },
                }
                proof_request_web_request = {
                    "connection_id": agent.active_connection_id,
                    "proof_request": indy_proof_request,
                }
                await agent.admin_POST(
                    "/present-proof/send-request", proof_request_web_request
                )


            elif option == "2":
                log_status("#13 Issue Verified Hospital credential offer to X")

                today = date.today()
                # TODO define attributes to send for credential
                agent.cred_attrs[credential_definition_id] = {
                    "hospital_name": agent.current_hospital_name,
                    "date": str(today),
                    # "degree": "Health",
                    # "age": "24",
                }

                cred_preview = {
                    "@type": CRED_PREVIEW_TYPE,
                    "attributes": [
                        {"name": n, "value": v}
                        for (n, v) in agent.cred_attrs[credential_definition_id].items()
                    ],
                }
                offer_request = {
                    "connection_id": agent.active_connection_id,
                    "credential_definition_id": credential_definition_id,
                    "comment": f"Offer on cred def id {credential_definition_id}",
                    "credential_preview": cred_preview,
                }
                await agent.admin_POST("/issue-credential/send-offer", offer_request)

            # elif option == "3":
            #     msg = await prompt("Enter message: ")
            #     await agent.admin_POST(
            #         f"/connections/{agent.active_connection_id}/send-message", {"content": msg}
            #     )
            elif option == "3":
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
                agent._connection_ready = asyncio.Future()
                log_msg("Waiting for connection...")
                await agent.detect_connection()

        if show_timing:
            timing = await agent.fetch_timing()
            if timing:
                for line in agent.format_timing(timing):
                    log_msg(line)

    finally:
        terminated = True
        try:
            if agent:
                await agent.terminate()
        except Exception:
            LOGGER.exception("Error terminating agent:")
            terminated = False

    await asyncio.sleep(0.1)

    if not terminated:
        os._exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Runs a NHS Head Office demo agent.")
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8060,
        metavar=("<port>"),
        help="Choose the starting port number to listen on",
    )
    parser.add_argument(
        "--timing", action="store_true", help="Enable timing information"
    )
    args = parser.parse_args()

    require_indy()

    try:
        asyncio.get_event_loop().run_until_complete(main(args.port, args.timing))
    except KeyboardInterrupt:
        os._exit(1)
