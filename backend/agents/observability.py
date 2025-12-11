import asyncio
async def run(job_id, payload):
    print(f'[observability] job={job_id} capturing traces and events')
    await asyncio.sleep(0.1)
    # send events to langfuse or other tracing endpoint
    return {'status':'ok'}
