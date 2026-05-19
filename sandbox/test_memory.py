from deer.core.agent import DeterministicAgent
from deer.schema.io import AgentInput, Struct
from deer.tools.registry import default_registry
from deer.tools.decorators import tool

from deer.drivers.gemini_driver import GeminiDriver

from dotenv import load_dotenv

load_dotenv()


driver = GeminiDriver(model_name="gemini-3.1-flash-lite")


class MathTools:
    @tool(
        name="circle_area",
        description="Calculates the area of a circle.",
    )
    def circle_area(
        params: Struct(radius=int | float),
    ) -> Struct(area=int | float):
        radius = params["radius"]
        area = 3.141592653589793 * radius**2
        return {
            "area": area,
        }


registry = default_registry()
registry.register([MathTools()])


agent = DeterministicAgent(
    driver=driver,
    registry=registry,
)

while True:
    msg = input(">>> ")
    if msg == "exit":
        break

    if msg:
        user_input = AgentInput(
            goal=msg,
            payload={
                "history": agent.history,
            },
        )
        output = agent.run(user_input)
        print(f"    {output.result}\n")
