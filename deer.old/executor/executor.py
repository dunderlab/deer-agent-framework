import logging
import re
from typing import Any, Dict

from deer.schema.io import AgentOutput, StepTrace
from deer.schema.plan import Plan
from deer.tracing.store import TraceStore
from deer.tools.registry import ToolRegistry
from .logic import evaluate_logic

logger = logging.getLogger("DEER")


class Executor:
    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry
        self.trace_store = TraceStore()

    def execute(self, plan: Plan, payload: {}) -> AgentOutput:
        self.trace_store.reset()
        context: Dict[str, Any] = {}
        last_output: Any = None

        for step in plan.steps:
            value = self.resolve_input(step.input_from, step.id, payload, context)
            logger.debug(f"Executing step {step.id} with input '{step.input_from}'")

            try:
                if step.logic is not None:
                    output = self.execute_logic(
                        logic=step.logic,
                        input_value=value,
                        params=step.params or {},
                        context=context,
                    )
                    trace_tool = "logic"

                if step.tool is not None:
                    params = self.resolve_params(step.params or {}, value, context)
                    output = self.execute_tool(
                        tool_name=step.tool,
                        params=params,
                    )
                    trace_tool = step.tool

                context[step.id] = output
                last_output = output

                self.trace_store.append(
                    StepTrace(
                        step_id=step.id,
                        tool=trace_tool,
                        input=value,
                        output=output,
                    )
                )
            except Exception as ex:
                self.trace_store.append(
                    StepTrace(
                        step_id=step.id,
                        tool=step.tool or "logic",
                        input=value,
                        output=None,
                        error=str(ex),
                    )
                )
                raise

        return AgentOutput(result=last_output, trace=self.trace_store.get_trace())

    def resolve_input(
        self,
        input_from: str | None,
        step_id: str,
        payload: {},
        context: Dict[str, Any],
    ) -> Any:
        if input_from is None:
            return payload

        if input_from not in context:
            raise ValueError(
                f"Unresolved dependency: '{input_from}' required by step '{step_id}'."
            )

        output = context[input_from]

        # # Automatically unwrap single-key dictionaries to simplify logic and tool usage.
        # # This ensures 'input' refers directly to the value (e.g., file content)
        # # instead of the wrapper dictionary.
        # if isinstance(output, dict) and len(output) == 1:
        #     return next(iter(output.values()))

        return output

    def resolve_params(
        self,
        params: Dict[str, Any],
        input_value: Any,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Resolves placeholders like 'input' or step IDs in parameters."""
        resolved = {}
        for k, v in params.items():
            if v == "input":
                resolved[k] = input_value
            elif isinstance(v, str) and v in context:
                resolved[k] = context[v]
            else:
                resolved[k] = v
        return resolved

    def execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
    ) -> Any:
        tool = self.tool_registry.get(tool_name)
        input_params = tool.validate_input(params)
        output = tool.run(params=input_params)
        logger.info(f"Executed tool: {tool_name} with params: {input_params}")
        logger.debug(f"Tool {tool_name} output: {output}")
        return tool.validate_output(output)

    def execute_logic(
        self,
        logic: str,
        input_value: Any,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        # logic = self.fix_multiline_strings(logic)
        logger.debug(f"Executing logic: {logic}")
        return evaluate_logic(
            logic,
            input_value=input_value,
            params=params,
            context=context,
        )

    #
    # def fix_multiline_strings(self, code: str) -> str:
    #     pattern = r'=\s*"([^"\n]*\n(?:.*\n)*?.*?)"'
    #
    #     def replacer(match):
    #         content = match.group(1)
    #         return '= """' + content + '"""'
    #
    #     return re.sub(pattern, replacer, code, flags=re.MULTILINE)

    # def normalize_logic(self, logic: str) -> str:
    #     logic = logic.strip()
    #
    #     # multiline JSON escapes
    #     logic = logic.replace("\\n", "\n")
    #
    #     # Caso: string completo serializado
    #     try:
    #         parsed = json.loads(logic)
    #         if isinstance(parsed, str):
    #             logic = parsed
    #     except Exception:
    #         pass
    #
    #     # Caso: código Python contaminado con escaping JSON
    #     logic = logic.replace('\\"', '"')
    #
    #     return logic
