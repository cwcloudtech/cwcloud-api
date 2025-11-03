from fastapi import Request

async def get_raw_body(request: Request) -> str:
    return (await request.body()).decode("utf-8")
