import asyncio
async def run(job_id, payload):
    print(f'[summarizer] job={job_id} generating embeddings & summaries')
    await asyncio.sleep(1)
    # call LLM / embeddings provider and store vectors in pgvector
    return {'status':'ok'}
