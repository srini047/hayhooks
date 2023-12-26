from typing import ForwardRef

from fastapi.responses import JSONResponse
from pydantic import BaseModel, create_model

from hayhooks.server import app
from hayhooks.server.pipelines import registry


class PipelineDefinition(BaseModel):
    name: str
    source_code: str


@app.post("/serve")
async def serve(pipeline_def: PipelineDefinition):
    pipe = registry.add(pipeline_def.name, pipeline_def.source_code)

    request_model = {}
    for component_name, inputs in pipe.inputs().items():
        # Inputs have this form:
        # {
        #     'first_addition': { <-- Component Name
        #         'value': {'type': <class 'int'>, 'is_mandatory': True}, <-- Input
        #         'add': {'type': typing.Optional[int], 'is_mandatory': False}, <-- Input
        #     },
        #     'second_addition': {'add': {'type': typing.Optional[int], 'is_mandatory': False}},
        # }
        component_model = {}
        for name, typedef in inputs.items():
            component_model[name] = (typedef["type"], ...)
        request_model[component_name] = (create_model('ComponentParams', **component_model), ...)

    PipelineRunRequest = create_model('PipelineRunRequest', **request_model)

    response_model = {}
    for component_name, outputs in pipe.outputs().items():
        # Outputs have this form:
        # {
        #   'second_addition': { <-- Component Name
        #       'result': {'type': "<class 'int'>"}  <-- Output
        #   },
        # }
        component_model = {}
        for name, typedef in outputs.items():
            component_model[name] = (typedef["type"], ...)
        response_model[component_name] = (create_model('ComponentParams', **component_model), ...)

    PipelineRunResponse = create_model('PipelineRunResponse', **response_model)

    async def pipeline_run(pipeline_run_req: PipelineRunRequest) -> JSONResponse:  # type: ignore
        output = pipe.run(data=pipeline_run_req.dict())
        return JSONResponse(PipelineRunResponse(**output).model_dump(), status_code=200)

    app.add_api_route(
        path=f"/{pipeline_def.name}",
        endpoint=pipeline_run,
        methods=["POST"],
        name=pipeline_def.name,
        response_model=PipelineRunResponse,
    )
    app.openapi_schema = None
    app.setup()

    return {"pipeline_name": "foo"}