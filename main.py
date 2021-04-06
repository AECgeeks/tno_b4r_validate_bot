"""
SHACL-based validation BIM Bot.

Written by Thomas Krijnen <thomas@aecgeeks.com>
"""

import os
import io
import uuid
import glob
import base64
import zipfile
import tempfile
import datetime

from tabulate import tabulate

import run_validate

from flask import Flask, render_template, request, send_file, jsonify
from dataclasses import dataclass

app = Flask(__name__)

@dataclass
class BcfComment:
    date: str
    author: str
    comment: str
    
@dataclass
class BcfTopic:
    date: str
    guid: str
    title: str
    
    
def bcf_viz(elements):
    """
    Creates the BCF VisualizationInfo as string
    """
    
    C = """
        <Component IfcGuid="%s" Selected="true" />"""
    return """<?xml version="1.0" encoding="utf-8"?>
<VisualizationInfo xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <Components>%s</Components>
</VisualizationInfo>
""" % "".join(C % e for e in elements)

def bcf_version():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Version xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" VersionId="2.0" xsi:noNamespaceSchemaLocation="version.xsd">
    <DetailedVersion>2.0 RC</DetailedVersion>
</Version>
"""

def bcf_markup(project_guid, title, guid, vp_guid):
    """
    Creates the BCF Markup as string
    """

    dt = datetime.datetime.now()
    date = dt.isoformat(sep='T').replace('+00:00', 'Z')
    
    comment = """
    <Comment Guid="3d56f8d1-149a-4cb5-86df-ec3049648169">
      <Date>%(date)s</Date>
      <Comment>%(text)s</Comment>
      <Topic Guid="%(guid)s"/>
      <Viewpoint/>
    </Comment>
""" 

    # comment_data = "".join(comment % c.__dict__ for c in comments)

    return """<?xml version="1.0" encoding="utf-8"?>
<Markup xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Header>
    <File IfcProject="%(project_guid)s" isExternal="true"/>
  </Header>
  <Topic Guid="%(guid)s">
    <Title>%(title)s</Title>
    <CreationDate>%(date)s</CreationDate>
  </Topic>
  <ViewPoints>
    <Viewpoint>Viewpoint_%(vp_guid)s.bcfv</Viewpoint>
  </ViewPoints>
</Markup>
"""  % locals()


def create_bcf(project_guid, comments):
    """
    Creates the BCF zip
    """
    
    zfb = io.BytesIO()
    zf = zipfile.ZipFile(zfb, "a", zipfile.ZIP_DEFLATED, False)
    zf.writestr("bcf.version", bcf_version())
    
    for elem_guid, text in comments:
        guid = str(uuid.uuid4())
        vp_guid = str(uuid.uuid4())
    
        zf.writestr("%s/markup.bcf" % guid, bcf_markup(
            project_guid=project_guid,
            title=text,
            guid=guid,
            vp_guid=vp_guid
        ))
        
        zf.writestr("%s/Viewpoint_%s.bcfv" % (guid, vp_guid), bcf_viz(
            [elem_guid]
        ))
    
    # Mark the files as having been created on Windows so that
    # Unix permissions are not inferred as 0000
    for zfile in zf.filelist:
        zfile.create_system = 0
        
    zf.close()
    zfb.seek(0)
    
    return zfb


@app.route('/' , methods = ['POST', 'GET'])
def entry_point():
    """
    Main entry point of the web application. Accepts an IFC file either
    as HTML form upload or BIM Bot invocation and based on HTTP Accept
    header renders a HTML output or BIM Bot reply.
    """
    
    use_html = 'text/html' in str(request.accept_mimetypes)
    
    if request.method == 'POST':
        handle, filename = tempfile.mkstemp()
        
        if use_html:
            f = request.files['file']
            os.close(handle)
            f.save(filename)
        
        else:
            payload = request.json
            b64_data = payload['inputs'][0]['location'].split(',')[1]
            contents = base64.b64decode(b64_data).decode('utf-8')

            with os.fdopen(handle, 'w', encoding='utf-8') as f:
                f.write(contents)
            
        R = list(run_validate.run(filename, *glob.glob(os.path.join("shapes", "Shapes", "*.ttl"))))
        project_guid, issues = R[0], R[1:]
        
        result = tabulate(issues, headers=["GlobalId", "Message"], tablefmt="html")
            
        bcf = create_bcf(
            project_guid,
            issues
        )

        url = "data:application/octet-stream;base64," + base64.b64encode(bcf.getvalue()).decode('ascii')
    else:
        result = ''
        url = None
    
    if use_html:
        shacl_content = '\n\n\n'.join(open(fn).read() for fn in glob.glob(os.path.join("shapes", "Shapes", "*.ttl")))
        return render_template(
            'index.html', 
            shacl_content=shacl_content,
            result=result,
            url = url
        )
    elif request.method == 'POST':
        return jsonify({
            "type": "FILE",
            "schema": "BCF_ZIP_2_0",
            "location": url
        })
    else:
        return "BIM BOT INTERFACE"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
