"""
SHACL-based validation BIM Bot.

Written by Thomas Krijnen <thomas@aecgeeks.com>
"""

import os
import sys
import base64
import logging
# logging.basicConfig(level=logging.DEBUG)

import requests
import json

import pprint as pp

PORT=80
try:
    PORT = int(sys.argv[1])
except: pass

class P(pp.PrettyPrinter):
  def _format(self, object, *args, **kwargs):
    if isinstance(object, str):
      if len(object) > 50:
        object = object[:47] + '...'
    return pp.PrettyPrinter._format(self, object, *args, **kwargs)
    
pprint = P()

def request(url, body):
    print("> POST", url, "HTTP/1.1")
    r = requests.post(url, json=body)
    for kv in r.request.headers.items():
        print("> %s: %s" % kv)
    print(">")
    for ln in pprint.pformat(body).split("\n"):
        print(">", ln)
    print("\n")
    
    for kv in r.headers.items():
        print("< %s: %s" % kv)
    print("<")
    J = json.loads(r.content)
    for ln in pprint.pformat(J).split("\n"):
        print("<", ln)
        
    return r

def invoke_bimbot(url, files):
    def file_desc(f):
        nm = os.path.basename(f.name)
        return {
            "identifier": nm.split('.')[0],
            "type": "RDF",
            "schema": "B4R",
            "location": "data:text/turtle;base64," + base64.b64encode(f.read().encode('utf-8')).decode('ascii')
        }
        
    return request(url, {
        "inputs": list(map(file_desc, files)),
        "outputs": [{
            "type": "FILE",
            "schema": "BCF_ZIP_2_0",
            "location": "embedded"
        }]
    })
    
if __name__ == "__main__":
    resp = invoke_bimbot("http://localhost:%d" % PORT, [open('BIM4Ren_DUNANT_cleaned_IFC2x3.ifc_LBD.ttl', 'r', encoding='utf-8')])
    J = json.loads(resp.content)
    import io, zipfile
    zfb = io.BytesIO(base64.b64decode(J['location'].split(',')[1].encode('ascii')))
    zf = zipfile.ZipFile(zfb, "r")
    print("\n\n\nBCF contents:")
    for p in zf.namelist():
        print("./" + p)
    
    