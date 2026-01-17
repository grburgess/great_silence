#!/usr/bin/env python3
"""
API Documentation Generator for Great Silence

Parses Python source files and generates MDX documentation files for Astro Starlight.
Extracts classes, functions, dataclasses, and their docstrings with proper formatting.
"""

import ast
import inspect
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_DIR = PROJECT_ROOT / "great_silence"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "src" / "content" / "docs" / "api"


@dataclass
class ParameterInfo:
    name: str
    type_hint: str
    default: Optional[str]
    description: str


@dataclass
class FunctionInfo:
    name: str
    signature: str
    docstring: str
    parameters: List[ParameterInfo]
    returns: str
    return_type: str
    decorators: List[str]
    is_method: bool = False
    is_property: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    line_number: int = 0


@dataclass
class ClassInfo:
    name: str
    docstring: str
    bases: List[str]
    methods: List[FunctionInfo]
    class_variables: Dict[str, str]
    is_dataclass: bool = False
    decorators: List[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class ModuleInfo:
    name: str
    path: str
    docstring: str
    classes: List[ClassInfo]
    functions: List[FunctionInfo]
    constants: Dict[str, str]
    imports: List[str]


def get_type_annotation_str(node: ast.AST) -> str:
    """Convert an AST annotation node to a string representation."""
    if node is None:
        return ""
    
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Constant):
        return repr(node.value)
    elif isinstance(node, ast.Subscript):
        value = get_type_annotation_str(node.value)
        slice_str = get_type_annotation_str(node.slice)
        return f"{value}[{slice_str}]"
    elif isinstance(node, ast.Tuple):
        elements = [get_type_annotation_str(el) for el in node.elts]
        return ", ".join(elements)
    elif isinstance(node, ast.Attribute):
        return f"{get_type_annotation_str(node.value)}.{node.attr}"
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = get_type_annotation_str(node.left)
        right = get_type_annotation_str(node.right)
        return f"{left} | {right}"
    elif isinstance(node, ast.List):
        elements = [get_type_annotation_str(el) for el in node.elts]
        return f"[{', '.join(elements)}]"
    
    return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)


def parse_docstring(docstring: str) -> Tuple[str, Dict[str, str], str, Dict[str, str]]:
    """
    Parse a docstring into description, parameters, returns, and other sections.
    Supports NumPy and Google docstring styles.
    """
    if not docstring:
        return "", {}, "", {}
    
    lines = docstring.strip().split('\n')
    description_lines = []
    params = {}
    returns = ""
    other_sections = {}
    
    current_section = "description"
    current_param = None
    current_content = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Check for section headers (NumPy style)
        if stripped in ("Parameters", "Args", "Arguments"):
            current_section = "parameters"
            i += 1
            if i < len(lines) and lines[i].strip().startswith('-'):
                i += 1
        elif stripped in ("Returns", "Return"):
            current_section = "returns"
            i += 1
            if i < len(lines) and lines[i].strip().startswith('-'):
                i += 1
        elif stripped in ("Raises", "Yields", "Examples", "Notes", "See Also", "Attributes"):
            current_section = stripped.lower()
            i += 1
            if i < len(lines) and lines[i].strip().startswith('-'):
                i += 1
        elif current_section == "description":
            description_lines.append(line)
            i += 1
        elif current_section == "parameters":
            # Parse parameter: name : type or name (type)
            param_match = re.match(r'^(\w+)\s*[:\(]?\s*([^)]+)?[\)]?\s*$', stripped)
            if param_match and not stripped.startswith(' '):
                if current_param:
                    params[current_param] = ' '.join(current_content).strip()
                current_param = param_match.group(1)
                current_content = []
            elif current_param and stripped:
                current_content.append(stripped)
            i += 1
        elif current_section == "returns":
            if stripped and not stripped.startswith('-'):
                returns += stripped + " "
            i += 1
        else:
            i += 1
    
    if current_param:
        params[current_param] = ' '.join(current_content).strip()
    
    description = '\n'.join(description_lines).strip()
    return description, params, returns.strip(), other_sections


