#!/usr/bin/env python3

from tree_sitter import Language, Parser
import tree_sitter_c as tsc
import sys
import os
import re
from threading import Lock, local
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

from HG.Knowledge.SymMgr import SymMgr
from HG.Frontend import FrontendMgr

max_workers = 16

sym_mgr = SymMgr()
func_def_mgr = sym_mgr.get_func_def_mgr()
macro_def_mgr = sym_mgr.get_macro_def_mgr()
gvar_def_mgr = sym_mgr.get_gvar_def_mgr()
struct_def_mgr = sym_mgr.get_struct_def_mgr()
func_use_mgr = sym_mgr.get_func_use_mgr()

frontend_mgr = FrontendMgr()
include_mgr = frontend_mgr.get_include_mgr()

INLINE_PATTERN = re.compile(
    r"\b(?:inline|__inline|__inline__|"
    r"__always_inline|__always_inline__)\b"
)

def get_node_text(node, source_code):
    return source_code[node.start_byte:node.end_byte].decode(
        "utf-8",
        errors="replace",
    )

def get_identifier(node):
    if node is None:
        return None

    if node.type == "identifier":
        return node

    declarator = node.child_by_field_name("declarator")
    if declarator is not None:
        identifier = get_identifier(declarator)
        if identifier is not None:
            return identifier

    for child in node.named_children:
        identifier = get_identifier(child)
        if identifier is not None:
            return identifier

    return None

def get_typedef_identifier(node):
    if node is None:
        return None

    if node.type in ("identifier", "type_identifier"):
        return node

    declarator = node.child_by_field_name("declarator")
    if declarator is not None:
        identifier = get_typedef_identifier(declarator)
        if identifier is not None:
            return identifier

    for child in node.named_children:
        identifier = get_typedef_identifier(child)
        if identifier is not None:
            return identifier

    return None


def collect_struct_typedef_names(root_node, source_code):
    struct_typedef_names = set()
    stack = [root_node]

    while stack:
        node = stack.pop()

        if node.type == "type_definition":
            type_node = node.child_by_field_name("type")

            if (
                type_node is not None
                and type_node.type == "struct_specifier"
            ):
                for child in node.named_children:
                    if child == type_node:
                        continue

                    identifier = get_typedef_identifier(child)
                    if identifier is not None:
                        struct_typedef_names.add(
                            get_node_text(identifier, source_code)
                        )

        stack.extend(reversed(node.named_children))

    return struct_typedef_names


def is_file_scope_declaration(node):
    parent = node.parent

    while parent and parent.type.startswith("preproc_"):
        parent = parent.parent

    return (
        parent is not None
        and parent.type == "translation_unit"
    )


def is_static(func_node, source_code):
    for child in func_node.children:
        if child.type == "storage_class_specifier":
            text = get_node_text(child, source_code)
            if text == "static":
                return True

    prev_node = func_node.prev_sibling
    if prev_node is None:
        return False

    if prev_node.start_point[0] == func_node.start_point[0]:
        for child in prev_node.children:
            if child.type == "storage_class_specifier":
                text = get_node_text(child, source_code)
                if text == "static":
                    return True

    return False


def is_inline(func_node, source_code):
    body_node = func_node.child_by_field_name("body")

    if body_node is not None:
        header_end_byte = body_node.start_byte
    else:
        header_end_byte = func_node.end_byte

    function_header = source_code[
        func_node.start_byte:header_end_byte
    ].decode("utf-8", errors="replace")

    return INLINE_PATTERN.search(function_header) is not None

def is_static_gvar(gvar_node, source_code):
    for child in gvar_node.children:
        if child.type != "storage_class_specifier":
            continue

        storage_class = get_node_text(child, source_code)
        if storage_class == "static":
            return 1

    return 0

def record_func_info(src_file: str, source_code, func_node, func_name):
    func_start_line = func_node.start_point[0]
    func_end_line = func_node.end_point[0]
    func_start_byte = func_node.start_byte
    func_end_byte = func_node.end_byte

    is_static_func = 1 if is_static(func_node, source_code) else 0
    is_inline_func = 1 if is_inline(func_node, source_code) else 0

    prev_node = func_node.prev_named_sibling
    while prev_node and (
        prev_node.type == "comment"
        or prev_node.start_point[0] == func_start_line
    ):
        func_start_line = prev_node.start_point[0]
        func_start_byte = prev_node.start_byte
        prev_node = prev_node.prev_named_sibling

    func_def_mgr.record(
        src_file,
        func_name,
        is_static_func,
        is_inline_func,
        func_start_line,
        func_end_line,
        func_start_byte,
        func_end_byte,
    )


