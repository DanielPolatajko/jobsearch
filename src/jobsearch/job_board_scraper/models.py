from pydantic import BaseModel
from enum import IntEnum, StrEnum


class LinkedInExperienceLevel(IntEnum):
    ASSOCIATE = 3
    MID_SENIOR = 4


class LinkedInIndustry(IntEnum):
    CLIMATE_DATA_AND_ANALYTICS = 3252
    ENVIRONMENTAL_SERVICES = 86


class LinkedInJobType(StrEnum):
    FULL_TIME = "F"


class LinkedInJobSearchParameters(BaseModel):
    location: str
    job_title: str
    industries: list[LinkedInIndustry]
    experience_level: LinkedInExperienceLevel
    job_type: str