def extract_function_info(node: ast.FunctionDef | ast.AsyncFunctionDef, source_lines: List[str]) -> FunctionInfo:
    """Extract information from a function definition node."""
    decorators = []
    is_property = False
    is_classmethod = False
    is_staticmethod = False
    
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name):
            dec_name = decorator.id
            decorators.append(f"@{dec_name}")
            if dec_name == "property":
                is_property = True
            elif dec_name == "classmethod":
                is_classmethod = True
            elif dec_name == "staticmethod":
                is_staticmethod = True
        elif isinstance(decorator, ast.Attribute):
            decorators.append(f"@{ast.unparse(decorator)}")
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                decorators.append(f"@{decorator.func.id}(...)")
    
    # Get docstring
    docstring = ast.get_docstring(node) or ""
    description, param_docs, returns_doc, _ = parse_docstring(docstring)
    
    # Build parameter list
    parameters = []
    args = node.args
    
    # Get defaults alignment
    num_defaults = len(args.defaults)
    num_args = len(args.args)
    default_offset = num_args - num_defaults
    
    for i, arg in enumerate(args.args):
        if arg.arg == 'self' or arg.arg == 'cls':
            continue
        
        type_hint = get_type_annotation_str(arg.annotation) if arg.annotation else ""
        
        default = None
        default_idx = i - default_offset
        if default_idx >= 0 and default_idx < len(args.defaults):
            default = ast.unparse(args.defaults[default_idx]) if hasattr(ast, 'unparse') else "..."
        
        param_description = param_docs.get(arg.arg, "")
        
        parameters.append(ParameterInfo(
            name=arg.arg,
            type_hint=type_hint,
            default=default,
            description=param_description
        ))
    
    # Handle *args and **kwargs
    if args.vararg:
        parameters.append(ParameterInfo(
            name=f"*{args.vararg.arg}",
            type_hint=get_type_annotation_str(args.vararg.annotation) if args.vararg.annotation else "",
            default=None,
            description=param_docs.get(args.vararg.arg, "")
        ))
    
    if args.kwarg:
        parameters.append(ParameterInfo(
            name=f"**{args.kwarg.arg}",
            type_hint=get_type_annotation_str(args.kwarg.annotation) if args.kwarg.annotation else "",
            default=None,
            description=param_docs.get(args.kwarg.arg, "")
        ))
    
    # Build signature
    param_strs = []
    for p in parameters:
        s = p.name
        if p.type_hint:
            s += f": {p.type_hint}"
        if p.default is not None:
            s += f" = {p.default}"
        param_strs.append(s)
    
    return_type = get_type_annotation_str(node.returns) if node.returns else ""
    signature = f"({', '.join(param_strs)})"
    if return_type:
        signature += f" -> {return_type}"
    
    return FunctionInfo(
        name=node.name,
        signature=signature,
        docstring=description,
        parameters=parameters,
        returns=returns_doc,
        return_type=return_type,
        decorators=decorators,
        is_property=is_property,
        is_classmethod=is_classmethod,
        is_staticmethod=is_staticmethod,
        line_number=node.lineno
    )


def extract_class_info(node: ast.ClassDef, source_lines: List[str]) -> ClassInfo:
    """Extract information from a class definition node."""
    decorators = []
    is_dataclass = False
    
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name):
            dec_name = decorator.id
            decorators.append(f"@{dec_name}")
            if dec_name == "dataclass":
                is_dataclass = True
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                dec_name = decorator.func.id
                decorators.append(f"@{dec_name}(...)")
                if dec_name == "dataclass":
                    is_dataclass = True
    
    bases = [get_type_annotation_str(base) for base in node.bases]
    docstring = ast.get_docstring(node) or ""
    
    methods = []
    class_variables = {}
    
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not item.name.startswith('_') or item.name in ('__init__', '__call__', '__enter__', '__exit__'):
                func_info = extract_function_info(item, source_lines)
                func_info.is_method = True
                methods.append(func_info)
        elif isinstance(item, ast.AnnAssign):
            if isinstance(item.target, ast.Name):
                var_name = item.target.id
                var_type = get_type_annotation_str(item.annotation) if item.annotation else ""
                default = ""
                if item.value:
                    default = ast.unparse(item.value) if hasattr(ast, 'unparse') else "..."
                class_variables[var_name] = f"{var_type}" + (f" = {default}" if default else "")
    
    return ClassInfo(
        name=node.name,
        docstring=docstring,
        bases=bases,
        methods=methods,
        class_variables=class_variables,
        is_dataclass=is_dataclass,
        decorators=decorators,
        line_number=node.lineno
    )


