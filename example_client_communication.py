from uuid import uuid4
from atf_message_processor import ATF_MessageProcessor
from fhir.resources.fhirtypes import ReferenceType
from fhir.resources.identifier import Identifier
from communication_mock import Communicator
from fhir.resources.messageheader import MessageHeaderSource


if __name__ == '__main__':
    commuicator = Communicator()
    sender = ReferenceType(
        identifier=Identifier(
            system="http://gematik.de/fhir/sid/KIM-Adresse",
            value="sender@gematik.kim.de"
        ),
        display="Sender"
    )
    source = MessageHeaderSource(
        endpointUrl="https://sender.example.com/endpoint",
    )

    receiver = ReferenceType(
        identifier=Identifier(
            system="http://gematik.de/fhir/sid/KIM-Adresse",
            value="Receiver@example.com",
        ),
        display="Receiver"
    )

    client_sender = ATF_MessageProcessor(sender,
                                         MessageHeaderSource(endpointUrl="https://receiver.example.com/endpoint"))
    message_id = str(uuid4())
    testbundle = client_sender.create_test_bundle(
        message_id, receiver=receiver)
    commuicator.send(sender['display'], receiver['display'],
                     "testbundle.json", testbundle.json(indent=4))

    client_receiver = ATF_MessageProcessor(receiver, source)
    client_receiver.process_bundle(testbundle.json())
