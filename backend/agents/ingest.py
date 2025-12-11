import asyncio
async def run(job_id, payload):
    # placeholder: clone the repo, find files, and split into documents
    repo_url = payload.get('repo_url')
    print(f'[ingest] job={job_id} cloning {repo_url}')
    await asyncio.sleep(1)  # simulate work
    # save artifacts to DB or storage (left as exercise)
    return {'status':'ok'}
