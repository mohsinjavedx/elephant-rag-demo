from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChunkSchema(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    document_id: str
    chunk_index: int = Field(ge=0)
    raw_text: str = Field(min_length=1)
    normalized_text: str = Field(min_length=1)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(gt=0)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_provenance(self) -> "ChunkSchema":
        if self.page_end != self.page_start or self.char_end <= self.char_start:
            raise ValueError("Chunks must have a valid single-page source span")
        if len(self.raw_text) != self.char_end - self.char_start:
            raise ValueError("Raw chunk length must equal its source span length")
        return self
