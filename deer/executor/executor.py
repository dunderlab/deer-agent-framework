import json
import math
from typing import Any, Dict

from deer.schema.io import AgentInput, AgentOutput, StepTrace
from deer.schema.plan import Plan
from deer.tracing.store import TraceStore
from deer.tools.registry import ToolRegistry


class Executor:
    def __init__(self, registry: ToolRegistry, trace_store: TraceStore) -> None:
        self.registry = registry
        self.trace_store = trace_store

    def execute(self, plan: Plan, agent_input: AgentInput) -> AgentOutput:
        self.trace_store.reset()
        context: Dict[str, Any] = {}
        last_output: Any = None

        for step in plan.steps:
            value = self._resolve_input(step.input_from, step.id, agent_input, context)

            try:
                if step.logic is not None:
                    output = self._execute_logic(
                        logic=step.logic,
                        input_value=value,
                        params=step.params or {},
                        context=context,
                    )
                    trace_tool = "logic"
                else:
                    if step.tool is None:
                        raise ValueError(
                            f"Step '{step.id}' must define either 'tool' or 'logic'."
                        )

                    output = self._execute_tool(
                        tool_name=step.tool,
                        input_value=value,
                        params=step.params or {},
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

    def _resolve_input(
        self,
        input_from: str | None,
        step_id: str,
        agent_input: AgentInput,
        context: Dict[str, Any],
    ) -> Any:
        if input_from is None:
            return agent_input.payload

        if input_from not in context:
            raise ValueError(
                f"Unresolved dependency: '{input_from}' required by step '{step_id}'."
            )

        return context[input_from]

    def _execute_tool(
        self,
        tool_name: str,
        input_value: Any,
        params: Dict[str, Any],
    ) -> Any:
        tool = self.registry.get(tool_name)
        valid_input = tool.validate_input(input_value)
        output = tool.run(valid_input, params=params)
        return tool.validate_output(output)

    def _execute_logic(
        self,
        logic: str,
        input_value: Any,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        safe_globals = {
            "__builtins__": {},
            "pi": math.pi,
            "abs": abs,
            "min": min,
            "max": max,
            "round": round,
            "str": str,
            "int": int,
            "float": float,
            "len": len,
        }

        local_scope = self._build_logic_scope(
            input_value=input_value,
            params=params,
            context=context,
        )

        logic = self.normalize_logic(logic)
        try:
            exec(logic, safe_globals, local_scope)
        except Exception as e:
            raise ValueError(f"Error executing logic step: {e}")

        if "result" not in local_scope:
            raise ValueError("Logic step must assign a value to 'result'.")

        return local_scope["result"]

    def _build_logic_scope(
        self,
        input_value: Any,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        local_scope: Dict[str, Any] = {
            "input": input_value,
            "params": params,
            "context": context,
        }

        if isinstance(input_value, dict):
            for key, value in input_value.items():
                if self._is_safe_variable_name(key):
                    local_scope[key] = value

        for key, value in params.items():
            if self._is_safe_variable_name(key):
                local_scope[key] = value

        return local_scope

    def _is_safe_variable_name(self, name: str) -> bool:
        return name.isidentifier() and not name.startswith("_")

    def normalize_logic(self, logic: str) -> str:
        logic = logic.strip()

        # multiline JSON escapes
        logic = logic.replace("\\n", "\n")

        # Caso: string completo serializado
        try:
            parsed = json.loads(logic)
            if isinstance(parsed, str):
                logic = parsed
        except Exception:
            pass

        # Caso: código Python contaminado con escaping JSON
        logic = logic.replace('\\"', '"')

        return logic
