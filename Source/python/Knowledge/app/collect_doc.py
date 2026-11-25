#!/usr/bin/env python3

import os
import sys
import json
from pathlib import Path

from lxml import etree
from HG.Common.Path import PathMgr
from HG.Knowledge.SymMgr import SymMgr

doc_list = []
path_mgr = PathMgr()
sym_mgr = SymMgr()

def remove_namespaces(elem):
    new_elem = etree.Element(etree.QName(elem).localname)

    if elem.text:
        new_elem.text = elem.text
    if elem.tail:
        new_elem.tail = elem.tail
    for k, v in elem.attrib.items():
        attr_name = etree.QName(k).localname
        new_elem.set(attr_name, v)

    for child in elem:
        new_elem.append(remove_namespaces(child))

    return new_elem

def get_name(desc_node):
    sig = desc_node.find(".//desc_signature_line")
    name_elem = sig.find(".//desc_sig_name")
    if name_elem is None:
        return ""
    name = name_elem.text.strip()
    return name

def get_summary(desc_node):
    desc_content_node = desc_node.find("./desc_content")
    desc_content = ""
    if desc_content_node is not None:
        desc_content = "".join([etree.tostring(child, encoding='unicode', pretty_print=True) for child in desc_content_node.iterchildren()])
    return desc_content

def get_content(container_node):
    if container_node is None:
        return ""
    return "".join([etree.tostring(child, encoding='unicode', pretty_print=True) for child in container_node.iterchildren()])

def parse_func_node_list(desc_node, container_node):
    func_name = get_name(desc_node)
    func_sum = get_summary(desc_node)
    func_content = get_content(container_node)
    func_info = {
            "name": func_name,
            "class": "function",
            "summary": func_sum,
            "content": func_content,
            }
    return func_info

def parse_struct_node_list(desc_node, container_node):
    struct_name = get_name(desc_node)
    struct_sum = get_summary(desc_node)
    struct_content = get_content(container_node)
    struct_info = {
            "name": struct_name,
            "class": "struct",
            "summary": struct_sum,
            "content": struct_content,
            }
    return struct_info

def parse_macro_node_list(desc_node, container_node, aux_node_list):
    macro_name = get_name(desc_node)
    macro_sum = full_text = "\n".join("".join(node.itertext()).strip() for node in aux_node_list)
    macro_content = get_content(container_node)
    macro_info = {
            "name": macro_name,
            "class": "macro",
            "summary": macro_sum,
            "content": macro_content
            }
    return macro_info

def parse_target_node_list(target_node_list):
    desc_node = None
    container_node = None
    for target_node in target_node_list:
        if target_node.tag == "desc":
            desc_node = target_node
        if target_node.tag == "container":
            container_node = target_node
    if desc_node is None:
        return None

    aux_node_list = [node for node in target_node_list if node.tag != "desc" and node.tag != "container"]

    class_type = desc_node.get("classes")
    if class_type == "c function":
        return parse_func_node_list(desc_node, container_node)
    elif class_type == "c struct":
        return parse_struct_node_list(desc_node, container_node)
    elif class_type == "c macro":
        return parse_macro_node_list(desc_node, container_node, aux_node_list)
    else:
        return None

def parse_node_list(node_list):
    target_node_list = []
    is_start = False
    for node in node_list:
        if node.tag == "index":
            if is_start and target_node_list:
                doc = parse_target_node_list(target_node_list)
                if doc:
                    doc_list.append(doc)
            target_node_list = [node]
            is_start = True
        else:
            if is_start:
                target_node_list.append(node)

def parse_tree(node, depth=0):
    if node.find("index") is not None and node.find("desc") is not None:
        child_list = []
        for child in node.iterchildren():
            child_list.append(child)
        parse_node_list(child_list)

    for child in node.iterchildren():
        parse_tree(child)

def parse_xml(xml_file):
    parser = etree.XMLParser(recover=True)
    tree = etree.parse(xml_file, parser)
    root = tree.getroot()
    clean_root = remove_namespaces(root)
    parse_tree(clean_root)


def main():
    checked_src_path = Path(path_mgr.get_checked_root())
    directory = checked_src_path / "Documentation" / "output" / "xml"
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(".xml"):
                path = os.path.join(root, f)
                try:
                    parse_xml(path)
                except Exception as e:
                    print("Error parsing:", path, e)

    with open(sym_mgr.get_doc_path(), "w") as f:
        json.dump(doc_list, f, indent = 2)

if __name__ == "__main__":
    main()

