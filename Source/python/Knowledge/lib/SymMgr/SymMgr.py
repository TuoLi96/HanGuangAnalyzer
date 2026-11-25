from HG.Common.Path import PathMgr
from HG.Common.Database import DBMgr
from HG.Frontend import IncludeMgr
from HG.Knowledge.SymMgr import FuncDefMgr, MacroDefMgr, StructDefMgr, GvarDefMgr, FuncUseMgr

from pathlib import Path
import json

class SymMgr(PathMgr):
    def __init__(self):
        super().__init__()
        self.compile_dir = self.work_root / "Compile"
        self.compile_db_path = self.db_root / "Compile" / "compile.db"
        self.compile_db_mgr = DBMgr(self.compile_db_path)
        self.include_mgr = IncludeMgr(self.compile_db_mgr)

        self.knowledge_db_path = self.db_root / "Knowledge" / "knowledge.db"
        self.knowledge_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.knowledge_doc_path = self.db_root / "Knowledge" /  "doc.json"

        self.knowledge_db_mgr = DBMgr(self.knowledge_db_path)
        self.func_def_mgr = FuncDefMgr(self.knowledge_db_mgr)
        self.macro_def_mgr = MacroDefMgr(self.knowledge_db_mgr)
        self.gvar_def_mgr = GvarDefMgr(self.knowledge_db_mgr)
        self.struct_def_mgr = StructDefMgr(self.knowledge_db_mgr)
        self.func_use_mgr = FuncUseMgr(self.knowledge_db_mgr)

        self.prepareTbl()
    
    def prepareTbl(self):
        db_schema_dir = self.metadata_root / "Knowledge" / "DBSchema"
        func_def_schema_path = db_schema_dir / "func_def.schema"
        with open(func_def_schema_path, "r", encoding="utf-8") as f:
            db_schema = f.read()
            self.knowledge_db_mgr.execute(db_schema)

        macro_def_schema_path = db_schema_dir / "macro_def.schema"
        with open(macro_def_schema_path, "r", encoding="utf-8") as f:
            db_schema = f.read()
            self.knowledge_db_mgr.execute(db_schema)
        
        gvar_def_schema_path = db_schema_dir / "gvar_def.schema"
        with open(gvar_def_schema_path, "r", encoding="utf-8") as f:
            db_schema = f.read()
            self.knowledge_db_mgr.execute(db_schema)
        
        struct_def_schema_path = db_schema_dir / "struct_def.schema"
        with open(struct_def_schema_path, "r", encoding="utf-8") as f:
            db_schema = f.read()
            self.knowledge_db_mgr.execute(db_schema)
        
        func_use_schema_path = db_schema_dir / "func_use.schema"
        with open(func_use_schema_path, "r", encoding="utf-8") as f:
            db_schema = f.read()
            self.knowledge_db_mgr.execute(db_schema)

    def get_knowledge_db_mgr(self):
        return self.knowledge_db_mgr

    def get_func_def_mgr(self):
        return self.func_def_mgr

    def get_macro_def_mgr(self):
        return self.macro_def_mgr

    def get_gvar_def_mgr(self):
        return self.gvar_def_mgr

    def get_struct_def_mgr(self):
        return self.struct_def_mgr

    def get_func_use_mgr(self):
        return self.func_use_mgr

    def get_doc_path(self):
        return str(self.knowledge_doc_path)

    def get_abs_path(self, file_path: str):
        p = Path(file_path)
        if p.is_absolute():
            return str(p.resolve())
        return str((self.checked_src_root / p).resolve())

    def get_relative_path(self, file_path: str):
        p = Path(file_path)
        if not p.is_absolute():
            return str(p)
        try:
            return str(p.resolve().relative_to(self.checked_src_root))
        except ValueError:
            return str(p)

    def get_text(self, file_path: str, start_byte: int, end_byte: int):
        file_path = self.get_abs_path(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()
            source_text = source_code[start_byte:end_byte]
            start_line = source_code[:start_byte].count("\n") + 1
            lines = source_text.splitlines()
            numbered_source_text = [f"{start_line + i:>5} | {line}" for i, line in enumerate(lines)]
            return (f"File: {self.get_relative_path(file_path)}"
                    f"\n{"\n".join(numbered_source_text)}")
        return None

    def get_func_def(self, src_file, func_name):
        #src_file = self.get_abs_path(src_file)
        func_def_items = self.func_def_mgr.get_by_func_name(func_name)
        for func_def in func_def_items:
            if func_def.src_file == src_file:
                return self.get_text(src_file, func_def.start_byte, func_def.end_byte)
        include_items = self.include_mgr.get_by_main_file(src_file)
        if not include_items:
            return (f"Can not find definition of {func_name}")
        include_files = include_items[0].include_files
        for func_def in func_def_items:
            if func_def.src_file in include_files:
                return self.get_text(func_def.src_file, func_def.start_byte, func_def.end_byte)
        for func_def in func_def_items:
            if func_def.is_static == 0:
                return self.get_text(func_def.src_file, func_def.start_byte, func_def.end_byte)
        return (f"Can not find definition of {func_name}")

    def get_func_use(self, src_file, func_name):
        #src_file = self.get_abs_path(src_file)
        func_use_items = self.func_use_mgr.get_by_src_func_name(src_file, func_name)
        func_use_info = ""
        for i, func_use_item in enumerate(func_use_items):
            func_use_info = (f"{func_use_info}\n"
                        f"{i}. {func_use_item.use_info}")
        if func_use_info == "":
            func_use_info = f"Can not find uses of {func_name} in file {src_file}"
        return func_use_info

    def get_macro_def(self, src_file, macro_name):
        #src_file = self.get_abs_path(src_file)
        macro_def_items = self.macro_def_mgr.get_by_macro_name(macro_name)
        for macro_def in macro_def_items:
            if macro_def.src_file == src_file:
                return self.get_text(src_file, macro_def.start_byte, macro_def.end_byte)
        include_items = self.include_mgr.get_by_main_file(src_file)
        if not include_items:
            return (f"Can not find definition of {macro_name}")
        include_files = include_items[0].include_files
        for macro_def in macro_def_items:
            if macro_def.src_file in include_files:
                return self.get_text(macro_def.src_file, macro_def.start_byte, macro_def.end_byte)
        return (f"Can not find definition of {macro_name}")

    def get_gvar_def(self, src_file, gvar_name):
        #src_file = self.get_abs_path(src_file)
        gvar_def_items = self.gvar_def_mgr.get_by_gvar_name(gvar_name)
        for gvar_def in gvar_def_items:
            if gvar_def.src_file == src_file:
                return self.get_text(src_file, gvar_def.start_byte, gvar_def.end_byte)
        include_items = self.include_mgr.get_by_main_file(src_file)
        if not include_items:
            return (f"Can not find definition of {gvar_name}")
        include_files = include_items[0].include_files
        for gvar_def in gvar_def_items:
            if gvar_def.src_file in include_files:
                return self.get_text(gvar_def.src_file, gvar_def.start_byte, gvar_def.end_byte)
        return (f"Can not find definition of {gvar_name}")

    def get_struct_def(self, src_file, struct_name):
        #src_file = self.get_abs_path(src_file)
        struct_def_items = self.struct_def_mgr.get_by_struct_name(struct_name)
        for struct_def in struct_def_items:
            if struct_def.src_file == src_file:
                return self.get_text(src_file, struct_def.start_byte, struct_def.end_byte)
        include_items = self.include_mgr.get_by_main_file(src_file)
        if not include_items:
            return (f"Can not find definition of {struct_name}")
        include_files = include_items[0].include_files
        for struct_def in struct_def_items:
            if struct_def.src_file in include_files:
                return self.get_text(struct_def.src_file, struct_def.start_byte, struct_def.end_byte)
        return (f"Can not find definition of {struct_name}")

    def get_doc(self, symbol_name):
        def find_items(json_path, symbol_name):                                         
            with open(json_path, "r", encoding="utf-8") as f:                           
                data = json.load(f)                                                     
            return [item for item in data if item.get("name") == symbol_name]
        item_list = find_items(self.knowledge_doc_path, symbol_name)
        if item_list:
            return json.dumps(item_list, ensure_ascii=False, indent=2)
        else:
            return f"Can not find document about {symbol_name}"

