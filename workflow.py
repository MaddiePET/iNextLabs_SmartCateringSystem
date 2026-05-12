from typing_extensions import Never
from agent_framework import WorkflowBuilder, WorkflowContext, executor

from app import generate_catering_plan


@executor(id="catering_pipeline")
async def catering_pipeline(
    message: str,
    ctx: WorkflowContext[Never, dict],
) -> None:
    result = await generate_catering_plan(message)
    await ctx.yield_output(result)


workflow = WorkflowBuilder(
    name="Smart Catering Workflow",
    start_executor=catering_pipeline,
).build()


async def run_catering_workflow(user_request: str, progress_callback=None):
    if progress_callback:
        return await generate_catering_plan(user_request, progress_callback)

    events = await workflow.run(user_request)
    outputs = events.get_outputs()

    return outputs[0] if outputs else {}