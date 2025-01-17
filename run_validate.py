"""
SHACL-based validation BIM Bot.

Written by Thomas Krijnen <thomas@aecgeeks.com>
"""

import os
import rdflib
import platform
import tempfile
import subprocess

from rdflib.namespace import RDF
from rdflib import Namespace

SHACL = Namespace("http://www.w3.org/ns/shacl#")
PROPS = Namespace("http://lbd.arch.rwth-aachen.de/props#")
BOT = Namespace('https://w3id.org/bot#')

VALIDATE_PATH = "shaclvalidate.sh"
if platform.system() == 'Windows':
    SHACL_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'shacl-1.3.2')
    VALIDATE_PATH = os.path.join(SHACL_PATH, 'bin', 'shaclvalidate.bat')
    
    if not os.path.exists(VALIDATE_PATH):
        raise RuntimeError(
            "Unable to find shaclvalidate \n"
            "Download shacl from https://repo1.maven.org/maven2/org/topbraid/shacl/1.3.2/shacl-1.3.2-bin.zip\n"
            "Extract and place in the this folder: \n" + 
            os.path.abspath(os.path.dirname(__file__))            
        )
        
    os.environ['SHACL_HOME'] = SHACL_PATH

def join(graphs):
    """
    Joins ttl serialized graphs on disk
    """
    
    g = rdflib.Graph()
    for fn in graphs:
        g.parse(fn, format="ttl")
    fd, ofn = tempfile.mkstemp()
    os.close(fd)
    g.serialize(destination=ofn, format='ttl')
    return ofn

def run(data, *shapes):
    """
    Invokes `shaclvalidate.sh` on the data using the union of shapes. Both
    supplied as filenames. Returns a generator that first yields the project/
    building guid and then pairs of SHACL focus node guids and resultMessages.
    """
    
    assert len(shapes)
    
    if len(shapes) > 1:
        shapes = join(shapes)
    else:
        shapes = shapes[0]
    
    proc = subprocess.Popen(
        [VALIDATE_PATH, "-datafile", data, "-shapesfile", shapes],
        stdout=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    stdout = stdout.decode('ascii')
    
    g = rdflib.Graph()
    g.parse(data=stdout, format="ttl")
    g.parse(data, format="ttl")
    
    b = next(g.triples((None, RDF.type, BOT.Building)))[0]
    guid = next(g.triples((b, PROPS.globalIdIfcRoot, None)))[2]
    
    yield guid
    
    for s,_,__ in g.triples((None, RDF.type, SHACL.ValidationResult)):
        for _,__, rM in g.triples((s, SHACL.resultMessage, None)):
            for _,__,fN in g.triples((s, SHACL.focusNode, None)):
                for _,__,guid in g.triples((fN, PROPS.globalIdIfcRoot, None)):
                    yield guid, rM
    
if __name__ == "__main__":
    import sys
    results = run(*sys.argv[1:])
    print("Project guid:", next(results))
    for a, b in results:
        print(a, b)
