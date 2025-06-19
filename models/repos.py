from pydantic import BaseModel
from typing import Optional, Literal
from gitlab import Gitlab
from gitlab.v4.objects import Project

class RepositoryItem(BaseModel):
    """
    Represents an item in a GitLab repository.
    """
    id: Optional[str] = None
    name: Optional[str] = None
    path: Optional[str] = None
    mode: Optional[str] = None
    type: Literal["blob", "tree"] = "blob"
    
        
    self: Gitlab
    repo_name: str
    branch: str = "main"
    
    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "allow"
    }
    
    def tree(self) -> list["RepositoryItem"]:
        """
        Iterate over the items in the repository tree.
        Returns:
            list[RepositoryItem]: List of items in the repository tree, if item is a directory.
        """
        pass
    
    @property
    def is_dir(self) -> bool:
        """
        Check if the item is a directory.
        Returns:
            bool: True if the item is a directory, False otherwise.
        """
        return self.type == "tree"
    
    @property
    def is_file(self) -> bool:
        """
        Check if the item is a file.
        Returns:
            bool: True if the item is a file, False otherwise.
        """
        return self.type == "blob"

class CloneableProject(Project):
    """
    Represents a project that can be cloned.
    """
    full_name: str
    clone: Optional[callable] = None
    
    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "allow"
    }
    
    def clone(self, overwrite: bool = False, **kwargs) -> str:
        """
        Clone the repository using the provided parameters.
        
        :param overwrite: If True, overwrite existing files.
        :param kwargs: Additional parameters for cloning.
        :return: The clone command or URL.
        """
        pass


CloneableProject.clone