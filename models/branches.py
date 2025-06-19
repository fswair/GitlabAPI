from typing import Optional
from pydantic import BaseModel
from models.repos import RepositoryItem
from gitlab.v4.objects import ProjectBranch

class Branch(BaseModel):
    """
    Class to represent a branch in a GitLab repository.
    """
    name: str
    branch: Optional[ProjectBranch] = None
    contents: list[RepositoryItem] = []
    
    model_config = {
        "arbitrary_types_allowed": True
    }

class BranchManager(BaseModel):
    """
    Class to manage branches in a GitLab repository.
    """
    main: Optional[Branch]
    has_more: bool = False
    other_branches: list[Branch] = []
    
    model_config = {
        "arbitrary_types_allowed": True
    }