def parse_module(filepath: Path) -> Optional[ModuleInfo]:
    """Parse a Python module and extract all documentation."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
            source_lines = source.split('\n')
        
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"  Warning: Could not parse {filepath}: {e}")
        return None
    
    module_docstring = ast.get_docstring(tree) or ""
    
    classes = []
    functions = []
    constants = {}
    imports = []
    
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            if not node.name.startswith('_'):
                classes.append(extract_class_info(node, source_lines))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith('_'):
                functions.append(extract_function_info(node, source_lines))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    value = ast.unparse(node.value) if hasattr(ast, 'unparse') else "..."
                    constants[target.id] = value
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            else:
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
    
    rel_path = filepath.relative_to(SRC_DIR)
    module_name = str(rel_path).replace('/', '.').replace('.py', '')
    
    return ModuleInfo(
        name=module_name,
        path=str(rel_path),
        docstring=module_docstring,
        classes=classes,
        functions=functions,
        constants=constants,
        imports=imports
    )


def escape_mdx(text: str) -> str:
    """Escape special characters for MDX."""
    if not text:
        return ""
    # Escape curly braces which are special in MDX
    text = text.replace('{', '\\{').replace('}', '\\}')
    # Escape angle brackets
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    return text


def generate_class_mdx(cls: ClassInfo, module_name: str) -> str:
    """Generate MDX content for a class."""
    lines = []
    
    # Class header
    decorator_str = '\n'.join(cls.decorators) + '\n' if cls.decorators else ''
    bases_str = f"({', '.join(cls.bases)})" if cls.bases else ""
    
    badge = ""
    if cls.is_dataclass:
        badge = '<span class="badge">dataclass</span>'
    
    lines.append(f"\n### {cls.name} {badge}\n")
    
    if cls.docstring:
        lines.append(escape_mdx(cls.docstring))
        lines.append("")
    
    # Class signature
    lines.append("```python")
    lines.append(f"{decorator_str}class {cls.name}{bases_str}:")
    lines.append("```")
    lines.append("")
    
    # Class variables / Fields (for dataclasses)
    if cls.class_variables:
        lines.append("#### Fields\n")
        lines.append("| Field | Type |")
        lines.append("|-------|------|")
        for var_name, var_info in cls.class_variables.items():
            lines.append(f"| `{var_name}` | `{escape_mdx(var_info)}` |")
        lines.append("")
    
    # Methods
    public_methods = [m for m in cls.methods if not m.name.startswith('_') or m.name == '__init__']
    if public_methods:
        lines.append("#### Methods\n")
        
        for method in public_methods:
            method_badge = ""
            if method.is_property:
                method_badge = " `property`"
            elif method.is_classmethod:
                method_badge = " `classmethod`"
            elif method.is_staticmethod:
                method_badge = " `staticmethod`"
            
            lines.append(f"##### `{method.name}`{method_badge}\n")
            
            if method.docstring:
                lines.append(escape_mdx(method.docstring))
                lines.append("")
            
            lines.append("```python")
            lines.append(f"def {method.name}{method.signature}")
            lines.append("```")
            
            if method.parameters:
                lines.append("\n**Parameters:**\n")
                for param in method.parameters:
                    type_str = f" (`{param.type_hint}`)" if param.type_hint else ""
                    default_str = f" — default: `{param.default}`" if param.default else ""
                    desc = f" — {escape_mdx(param.description)}" if param.description else ""
                    lines.append(f"- `{param.name}`{type_str}{default_str}{desc}")
                lines.append("")
            
            if method.returns:
                lines.append(f"**Returns:** {escape_mdx(method.returns)}\n")
            
            lines.append("---\n")
    
    return '\n'.join(lines)


def generate_function_mdx(func: FunctionInfo) -> str:
    """Generate MDX content for a standalone function."""
    lines = []
    
    lines.append(f"\n### `{func.name}`\n")
    
    if func.docstring:
        lines.append(escape_mdx(func.docstring))
        lines.append("")
    
    # Signature
    lines.append("```python")
    dec_str = '\n'.join(func.decorators) + '\n' if func.decorators else ''
    lines.append(f"{dec_str}def {func.name}{func.signature}")
    lines.append("```")
    lines.append("")
    
    if func.parameters:
        lines.append("**Parameters:**\n")
        for param in func.parameters:
            type_str = f" (`{param.type_hint}`)" if param.type_hint else ""
            default_str = f" — default: `{param.default}`" if param.default else ""
            desc = f" — {escape_mdx(param.description)}" if param.description else ""
            lines.append(f"- `{param.name}`{type_str}{default_str}{desc}")
        lines.append("")
    
    if func.returns:
        lines.append(f"**Returns:** {escape_mdx(func.returns)}\n")
    
    return '\n'.join(lines)


def generate_module_mdx(module: ModuleInfo, order: int) -> str:
    """Generate complete MDX file content for a module."""
    # Clean module name for display
    display_name = module.name.split('.')[-1].replace('_', ' ').title()
    parent_module = module.name.split('.')[0] if '.' in module.name else ""
    
    lines = []
    
    # Frontmatter
    lines.append("---")
    lines.append(f'title: "{display_name}"')
    lines.append(f'description: "API reference for great_silence.{module.name}"')
    lines.append(f"sidebar:")
    lines.append(f"  order: {order}")
    lines.append("---")
    lines.append("")
    
    # Module description
    lines.append(f"# {display_name}\n")
    lines.append(f"**Module:** `great_silence.{module.name}`\n")
    
    if module.docstring:
        lines.append(escape_mdx(module.docstring))
        lines.append("")
    
    # Import statement
    lines.append("```python")
    lines.append(f"from great_silence.{module.name} import ...")
    lines.append("```")
    lines.append("")
    
    # Constants
    if module.constants:
        lines.append("## Constants\n")
        lines.append("| Constant | Value |")
        lines.append("|----------|-------|")
        for name, value in module.constants.items():
            lines.append(f"| `{name}` | `{escape_mdx(value[:50])}{'...' if len(value) > 50 else ''}` |")
        lines.append("")
    
    # Classes
    if module.classes:
        lines.append("## Classes\n")
        for cls in module.classes:
            lines.append(generate_class_mdx(cls, module.name))
    
    # Functions
    if module.functions:
        lines.append("## Functions\n")
        for func in module.functions:
            lines.append(generate_function_mdx(func))
    
    return '\n'.join(lines)


def collect_modules(src_dir: Path) -> Dict[str, List[ModuleInfo]]:
    """Collect all modules organized by package."""
    packages: Dict[str, List[ModuleInfo]] = {}
    
    for py_file in src_dir.rglob("*.py"):
        if py_file.name.startswith('_') and py_file.name != '__init__.py':
            continue
        if '__pycache__' in str(py_file):
            continue
        
        # Determine package name
        rel_path = py_file.relative_to(src_dir)
        parts = list(rel_path.parts[:-1])
        
        if parts:
            package_name = parts[0]
        else:
            package_name = "core"
        
        print(f"  Parsing: {rel_path}")
        module = parse_module(py_file)
        
        if module and (module.classes or module.functions or module.constants):
            if package_name not in packages:
                packages[package_name] = []
            packages[package_name].append(module)
    
    return packages


def generate_index_page(packages: Dict[str, List[ModuleInfo]]) -> str:
    """Generate the API index page."""
    lines = []
    
    lines.append("---")
    lines.append('title: "API Reference"')
    lines.append('description: "Complete API documentation for Great Silence"')
    lines.append("sidebar:")
    lines.append("  order: 0")
    lines.append("---")
    lines.append("")
    lines.append("import { Card, CardGrid } from '@astrojs/starlight/components';")
    lines.append("")
    lines.append("# API Reference\n")
    lines.append("Complete API documentation for the Great Silence simulation framework.\n")
    lines.append("")
    lines.append("<CardGrid>")
    
    package_descriptions = {
        "galaxy": "Galactic structure, stellar populations, and dynamics",
        "civilization": "Civilization emergence, expansion, and extinction models",
        "astrophysics": "Astrophysical hazards including supernovae and GRBs",
        "simulation": "Core simulation engine and Monte Carlo framework",
        "config": "Configuration dataclasses and parameter management",
        "visualization": "Plotting and 3D visualization tools",
        "utils": "Utility functions and spatial indexing",
        "webapp": "NiceGUI web application interface",
        "notebook": "Jupyter notebook integration helpers",
    }
    
    for package_name in sorted(packages.keys()):
        modules = packages[package_name]
        desc = package_descriptions.get(package_name, f"The {package_name} module")
        num_classes = sum(len(m.classes) for m in modules)
        num_funcs = sum(len(m.functions) for m in modules)
        
        lines.append(f'  <Card title="{package_name.title()}" icon="document">')
        lines.append(f"    {desc}. Contains {num_classes} classes and {num_funcs} functions.")
        lines.append("  </Card>")
    
    lines.append("</CardGrid>")
    lines.append("")
    
    # Quick links
    lines.append("## Quick Links\n")
    lines.append("### Core Classes\n")
    lines.append("- [`GalaxySimulation`](/great_silence/api/simulation-engine/#galaxysimulation) — Main simulation orchestrator")
    lines.append("- [`SimulationConfig`](/great_silence/api/config-parameters/#simulationconfig) — Configuration container")
    lines.append("- [`GalaxyModel`](/great_silence/api/galaxy-structure/#galaxymodel) — Galaxy structure model")
    lines.append("- [`CivilizationState`](/great_silence/api/simulation-engine/#civilizationstate) — Civilization state tracking")
    lines.append("")
    
    return '\n'.join(lines)


def main():
    """Main entry point for the API documentation generator."""
    print("=" * 60)
    print("Great Silence API Documentation Generator")
    print("=" * 60)
    print(f"\nSource directory: {SRC_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print("")
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Collect all modules
    print("Collecting modules...")
    packages = collect_modules(SRC_DIR)
    
    total_modules = sum(len(mods) for mods in packages.values())
    total_classes = sum(len(m.classes) for mods in packages.values() for m in mods)
    total_functions = sum(len(m.functions) for mods in packages.values() for m in mods)
    
    print(f"\nFound {total_modules} modules with {total_classes} classes and {total_functions} functions")
    print("")
    
    # Generate index page
    print("Generating index page...")
    index_content = generate_index_page(packages)
    index_path = OUTPUT_DIR / "index.mdx"
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_content)
    print(f"  Created: {index_path.relative_to(PROJECT_ROOT)}")
    
    # Generate module pages
    print("\nGenerating module pages...")
    order = 1
    
    for package_name in sorted(packages.keys()):
        modules = packages[package_name]
        
        for module in sorted(modules, key=lambda m: m.name):
            # Create filename from module path
            filename = module.name.replace('.', '-').replace('_', '-') + ".mdx"
            if filename.startswith(f"{package_name}-"):
                pass
            else:
                filename = f"{package_name}-{filename}"
            
            output_path = OUTPUT_DIR / filename
            content = generate_module_mdx(module, order)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"  Created: {output_path.relative_to(PROJECT_ROOT)}")
            order += 1
    
    print("")
    print("=" * 60)
    print(f"Documentation generated successfully!")
    print(f"  Total files: {order}")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
