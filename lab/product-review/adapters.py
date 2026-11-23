"""Registered adapter for an accepted external operation with a separately queried receipt."""
from urllib.parse import quote


class ReceiptJob:
    def __init__(self, descriptor):
        if (descriptor["mode"], descriptor["side_effect"], descriptor["status_source"]) != (
            "asynchronous", "submit", "lookup"
        ):
            raise ValueError("unsupported external receipt contract")
        self.name = descriptor["name"]

    def dispatch(self, transport, operation, call):
        return transport("submit", {"op":operation, "call":call.tool_call_id,
                                    "name":self.name, "input":call.args_as_dict()})

    def lookup(self, transport, operation):
        return transport("lookup/" + quote(operation, safe=""))


def adapter_for(descriptor):
    constructors = {"external_receipt_v1": ReceiptJob}
    return constructors[descriptor["adapter"]](descriptor)
