import asyncio
async def run(job_id, payload):
    print(f'[docgen] job={job_id} generating documentation artifacts')
    await asyncio.sleep(1)
    return {'status':'ok'}

async def get_mermaid(job_id):
    # return a sample mermaid diagram describing the pipeline
    return '''
flowchart LR
    A[Repository] --> B[Preprocessing]
    B --> C{Important files}
    C --> D[Summarizer]
    D --> E[Doc Generator]
    E --> F[Output Docs]
    '''
