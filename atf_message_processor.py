from json import JSONDecodeError
from uuid import uuid4
from atf_message_builder import MessageBundleCreator, MessageHeaderCreator, OperationOutcomeBundleCreator
from communication_mock import Communicator
from fhir.resources.bundle import Bundle
from fhir.resources.operationoutcome import OperationOutcome, OperationOutcomeIssue
from fhir.resources.extension import Extension
from fhir.resources.meta import Meta
from fhir.resources.messageheader import MessageHeader, MessageHeaderDestination, MessageHeaderSource
from fhir.resources.bundle import BundleEntry
from fhir.resources.communication import Communication, CommunicationPayload
from fhir.resources.fhirtypes import ReferenceType, CodeableConceptType
from fhir.resources.attachment import Attachment


class CommunicationCreator:
    @staticmethod
    def create(id: str, status: str, priority: str, subject_display: str, sender_display: str,
               content_attachment_title: str, content_attachment_content_type: str,
               content_attachment_data: str, sent: str, received: str) -> Communication:
        communication = Communication(
            id=id,
            status=status,
            priority=priority,
            subject=ReferenceType(display=subject_display),
            sender=ReferenceType(display=sender_display),
            payload=[
                CommunicationPayload(
                    contentAttachment=Attachment(
                        title=content_attachment_title,
                        contentType=content_attachment_content_type,
                        data=content_attachment_data
                    )
                )
            ],
            sent=sent,
            received=received
        )
        category_coding = CodeableConceptType(
            system="http://loinc.org",
            code="45012-6",
            display="Communication regarding test results"
        )
        communication.category = [
            CodeableConceptType(coding=[category_coding])]
        return communication


