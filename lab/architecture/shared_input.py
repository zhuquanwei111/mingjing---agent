"""Business-neutral test vectors, public capability descriptors and synthetic inputs."""
import hashlib, os
from pydantic import BaseModel, ConfigDict, create_model

class Payload(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
class Output(Payload):
    value:str
def schema(spec):
    return create_model("Input_"+spec["name"],__base__=Payload,**{n:(str,...) for n in spec["fields"]})
def tool_descriptions(specs):
    return [{"type":"function","function":{"name":s["name"],"description":s["description"],"parameters":schema(s).model_json_schema()}} for s in specs]
BASE=[{"name":"read_manifest","fields":["resource"],"description":"Read the synthetic resource named bundle. Returns an opaque lookup key in value."},
      {"name":"item_state","fields":["key"],"description":"Find the item status with the exact lookup key returned by read_manifest."}]
def challenge():
    h=hashlib.sha256(("sealed-capability/"+os.environ["LAB_REV"]).encode()).hexdigest()
    return {"name":"inspect_"+h[:12],"fields":["ref_"+h[12:19],"kind_"+h[19:24]],"description":"Verify both opaque fields and return their canonical JSON."}
