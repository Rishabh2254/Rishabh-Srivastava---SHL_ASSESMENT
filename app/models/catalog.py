"""Domain models for SHL catalog entries."""

from pydantic import BaseModel, Field, HttpUrl


class AssessmentRecord(BaseModel):
    name: str
    url: str
    description: str = ""
    test_type: str = ""
    test_type_codes: list[str] = Field(default_factory=list)
    duration: str = ""
    remote_support: str = ""
    adaptive_support: str = ""
    languages: list[str] = Field(default_factory=list)
    job_levels: list[str] = Field(default_factory=list)
    category: str = ""
    skills: list[str] = Field(default_factory=list)
    competencies: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: str = "individual_test"

    def embedding_text(self) -> str:
        parts = [
            self.name,
            self.description,
            self.test_type,
            self.category,
            " ".join(self.skills),
            " ".join(self.competencies),
            " ".join(self.keywords),
            " ".join(self.job_levels),
            " ".join(self.languages),
            self.duration,
        ]
        return " | ".join(p.strip() for p in parts if p and p.strip())

    def slug(self) -> str:
        return self.url.rstrip("/").split("/")[-1].lower()
