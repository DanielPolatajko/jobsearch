from pydantic import BaseModel, Field
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
    location: str = Field(
        description="The location to search for jobs in. This field must be provided."
    )
    job_title: str = Field(
        description="The job title to search for. This field must be provided."
    )
    industries: list[LinkedInIndustry] = Field(
        description="The industries to search for jobs in. The available industries are defined as follows: "
        + "\n".join(
            [f"{industry.name}: {industry.value}" for industry in LinkedInIndustry]
        )
        + "\nYou must provided only a list of numeric codes from those given here as the mapping values. This field must be provided."
    )
    experience_level: LinkedInExperienceLevel = Field(
        description="The experience level to search for jobs in. The available experience levels are defined as follows: "
        + "\n".join(
            [
                f"{experience_level.name}: {experience_level.value}"
                for experience_level in LinkedInExperienceLevel
            ]
        )
        + "\nYou must provided only a numeric code from those given here as the mapping values. This field must be provided."
    )
    job_type: LinkedInJobType = Field(
        description="The job type to search for. The available job types are defined as follows: "
        + "\n".join(
            [f"{job_type.name}: {job_type.value}" for job_type in LinkedInJobType]
        )
        + "\nYou must provided only a code from those given here as the mapping values. This field must be provided."
    )