class ATF_MessageProcessor:
    def __init__(self, sender: ReferenceType, source: MessageHeaderSource):
        self.sender = sender
        self.communicator = Communicator()
        self.source = source
        self.messageBundleCreator = MessageBundleCreator()
        self.operationOutcomeBundleCreator = OperationOutcomeBundleCreator()
        self.messageHeaderCreator = MessageHeaderCreator()

    def send(self, receiver: ReferenceType, operation_outcome: OperationOutcome):
        print("Sende OperationOutcome")

        # TODO: Which endpointUrl should be used?
        destination = [MessageHeaderDestination(endpointUrl="unknown",
                                                receiver=receiver)]

        op_bundle = self.operationOutcomeBundleCreator.create_operation_outcome_bundle(
            self.sender, self.source, destination, operation_outcome)

        self.communicator.send(
            self.sender['display'], receiver.identifier.value, "operationOutcome.json", op_bundle.json(indent=4))

    def resolve_reference(self, reference_str: str, bundle: Bundle):
        for entry in bundle.entry:
            if entry.resource.id == reference_str.split('urn:uuid:')[-1]:
                return entry.resource
        return None

    def analyseOperationOutcome(self, operationOutcome: OperationOutcome):
        print("Analyse OperationOutcome")
        print(operationOutcome.json(indent=4))

    def create_operation_outcome_ressource(self, message_id: str, issues: list[OperationOutcomeIssue]) -> OperationOutcome:
        operation_outcome = OperationOutcome(
            id=str(uuid4()),
            meta=Meta.construct(
                profile=["https://gematik.de/fhir/atf/StructureDefinition/atf-operation-outcome"]),
            extension=[
                Extension(
                    url="https://gematik.de/fhir/atf/StructureDefinition/atf-message-id-ex",
                    valueString=message_id
                )
            ],
            issue=issues
        )
        return operation_outcome

    def handle_empfangsbestaetigung(self, message_header, parsed_bundle):
        operationOutcome = next((entry.resource for entry in parsed_bundle.entry if isinstance(
            entry.resource, OperationOutcome)), None)
        if operationOutcome is None:
            print("Die empfangene Nachricht enthält keine OperationOutcome-Ressource.")
            return
        else:
            print("Die empfangene Nachricht enthält eine OperationOutcome-Ressource.")
            self.analyseOperationOutcome(operationOutcome)

    def handle_selbsttest_lieferung(self, message_header, parsed_bundle):
        focus = message_header.focus
        if not any([isinstance(self.resolve_reference(focus_ref.reference, parsed_bundle), Communication) for focus_ref in focus]):
            issues = [
                OperationOutcomeIssue(
                    severity="fatal",
                    code="invalid",
                    diagnostics="Eine Communication-Ressource wurde im MessageHeader.focus nicht gefunden"
                )
            ]
            self.send(message_header.sender, self.create_operation_outcome_ressource(
                message_id=message_header.id,
                issues=issues
            ))
        else:
            issues = [
                OperationOutcomeIssue(
                    severity="information",
                    code="informational",
                    diagnostics="Anfrage erfolgreich entgegengenommen"
                )
            ]
            self.send(message_header.sender, self.create_operation_outcome_ressource(
                message_id=message_header.id,
                issues=issues
            ))

    def process_bundle(self, bundle: str) -> OperationOutcome:
        print("Processing Bundle")
        try:
            parsed_bundle = Bundle.parse_raw(bundle)
        except JSONDecodeError:
            print("Die empfangene Nachricht ist keine gültige FHIR-Nachricht.")
            return

        bundle_codesystem = parsed_bundle.meta.profile[0]
        if bundle_codesystem != "https://gematik.de/fhir/atf/StructureDefinition/bundle-app-transport-framework":
            print("Die empfangene Nachricht ist keine gültige ATF-Nachricht.")
            return

        message_header = next((entry.resource for entry in parsed_bundle.entry if isinstance(
            entry.resource, MessageHeader)), None)

        if message_header is None:
            print(
                "Die empfangene Nachricht ist keine gültige ATF-Nachricht. Ein MessageHeader fehlt.")
            return

        event_coding = message_header.eventCoding
        if event_coding.system == "https://gematik.de/fhir/atf/CodeSystem/operation-identifier-cs":
            if event_coding.code == "atf;Empfangsbestaetigung":
                self.handle_empfangsbestaetigung(message_header, parsed_bundle)
            else:
                print(
                    "Die empfangene Nachricht kann nicht verarbeitet werden. Der 'operation-identifier-cs' ist nicht bekannt.")
                return
        elif event_coding.system == "https://gematik.de/fhir/atf/CodeSystem/service-identifier-cs":
            if event_coding.code == "Selbsttest;Lieferung":
                self.handle_selbsttest_lieferung(message_header, parsed_bundle)
            else:
                issues = [
                    OperationOutcomeIssue(
                        severity="error",
                        code="processing",
                        diagnostics=f"Die empfangene Nachricht mit dem {event_coding.code} kann nicht verarbeitet werden, da der Use-Case nicht unterstützt wird"
                    )
                ]
                self.send(self.create_operation_outcome_ressource(
                    message_id=message_header.id,
                    issues=issues
                ))

    def create_test_bundle(self, message_id: str, receiver: ReferenceType):
        communication_id = str(uuid4())

        source = MessageHeaderSource(
            endpointUrl="https://sender.example.com/endpoint",
        )
        message_receiver = receiver
        destination = [MessageHeaderDestination(endpointUrl="https://receiver.example.com/endpoint",
                                                receiver=message_receiver)]

        message_header = self.messageHeaderCreator.create_message_header(
            message_id,
            self.sender,
            source,
            destination,
            code_system="https://gematik.de/fhir/atf/CodeSystem/service-identifier-cs",
            use_case="Selbsttest;Lieferung",
            use_case_display="Diese Dienstkennung dient ausschließlich der Einrichtung des Kontos innerhalb eines PVS und des Testes, ob Nachrichten versendet und empfangen werden können. Diese Dienstkennung wird im PVS bei der normalen Abholung von Nachrichten ignoriert.",
            focus_reference=communication_id)

        communication = CommunicationCreator.create(
            id=communication_id,
            status="completed",
            priority="routine",
            subject_display="Max Mustermann",
            sender_display="Dr. Anna Schmidt",
            content_attachment_title="Selbsttest Bestätigung",
            content_attachment_content_type="text/plain",
            content_attachment_data="U2VsYnN0dGVzdCBhYnNjaGxpZXNzZW4uIEJpdHRlIGtsYXJlbiBTaWUgZGllIFRlc3RlcmdlYm5pc3NlIGFiLg==",
            sent="2023-03-29T13:28:17.239+02:00",
            received="2023-03-29T13:30:00.000+02:00"
        )

        resources = [
            BundleEntry(
                fullUrl=f"urn:uuid:{communication_id}",
                resource=communication
            )
        ]

        bundle = self.messageBundleCreator.create_message_bundle(
            message_header=message_header,
            resources=resources
        )

        return bundle
