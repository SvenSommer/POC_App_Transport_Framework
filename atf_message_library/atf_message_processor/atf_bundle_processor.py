from json import JSONDecodeError
from fhir.resources.bundle import Bundle
from fhir.resources.messageheader import MessageHeader, MessageHeaderSource, MessageHeaderDestination
from fhir.resources.fhirtypes import ReferenceType
from fhir.resources.bundle import BundleEntry
from fhir.resources.operationoutcome import OperationOutcomeIssue
from atf_message_library.atf_message_processor.base_use_case_handler import BaseUseCaseHandler
from atf_message_library.atf_message_processor.models.event import Event
from atf_message_library.atf_message_processor.models.message_to_send import MessageToSend
from atf_message_library.atf_message_processor.ressource_creators.operation_outcome_creator import OperationOutcomeCreator
from atf_message_library.atf_message_processor.ressource_creators.operation_outcome_bundle_creator import OperationOutcomeBundleCreator
from atf_message_library.atf_message_processor.use_cases.empfangsbestaetigung_handler import EmpfangsbestaetigungHandler
from atf_message_library.atf_message_processor.use_cases.selbsttest_lieferung_handler import SelbsttestLieferungHandler


class ATF_BundleProcessor:
    def __init__(self, sender: ReferenceType, source: MessageHeaderSource):
        self.sender = sender
        self.source = source
        self.use_case_handlers = {}
        self.message_to_send_event = Event()

        # Register standard use case handlers
        self.register_use_case_handler(
            "https://gematik.de/fhir/atf/CodeSystem/operation-identifier-cs",
            "atf;Empfangsbestaetigung",
            EmpfangsbestaetigungHandler(self.sender, self.source)
        )

        self.register_use_case_handler(
            "https://gematik.de/fhir/atf/CodeSystem/service-identifier-cs",
            "Selbsttest;Lieferung",
            SelbsttestLieferungHandler(self.sender, self.source)
        )

    def register_use_case_handler(self, system: str, code: str, handler: BaseUseCaseHandler):
        self.use_case_handlers[(system, code)] = handler

    def process_bundle(self, bundle: Bundle) -> list[BundleEntry]:
        try:
            parsed_bundle = Bundle.parse_raw(bundle.json())
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
        handler_key = (event_coding.system, event_coding.code)
        if handler_key in self.use_case_handlers:
            handler = self.use_case_handlers[handler_key]
            ressources, issues = handler.handle(message_header, parsed_bundle)
            if issues:
                self.sendEmpfangsbestätigung(message_header, issues)

            return ressources

        else:
            issues = [
                OperationOutcomeIssue(
                    severity="error",
                    code="processing",
                    diagnostics=f"Die empfangene Nachricht mit dem {event_coding.code} kann nicht verarbeitet werden, da der Use-Case nicht unterstützt wird."
                )
            ]
            self.sendEmpfangsbestätigung(message_header, issues)
            return

    def sendEmpfangsbestätigung(self, message_header, issues):
        operation_outcome = OperationOutcomeCreator.create_operation_outcome_ressource(
            message_id=message_header.id,
            issues=issues)

        message_to_send = self.create_MessageToSend(
            message_header, operation_outcome)

        self.message_to_send_event.trigger(message_to_send)

    def create_MessageToSend(self, message_header, operation_outcome):
        destination = [MessageHeaderDestination(endpointUrl=message_header.source.endpointUrl,
                                                receiver=message_header.sender)]

        operationOutcomeBundle = OperationOutcomeBundleCreator.create_operation_outcome_receipt_bundle(
            self.sender, self.source, destination, operation_outcome)
        message_to_send = MessageToSend(
            operation_outcome_bundle=operationOutcomeBundle,
            receiver=message_header.sender.identifier.value,
            message_type="atf;Empfangsbestaetigung"
        )

        return message_to_send
