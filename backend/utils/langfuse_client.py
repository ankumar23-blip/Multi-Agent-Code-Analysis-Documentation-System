import os
# Placeholder for langfuse integration
LANGFUSE_KEY = os.getenv('LANGFUSE_API_KEY')

def track_event(name, payload):
    # In production: call Langfuse SDK or API to log events/traces
    print(f'[langfuse] event={name} payload={payload}')
