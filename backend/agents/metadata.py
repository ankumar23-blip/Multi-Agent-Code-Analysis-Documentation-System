import asyncio
async def run(job_id, payload):
    print(f'[metadata] job={job_id} extracting file importance & metadata')
    await asyncio.sleep(1)
    # compute file sizes, import graphs, language heuristics, and mark 'important' files
    return {'status':'ok'}
