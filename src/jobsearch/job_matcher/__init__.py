"""
Job matcher module for evaluating job listings against candidate profiles
"""

from jobsearch.job_matcher.base import BaseJobMatcher
from jobsearch.job_matcher.claude_matcher import ClaudeJobMatcher
from jobsearch.job_matcher.huggingface_matcher import HuggingFaceJobMatcher

__all__ = [
    'BaseJobMatcher',
    'ClaudeJobMatcher',
    'HuggingFaceJobMatcher'
]