def process_func_def_node(src_file: str, source_code, func_node):
    declarator = func_node.child_by_field_name("declarator")
    identifier = get_identifier(declarator)

    if identifier is None:
        return

    func_name = get_node_text(identifier, source_code)
    record_func_info(src_file, source_code, func_node, func_name)


def record_macro_info(src_file: str, source_code, macro_node, macro_name):
    macro_start_line = macro_node.start_point[0]
    macro_end_line = macro_node.end_point[0]
    macro_start_byte = macro_node.start_byte
    macro_end_byte = macro_node.end_byte

    prev_node = macro_node.prev_named_sibling
    while prev_node and (
        prev_node.type == "comment"
        or prev_node.start_point[0] == macro_start_line
    ):
        macro_start_line = prev_node.start_point[0]
        macro_start_byte = prev_node.start_byte
        prev_node = prev_node.prev_named_sibling

    macro_def_mgr.record(
        src_file,
        macro_name,
        macro_start_line,
        macro_end_line,
        macro_start_byte,
        macro_end_byte,
    )


def process_macro_def_node(src_file: str, source_code, macro_node):
    name_node = macro_node.child_by_field_name("name")
    if name_node is None:
        return

    macro_name = get_node_text(name_node, source_code)
    record_macro_info(src_file, source_code, macro_node, macro_name)


def record_gvar_info(src_file: str, source_code, gvar_node, gvar_name, gvar_type):
    gvar_start_line = gvar_node.start_point[0]
    gvar_end_line = gvar_node.end_point[0]
    gvar_start_byte = gvar_node.start_byte
    gvar_end_byte = gvar_node.end_byte

    prev_node = gvar_node.prev_named_sibling
    while prev_node and (
        prev_node.type == "comment"
        or prev_node.start_point[0] == gvar_start_line
    ):
        gvar_start_line = prev_node.start_point[0]
        gvar_start_byte = prev_node.start_byte
        prev_node = prev_node.prev_named_sibling

    is_static_var = is_static_gvar(
        gvar_node,
        source_code,
    )

    gvar_def_mgr.record(
        src_file,
        gvar_name,
        gvar_type,
        is_static_var,
        gvar_start_line,
        gvar_end_line,
        gvar_start_byte,
        gvar_end_byte,
    )


def process_gvar_def_node(src_file, source_code, gvar_node, struct_typedef_names):
    storage_classes = [
        child
        for child in gvar_node.children
        if child.type == "storage_class_specifier"
    ]

    if storage_classes and any(
        get_node_text(child, source_code) == "extern"
        for child in storage_classes
    ):
        return

    type_node = None

    for child in gvar_node.children:
        if child.type == "struct_specifier":
            type_node = child
            break

        if child.type == "type_identifier":
            type_name = get_node_text(child, source_code)

            if type_name in struct_typedef_names:
                type_node = child
                break

    if type_node is None:
        return

    type_name = get_node_text(type_node, source_code)

    for child in gvar_node.children:
        if child.type != "init_declarator":
            continue

        var_node = child.child_by_field_name("declarator")
        if var_node is None:
            continue

        var_name = get_node_text(var_node, source_code)

        record_gvar_info(src_file, source_code, gvar_node, var_name, type_name)


def declaration_has_declarator(declaration_node, struct_node):
    declarator_types = {
        "identifier",
        "init_declarator",
        "pointer_declarator",
        "array_declarator",
        "function_declarator",
        "parenthesized_declarator",
    }

    for child in declaration_node.named_children:
        if child == struct_node:
            continue

        if child.type in declarator_types:
            return True

    return False


