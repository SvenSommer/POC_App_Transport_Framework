from typing import Tuple
from fhir.resources.bundle import Bundle
from fhir.resources.operationoutcome import OperationOutcomeIssue
from fhir.resources.messageheader import MessageHeader
from fhir.resources.bundle import BundleEntry

from atf_message_library.atf_message_processor.base_use_case_handler import BaseUseCaseHandler


class EmpfangsbestaetigungHandler(BaseUseCaseHandler):
    def handle(self, message_header: MessageHeader, bundle: Bundle) -> Tuple[list[BundleEntry], list[OperationOutcomeIssue]]:
        return self.bundleEntries, self.issues
