
from uuid import uuid4
from atf_message_library.atf_message_processor.atf_bundle_processor import ATF_BundleProcessor
from atf_message_library.atf_message_processor.models.message_to_send import MessageToSend
from atf_message_library.atf_message_processor.ressource_creators.test_message_creator import CommunicationCreator, TestMessageCreator


from fhir.resources.fhirtypes import ReferenceType
from fhir.resources.identifier import Identifier
from fhir.resources.messageheader import MessageHeaderSource

from example_helper.communication_mock import Communicator

sender_address = "sender@gematik.kim.de"
sender = ReferenceType(
    identifier=Identifier(
        system="http://gematik.de/fhir/sid/KIM-Adresse",
        value=sender_address
    ),
    display="Sender"
)
sender_source = MessageHeaderSource(
    endpointUrl="https://sender.example.com/endpoint",
)

receiver_address = "receiver@gematik.kim.de"
receiver = ReferenceType(
    identifier=Identifier(
        system="http://gematik.de/fhir/sid/KIM-Adresse",
        value=receiver_address,
    ),
    display="Receiver"
)
receiver_source = MessageHeaderSource(
    endpointUrl="https://receiver.example.com/endpoint",
)

communicator = Communicator()
sender_processor = ATF_BundleProcessor(sender, sender_source)
receiver_processor = ATF_BundleProcessor(receiver, receiver_source)


def on_message_from_receiver_to_sender(message_to_send: MessageToSend):
    communicator.send(message_to_send.receiver,
                      message_to_send.message_type, message_to_send.operation_outcome_bundle.json(indent=4))
    sender_processor.process_bundle(message_to_send.operation_outcome_bundle)


def on_message_from_sender_to_receiver(message_to_send: MessageToSend):
    communicator.send(message_to_send.receiver,
                      message_to_send.message_type, message_to_send.operation_outcome_bundle.json(indent=4))
    receiver_processor.process_bundle(message_to_send.operation_outcome_bundle)


sender_processor.message_to_send_event.subscribe(
    on_message_from_sender_to_receiver)
receiver_processor.message_to_send_event.subscribe(
    on_message_from_receiver_to_sender)

# Testnachricht erstellen
message_id = str(uuid4())


testbundle = TestMessageCreator.create_test_bundle(
    sender, receiver, message_id)

# Testnachricht "senden"
communicator.send(receiver_address,
                  "Selbsttest;Lieferung", testbundle.json(indent=4))

# Testnachricht (beim Empfänger) verarbeiten
receiver_processor.process_bundle(testbundle)
