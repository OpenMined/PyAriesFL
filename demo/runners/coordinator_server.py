from quart import Quart
import os
import argparse
import sys
import asyncio
import json
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa

from runners.coordinator_web import CoordinatorAgent
from runners.support.agent import default_genesis_txns
from runners.support.utils import (
    log_json,
    log_msg,
    log_status,
    log_timer,
    prompt,
    prompt_loop,
    require_indy,
)

LOGGER = logging.getLogger(__name__)


def create_app(test_config=None):
    # create and configure the app
    app = Quart(__name__)

    parser = argparse.ArgumentParser(description="Runs a Coordinator demo agent.")
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8020,
        metavar=("<port>"),
        help="Choose the starting port number to listen on",
    )
    parser.add_argument(
        "--timing", action="store_true", help="Enable timing information"
    )
    args = parser.parse_args()

    require_indy()
    agent = None

    try:
        agent = asyncio.get_event_loop().run_until_complete(create_agent(args.port, args.timing))
    except KeyboardInterrupt:
        os._exit(1)

    log_msg("Agent created", agent.active_connection_id)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    @app.route('/connect')
    async def connect():
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

        return json.dumps(connection["invitation"])

    @app.route('/trustedconnections')
    def connections():
        # Generate an invitation
        log_msg(agent.connection_list)
        return json.dumps(agent.trusted_connection_ids)

    return app


async def create_agent(start_port: int, show_timing: bool = False):

    genesis = await default_genesis_txns()
    if not genesis:
        print("Error retrieving ledger genesis transactions")
        sys.exit(1)

    agent = None

    try:
        log_status("#1 Provision an agent and wallet, get back configuration details")
        agent = CoordinatorAgent(
            start_port, start_port + 1, genesis_data=genesis, timing=show_timing
        )
        await agent.listen_webhooks(start_port + 2)

        with log_timer("Startup duration:"):
            await agent.start_process()
        log_msg("Admin url is at:", agent.admin_url)
        log_msg("Endpoint url is at:", agent.endpoint)

        return agent

    # log_msg("Waiting for connection...")
    # await agent.detect_connection()

    #     async for option in prompt_loop(
    #         "(1) Send Proof Request, "
    #         + "(2) Send Message (3) New Connection (4) Input New Invitation Details (X) Exit? [1/2/3/4/X] "
    #     ):
    #         if option is None or option in "xX":
    #             break
    #
    #         elif option == "1":
    #             log_status("#20 Request proof of degree from alice")
    #             req_attrs = [
    #                 {"name": "date", "restrictions": [{"issuer_did": agent.nhsheadoffice_did}]},
    #             ]
    #             # req_preds = [
    #             #     {
    #             #         "name": "age",
    #             #         "p_type": ">=",
    #             #         "p_value": 18,
    #             #         "restrictions": [{"issuer_did": agent.did}],
    #             #     }
    #             # ]
    #             indy_proof_request = {
    #                 "name": "Proof of Verified Hospital",
    #                 "version": "1.0",
    #                 "nonce": str(uuid4().int),
    #                 "requested_attributes": {
    #                     f"0_{req_attr['name']}_uuid": req_attr for req_attr in req_attrs
    #                 },
    #                 "requested_predicates": {
    #                 },
    #             }
    #             print("Asking for this proof: ", indy_proof_request)
    #             proof_request_web_request = {
    #                 "connection_id": agent.active_connection_id,
    #                 "proof_request": indy_proof_request,
    #             }
    #             await agent.admin_POST(
    #                 "/present-proof/send-request", proof_request_web_request
    #             )
    #
    #         elif option == "2":
    #             msg = await prompt("Enter message: ")
    #             await agent.admin_POST(
    #                 f"/connections/{agent.active_connection_id}/send-message", {"content": msg}
    #             )
    #         elif option == "3":
    #             # handle new invitation
    #             with log_timer("Generate invitation duration:"):
    #                 # Generate an invitation
    #                 log_status(
    #                     "#5 Create a connection to alice and print out the invite details"
    #                 )
    #                 connection = await agent.admin_POST("/connections/create-invitation")
    #
    #             agent.active_connection_id = connection["connection_id"]
    #             agent.connection_list.append(connection["connection_id"])
    #             log_msg("all connections :", agent.connection_list)
    #             log_json(connection, label="Invitation response:")
    #             log_msg("*****************")
    #             log_msg(json.dumps(connection["invitation"]), label="Invitation:", color=None)
    #             log_msg("*****************")
    #             agent._connection_ready = asyncio.Future()
    #
    #             log_msg("Waiting for connection...")
    #             await agent.detect_connection()
    #         elif option == "4":
    #             # handle new invitation
    #             log_status("Input new invitation details")
    #             await input_invitation(agent)
    #     if show_timing:
    #         timing = await agent.fetch_timing()
    #         if timing:
    #             for line in agent.format_timing(timing):
    #                 log_msg(line)
    #
    except Exception:
        LOGGER.exception("Error terminating agent:")
        return None

    # finally:
    #     terminated = True
    #     try:
    #         if agent:
    #             await agent.terminate()
    #     except Exception:
    #         LOGGER.exception("Error terminating agent:")
    #         terminated = False
    #
    # await asyncio.sleep(0.1)
    #
    # if not terminated:
    #     os._exit(1)

if __name__ == "__main__":

    app = create_app()
    app.run(host='0.0.0.0', port='8140')