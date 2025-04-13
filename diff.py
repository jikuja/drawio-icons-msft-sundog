import argparse
import base64
import difflib
import logging
import sys
from typing import TypedDict
import xml.etree.ElementTree as ET
import json
import zlib

# XML helpers
# source: https://github.com/joh/xmldiffs/blob/master/xmldiffs#L33
""" 
Copyright (c) 2017-2022, xmldiffs developers.

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

* Redistributions of source code must retain the above copyright
  notice, this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright
  notice, this list of conditions and the following disclaimer in the
  documentation and/or other materials provided with the distribution.

* The names of the contributors may not be used to endorse or promote 
  products derived from this software without specific prior written
  permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. """


def attr_str(k, v):
    return "{}=\"{}\"".format(k,v)

def node_str(n):
    attrs = sorted(n.attrib.items())
    astr = " ".join(attr_str(k,v) for k,v in attrs)
    s = n.tag
    if astr:
        s += " " + astr
    return s

def node_key(n):
    return node_str(n)

def sort_xml(node, level=0):
    """Return a list of text lines from an I{ElementTree} node

    @param node: an C{Element} object containing XML data.
    @param level: text indentation level.

    """
    indent = "  " * level
    children = list(node)
    text = (node.text or "").strip()
    tail = (node.tail or "").strip()
    out = []

    if children or text:
        children.sort(key=node_key)

        node_start = "%s<%s>" % (indent, node_str(node))

        if text and len(children) == 0:
            line_length = len(node_start) + len(text) + 1 + len(node.tag) + 1
            if line_length < 120:
                out.append("%s%s</%s>\n" % (node_start, text, node.tag))
            else:
                out.append(node_start + "\n")
                out.append("%s%s\n" % (indent, text))
                out.append("%s</%s>\n" % (indent, node.tag))

        else:
            out.append(node_start + "\n")
            if text:
                out.append("%s%s\n" % (indent, text))
            for child in sorted(children, key=node_key):
                out.extend(sort_xml(child, level+1))
            out.append("%s</%s>\n" % (indent, node.tag))
    else:
        out.append("%s<%s/>\n" % (indent, node_str(node)))

    if tail:
        out.append("%s%s\n" % (indent, tail))

    return out

# End of XML helpers

DEFAULT_STYLE=('shape=image;'
               'verticalLabelPosition=bottom;'
               'align=center;verticalAlign=top;' # label alignment
               'imageAlign=center;imageVerticalAlign=middle;' # image alignment
               'imageAspect=1;aspect=fixed')

