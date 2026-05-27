from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

import pytest

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "core" / "pipeline.py"
CALCULATIONS = ROOT / "core" / "calculations.py"
RUN_LOGGING = ROOT / "core" / "run_logging.py"

ECONOMIST_ENTRYPOINTS = {"run_economist_step", "run_economist_code"}
RUN_LOGGING_GIT_SHA_EXCEPTION = (
    "core/run_logging.py",
    "current_code_version_metadata",
    "subprocess.run",
)

BUILTIN_CODE_EXECUTION = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "builtins.eval",
    "builtins.exec",
    "builtins.compile",
    "builtins.__import__",
}
SHELL_EXECUTION_CALLS = {
    "os.system",
    "os.popen",
    "os.spawnl",
    "os.spawnle",
    "os.spawnlp",
    "os.spawnlpe",
    "os.spawnv",
    "os.spawnve",
    "os.spawnvp",
    "os.spawnvpe",
    "commands.getoutput",
    "commands.getstatusoutput",
}
DYNAMIC_PYTHON_EXECUTION_CALLS = {
    "runpy.run_path",
    "runpy.run_module",
    "importlib.import_module",
    "importlib.util.spec_from_file_location",
    "importlib.machinery.SourceFileLoader",
    "py_compile.compile",
    "compileall.compile_file",
    "compileall.compile_dir",
    "code.InteractiveConsole",
    "code.InteractiveInterpreter",
    "codeop.compile_command",
}
MODEL_CODE_EXECUTION_HELPERS = {
    "execute_code",
    "execute_python",
    "exec_code",
    "run_python",
}

Finding = tuple[str, str, int, str, str]


def parse_module(path: Path) -> ast.Module:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        pytest.fail(f"Syntax error in {path.relative_to(ROOT)}: {exc}")


def module_functions(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }


