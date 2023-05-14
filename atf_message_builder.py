from fhir.resources.meta import Meta
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.messageheader import MessageHeader, MessageHeaderDestination, MessageHeaderSource
from fhir.resources.fhirtypes import ReferenceType, IdentifierType
from fhir.resources.operationoutcome import OperationOutcome
from fhir.resources.coding import Coding
from uuid import uuid4
from typing import List


class MessageHeaderCreator:
    @staticmethod
    def create_message_header(
        id: str,
        message_sender: ReferenceType,
        source: MessageHeaderSource,
        destinations: List[MessageHeaderDestination],
        code_system: str,
        use_case: str,
        use_case_display: str,
        focus_reference: str,
    ) -> MessageHeader:
        message_header = MessageHeader(
            id=id,
            meta=Meta.construct(profile=[
                "https://gematik.de/fhir/atf/StructureDefinition/message-header-app-transport"
            ]),
            eventCoding=Coding(
                system=code_system,
                code=use_case,
                display=use_case_display
            ),
            source=source,
            destination=destinations,
            sender=message_sender,
            focus=[ReferenceType(reference=f"urn:uuid:{focus_reference}")]
        )
        return message_header


class MessageBundleCreator:
    @staticmethod
    def create_message_bundle(message_header: MessageHeader, resources: List[BundleEntry]) -> Bundle:
        bundle_id = str(uuid4())

        entries = [
            BundleEntry(
                fullUrl=f"urn:uuid:{message_header.id}", resource=message_header)
        ]

        entries.extend(resources)

        message_bundle = Bundle(
            id=bundle_id,
            meta=Meta.construct(profile=[
                "https://gematik.de/fhir/atf/StructureDefinition/bundle-app-transport-framework"
            ]),
            type="message",
            identifier=IdentifierType(
                system="urn:ietf:rfc:3986", value=f"urn:uuid:{bundle_id}"),
            entry=entries
        )

        return message_bundle


class OperationOutcomeBundleCreator:
    @staticmethod
    def create_operation_outcome_bundle(message_sender: ReferenceType,
                                        source: MessageHeaderSource,
                                        destinations: List[MessageHeaderDestination],
                                        operation_outcome: OperationOutcome) -> Bundle:

        message_header = MessageHeaderCreator.create_message_header(
            str(uuid4()),
            message_sender,
            source,
            destinations,
            code_system="https://gematik.de/fhir/atf/CodeSystem/operation-identifier-cs",
            use_case="atf;Empfangsbestaetigung",
            use_case_display="Empfangsbestätigung und Auskunft über FHIR Interpretierbarkeit der Nachricht",
            focus_reference=operation_outcome.id)

        resources = [
            BundleEntry(
                fullUrl=f"urn:uuid:{operation_outcome.id}",
                resource=operation_outcome
            )
        ]

        bundle = MessageBundleCreator.create_message_bundle(
            message_header=message_header,
            resources=resources
        )

        return bundle
