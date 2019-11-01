"""Message type identifiers for Connections."""

MESSAGE_FAMILY = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/federatedlearningmessage/1.0"

FEDERATEDLEARNING_MESSAGE = f"{MESSAGE_FAMILY}/federatedlearningmessage"

MESSAGE_TYPES = {
    FEDERATEDLEARNING_MESSAGE: "aries_cloudagent.messaging.federatedlearningmessage."
                               + "messages.federatedlearningmessage.FederatedLearningMessage"
}