def record_struct_info(src_file: str, source_code, start_node, end_node, 
                struct_name, typedef_name):
    struct_start_line = start_node.start_point[0]
    struct_start_byte = start_node.start_byte

    prev_node = start_node.prev_named_sibling
    while prev_node and (
        prev_node.type == "comment"
        or prev_node.start_point[0] == struct_start_line
    ):
        struct_start_line = prev_node.start_point[0]
        struct_start_byte = prev_node.start_byte
        prev_node = prev_node.prev_named_sibling

    struct_end_line = end_node.end_point[0]
    struct_end_byte = end_node.end_byte

    struct_def_mgr.record(
        src_file,
        struct_name,
        typedef_name,
        struct_start_line,
        struct_end_line,
        struct_start_byte,
        struct_end_byte,
    )


def process_struct_def_node(src_file, source_code, node):
    typedef_name = "<None>"
    struct_name = "<None>"

    if node.type == "struct_specifier":
        struct_node = node
        start_node = struct_node
        end_node = struct_node

        if (
            struct_node.parent is not None
            and struct_node.parent.type == "declaration"
        ):
            declaration_node = struct_node.parent
            start_node = declaration_node

            if not declaration_has_declarator(
                declaration_node,
                struct_node,
            ):
                end_node = declaration_node

    elif node.type == "type_definition":
        typedef_node = node

        struct_node = typedef_node.child_by_field_name("type")
        if (
            struct_node is None
            or struct_node.type != "struct_specifier"
        ):
            return

        declarator = typedef_node.child_by_field_name("declarator")
        identifier = get_typedef_identifier(declarator)

        if identifier is None:
            return

        typedef_name = get_node_text(identifier, source_code)
        start_node = typedef_node
        end_node = typedef_node

    else:
        return

    body = (
        struct_node.child_by_field_name("body")
        or struct_node.child_by_field_name(
            "field_declaration_list"
        )
    )

    if body is None:
        return

    struct_name_node = struct_node.child_by_field_name("name")
    if struct_name_node is not None:
        struct_name = get_node_text(
            struct_name_node,
            source_code,
        )

    if (
        typedef_name == "<None>"
        and struct_name == "<None>"
    ):
        return

    record_struct_info(src_file, source_code, 
            start_node, end_node, struct_name, typedef_name)


def collect_sym_def_in_file(src_file: str):
    try:
        abs_src_path = frontend_mgr.get_abspath_from_src(src_file)
        with open(abs_src_path, "rb") as file:
            source_code = file.read()

        c_language = Language(tsc.language())
        parser = Parser(c_language)
        tree = parser.parse(source_code)
        root_node = tree.root_node

        struct_typedef_names = collect_struct_typedef_names(
            root_node,
            source_code,
        )

        stack = [root_node]

        while stack:
            node = stack.pop()

            if node.type == "function_definition":
                process_func_def_node(
                    src_file,
                    source_code,
                    node,
                )

            elif node.type in (
                "preproc_function_def",
                "preproc_def",
            ):
                process_macro_def_node(
                    src_file,
                    source_code,
                    node,
                )

            elif node.type == "declaration":
                if is_file_scope_declaration(node):
                    process_gvar_def_node(
                        src_file,
                        source_code,
                        node,
                        struct_typedef_names,
                    )

            elif node.type == "type_definition":
                process_struct_def_node(
                    src_file,
                    source_code,
                    node,
                )

            elif node.type == "struct_specifier":
                if not (
                    node.parent
                    and node.parent.type == "type_definition"
                ):
                    process_struct_def_node(
                        src_file,
                        source_code,
                        node,
                    )

            stack.extend(reversed(node.children))
    except Exception:
        traceback.print_exc()


def collect_sym_def():
    include_items = include_mgr.get_all()

    all_files = {
        file_path
        for item in include_items
        for file_path in [
            item.main_file,
            *item.include_files.split(),
        ]
        if file_path
    }

    futures = {}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for index, file_path in enumerate(
            all_files,
            start=1,
        ):
            future = pool.submit(
                collect_sym_def_in_file,
                file_path,
            )
            futures[future] = (index, file_path)

        for future in as_completed(futures):
            index, file_path = futures[future]

            try:
                future.result()
            except Exception as error:
                print(f"Error in {file_path}: {error}")

            print(
                f"{index}/{len(all_files)} {file_path}"
            )

def main():
    collect_sym_def()

if __name__ == "__main__":
    main()
