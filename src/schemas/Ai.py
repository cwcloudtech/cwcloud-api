from typing import Optional

from pydantic import BaseModel

class PromptSettingsSchema(BaseModel):
    max_length: Optional[int]
    num_return_sequences: Optional[int] = None
    no_repeat_ngram_size: Optional[int] = None
    num_beans: Optional[int] = None
    early_stopping: Optional[bool] = True
    do_sample: Optional[bool] = True
    skip_special_tokens: Optional[bool] = True
    truncate: Optional[bool] = True
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    temperature: Optional[float] = None

class PromptSchema(BaseModel):
    model: str
    message: str
    settings: Optional[PromptSettingsSchema] = None