def _setup_argparse():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-level", help="Configure the logging level.", default=logging.INFO, type=lambda x: getattr(logging, x))
    parser.add_argument('--svg', action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('--inner-xml', action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('file', help='input file', nargs=2)
    args = parser.parse_args()

    if not args.file[0] or not args.file[1]:
        print('Input files required')
        parser.print_usage()
        sys.exit(1)

    return args

def extract_xml(xml):
    data = base64.b64decode(xml)
    #print(data)
    xml_str = zlib.decompress(data, wbits=-15).decode('utf-8')
    tree = ET.fromstring(xml_str)
    return tree

def extract_style(element) -> str:
    style = element.find(".//mxCell[@id='2']").get('style')
    if style:
        return style
    else:
        raise ValueError("Element does not have a style attribute")

def extract_svg_from_style(style: str):
    logger.error(style)
    splitted_style = style.split(';image=data:image/svg+xml,')
    svg = base64.b64decode(splitted_style[1]).decode('utf-8')
    return svg

def compare_svg_headers(svg1: str, svg2: str):
    # Compare the headers of two SVG files
    # <svg data-slug-id="72-percent" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
    hasChanges = False
    el1 = ET.fromstring(svg1).find(".//svg")
    el2 = ET.fromstring(svg2).find(".//svg")
    diff = list(difflib.unified_diff(
                        sort_xml(el1), sort_xml(el2)))
    sys.stdout.writelines(diff)
    hasChanges = len(diff) > 0
    return hasChanges

def compare_svg(svg1: str, svg2: str):
    # Compare the headers of two SVG files
    # <svg data-slug-id="72-percent" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
    hasChanges = False
    el1 = ET.fromstring(svg1)
    el2 = ET.fromstring(svg2)
    logger.debug("asdfgh %s", el1.tail)
    logger.debug("asdfgh %s", el2.tail)
    elems1 = [elem.tag for elem in el1.iter() if elem is not el1]
    elems2 = [elem.tag for elem in el2.iter() if elem is not el2]
    diff = list(difflib.unified_diff(elems1, elems2))
    sys.stdout.writelines(diff)
    hasChanges = len(diff) > 0
    return hasChanges

logger = logging.getLogger(__name__)

def main():
    #print(len(sys.argv))
    args = _setup_argparse()
    logging.basicConfig(level=args.log_level)

    #print(args.file[0])

    # First layer of XML is
    # <mxlibrary>...</mxlibrary>
    # where... is JSON array of objects with xml, w, h and title keys
    class mxlibraryObject(TypedDict):
        xml: str
        w: int
        h: int
        title: str
    tree1 = ET.parse(args.file[0])
    tree2 = ET.parse(args.file[1])
    text1 = tree1.getroot().text
    text2 = tree2.getroot().text
    objects1: mxlibraryObject = json.loads(text1)
    objects2: mxlibraryObject = json.loads(text2)

    changes = []

    for item1 in objects1:
        found = False
        for item2 in objects2:
            if item1['title'] == item2['title']:
                found = True
                break
        if not found:
            changes.append({"change": "D", "item": item1['title']})

    for item2 in objects2:
        found = False
        for item1 in objects1:
            if item2['title'] == item1['title']:
                found = True
                break
        if not found:
            changes.append({"change": "A", "item": item2['title']})
        if found:
            # title is handled earlier and h and w should be stable
            if item1['xml'] != item2['xml']:
                changes.append({"change": "C", "item": item1['title']})
                logger.debug(f"XML changed: {item1['title']}")
                xml1 = extract_xml(item1['xml'])
                xml2 = extract_xml(item2['xml'])
                
                if args.inner_xml:
                    diff = difflib.unified_diff(
                        sort_xml(xml1), sort_xml(xml2),
                        'before', 'after', n=3
                    )
                    #sys.stdout.writelines(diff)
                if args.svg:
                    style1 = extract_style(xml1)
                    style2 = extract_style(xml2)
                    svg1 = extract_svg_from_style(style1)
                    svg2 = extract_svg_from_style(style2)
                    logger.debug("svg1: %s", svg1)
                    logger.debug("svg2: %s", svg2)
                    logger.info("=====DIFF=====")
                    if compare_svg_headers(svg1, svg2):
                        logger.info("Headers are different")
                    if compare_svg(svg1, svg2):
                        logger.info("SVGs are different")
                    # for some reason this results really messy diff
                    diff = difflib.unified_diff(
                        svg1, svg2,
                        'before', 'after', n=3
                    )
                    #sys.stdout.writelines(diff)
            else:
                changes.append({"change": "N/A", "item": item1['title']})
    print("Comparison complete.")

    for change in changes:
        if change['change'] == 'A':
            print(f"Added: {change['item']}")
    for change in changes:
        if change['change'] == 'D':
            print(f"Deleted: {change['item']}")
    for change in changes:
        if change['change'] == 'C':
            print(f"Changed: {change['item']}")
    for change in changes:
        if change['change'] == 'N/A':
            print(f"Changed: {change['item']}")

    print("========== Summary ==========")
    print(f"Changed: {len([c for c in changes if c['change'] == 'C'])}")
    print(f"Added: {len([c for c in changes if c['change'] == 'A'])}")
    print(f"Deleted: {len([c for c in changes if c['change'] == 'D'])}")
    print(f"Unchanged: {len([c for c in changes if c['change'] == 'N/A'])}")
    print(f"Total: {len(changes)}")
    print("Done.")

if __name__ == '__main__':
    main()
