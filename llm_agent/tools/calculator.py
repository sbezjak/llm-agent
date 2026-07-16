import ast
import operator

from .base import Tool

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARYOPS = {ast.USub: operator.neg, ast.UAdd: operator.pos}


def _eval_node(node: ast.expr) -> int | float:
    match node:
        case ast.Constant(value=int() | float() as value):
            return value
        case ast.BinOp(left=left, op=op, right=right) if type(op) in _BINOPS:
            return _BINOPS[type(op)](_eval_node(left), _eval_node(right))
        case ast.UnaryOp(op=op, operand=operand) if type(op) in _UNARYOPS:
            return _UNARYOPS[type(op)](_eval_node(operand))
    raise ValueError(f"unsupported expression element: {ast.dump(node)}")


async def calculate(expression: str) -> str:
    """Evaluate an arithmetic expression via the AST, never eval(). Raises on
    bad input; the agent loop converts raised errors into error observations."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"not a valid arithmetic expression: {expression!r}") from exc
    return str(_eval_node(tree.body))


CALCULATOR = Tool(
    name="calculator",
    description="Evaluate an arithmetic expression and return the numeric result.",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Arithmetic expression, e.g. '2 * (3 + 4)'",
            }
        },
        "required": ["expression"],
    },
    handler=calculate,
)