def import_aliases(nodes: Iterable[ast.AST]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in nodes:
        scope = node.body if isinstance(node, ast.Module) else ast.walk(node)
        for item in scope:
            if isinstance(item, ast.Import):
                for alias in item.names:
                    local = alias.asname or alias.name.split(".", 1)[0]
                    target = alias.name if alias.asname else alias.name.split(".", 1)[0]
                    aliases[local] = target
            elif isinstance(item, ast.ImportFrom):
                module = "." * item.level + (item.module or "")
                for alias in item.names:
                    local = alias.asname or alias.name
                    aliases[local] = f"{module}.{alias.name}" if module else alias.name
    return aliases


def attribute_chain(node: ast.AST) -> list[str]:
    chain: list[str] = []
    while isinstance(node, ast.Attribute):
        chain.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        chain.append(node.id)
    return list(reversed(chain))


def call_name(node: ast.AST, aliases: dict[str, str]) -> str | None:
    chain = attribute_chain(node)
    if not chain:
        return None
    if chain[0] in aliases:
        chain = aliases[chain[0]].split(".") + chain[1:]
    return ".".join(part for part in chain if part)


def called_local_functions(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    names: set[str],
) -> set[str]:
    return {
        item.func.id
        for item in ast.walk(node)
        if isinstance(item, ast.Call)
        and isinstance(item.func, ast.Name)
        and item.func.id in names
    }


def reachable_functions(
    functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
    entrypoints: set[str],
) -> set[str]:
    missing = entrypoints - set(functions)
    assert not missing, f"Missing Economist entrypoints: {sorted(missing)}"

    reachable: set[str] = set()
    pending = list(entrypoints)
    names = set(functions)
    while pending:
        name = pending.pop()
        if name in reachable:
            continue
        reachable.add(name)
        pending.extend(called_local_functions(functions[name], names) - reachable)
    return reachable


def imports_subprocess(node: ast.AST) -> bool:
    if isinstance(node, ast.Import):
        return any(alias.name == "subprocess" for alias in node.names)
    return isinstance(node, ast.ImportFrom) and node.module == "subprocess"


def literal_true(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def call_violation(name: str, node: ast.Call) -> tuple[str, str] | None:
    if name in BUILTIN_CODE_EXECUTION:
        return name, "dynamic Python code execution primitive"
    if name == "subprocess" or name.startswith("subprocess."):
        return name, "subprocess call"
    if name in SHELL_EXECUTION_CALLS:
        return name, "shell execution primitive"
    if name in DYNAMIC_PYTHON_EXECUTION_CALLS:
        return name, "dynamic Python module/script execution primitive"
    if name.rsplit(".", 1)[-1] in MODEL_CODE_EXECUTION_HELPERS:
        return name, "model-generated Python execution helper"
    if any(keyword.arg == "shell" and literal_true(keyword.value) for keyword in node.keywords):
        return name, "shell=True call"
    return None


def code_execution_findings(
    path: Path,
    function_name: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    module_aliases: dict[str, str],
) -> list[Finding]:
    aliases = {**module_aliases, **import_aliases([node])}
    rel_path = path.relative_to(ROOT).as_posix()
    findings: list[Finding] = []
    for item in ast.walk(node):
        if isinstance(item, ast.Import | ast.ImportFrom) and imports_subprocess(item):
            findings.append(
                (
                    rel_path,
                    function_name,
                    item.lineno,
                    "import subprocess",
                    "subprocess import inside guarded code",
                )
            )
        if not isinstance(item, ast.Call):
            continue
        name = call_name(item.func, aliases)
        violation = call_violation(name, item) if name else None
        if violation:
            findings.append((rel_path, function_name, item.lineno, *violation))
    return findings


def format_findings(findings: list[Finding]) -> str:
    return "\n".join(
        f"{path}:{line} in {function}: {call} ({reason})"
        for path, function, line, call, reason in findings
    )


def literal_str_sequence(node: ast.AST) -> list[str] | None:
    if not isinstance(node, ast.List | ast.Tuple):
        return None
    values: list[str] = []
    for item in node.elts:
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
            return None
        values.append(item.value)
    return values


def findings_for_functions(path: Path, function_names: Iterable[str] | None = None) -> list[Finding]:
    tree = parse_module(path)
    functions = module_functions(tree)
    names = sorted(function_names or functions)
    aliases = import_aliases([tree])
    return [
        finding
        for name in names
        for finding in code_execution_findings(path, name, functions[name], aliases)
    ]


def test_economist_call_path_has_no_code_execution_primitives() -> None:
    tree = parse_module(PIPELINE)
    functions = module_functions(tree)
    reachable = reachable_functions(functions, ECONOMIST_ENTRYPOINTS)
    aliases = import_aliases([tree])
    findings = [
        finding
        for name in sorted(reachable)
        for finding in code_execution_findings(PIPELINE, name, functions[name], aliases)
    ]

    assert not findings, (
        "Economist-reachable code execution primitives found:\n"
        + format_findings(findings)
    )


def test_allowed_calculation_helpers_have_no_code_execution_primitives() -> None:
    findings = findings_for_functions(CALCULATIONS)
    assert not findings, (
        "Allowed calculation helpers must stay deterministic:\n"
        + format_findings(findings)
    )


def test_non_economist_subprocess_exception_is_narrow_git_sha_metadata() -> None:
    findings = findings_for_functions(RUN_LOGGING)
    assert {(path, function, call) for path, function, _line, call, _reason in findings} == {
        RUN_LOGGING_GIT_SHA_EXCEPTION
    }, (
        "Only best-effort non-Economist git SHA metadata may use subprocess:\n"
        + format_findings(findings)
    )

    tree = parse_module(RUN_LOGGING)
    git_sha_function = module_functions(tree)["current_code_version_metadata"]
    aliases = {**import_aliases([tree]), **import_aliases([git_sha_function])}
    subprocess_calls = [
        item
        for item in ast.walk(git_sha_function)
        if isinstance(item, ast.Call) and call_name(item.func, aliases) == "subprocess.run"
    ]

    assert len(subprocess_calls) == 1
    assert literal_str_sequence(subprocess_calls[0].args[0]) == [
        "git",
        "rev-parse",
        "HEAD",
    ]
    assert not any(
        keyword.arg == "shell" and literal_true(keyword.value)
        for keyword in subprocess_calls[0].keywords
    )
