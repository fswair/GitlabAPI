import base64
import os

from functools import partial
from pathlib import Path

from gitlab import Gitlab
from gitlab.v4.objects import Project

from models.branches import Branch, BranchManager
from models.repos import RepositoryItem, CloneableProject
from settings import settings


def can_clone(self: "GitLab", project: Project) -> CloneableProject:
    """
    Check if a project can be cloned.

    Args:
        project (Project): The GitLab project to check.

    Returns:
        Project: The project with the clone method attached.
    """
    setattr(project, 'clone', partial(self.clone_repo, full_name=project.path_with_namespace))
    return project


class GitLab(Gitlab):
    def __init__(self, url: str = None, token: str = None, warnings: bool = True, *args, **kwargs):
        self.settings = settings
        self.info = lambda *args, **kwargs: None if not warnings else print(*args, **kwargs)
        super().__init__(
            url=url or self.settings.gitlab_base_url,
            private_token=token or self.settings.gitlab_access_token,
        )
        self.auth()

    def can_iterate(self, item: RepositoryItem) -> RepositoryItem:
        """
        Check if the item can be iterated over (i.e., if it is a directory).

        Args:
            item (RepositoryItem): The item to check.

        Returns:
            RepositoryItem: The item itself if it can be iterated, otherwise None.
        """
        def tree(item: RepositoryItem) -> list[RepositoryItem]:
            """
            Iterate over the items in the repository tree.

            Returns:
                list[RepositoryItem]: List of items in the repository tree, if item is a directory.
            """
            if item.type == "tree":
                return [
                    self.can_iterate(
                        RepositoryItem(
                            **subitem,
                            self=item.self,
                            repo_name=item.repo_name,
                            branch=item.branch
                        )
                    )
                    for subitem in item.self.projects.get(item.repo_name).repository_tree(
                        ref=item.branch, path=item.path
                    )
                ]
            return []

        item.tree = partial(tree, item=item)
        return item

    def decode_content(self, content):
        """
        Decode the content from base64 to a string or bytes.

        Args:
            content (str): Base64 encoded content.

        Returns:
            tuple: Decoded content and a flag indicating if it is a string (1) or bytes (0).
        """
        try:
            return base64.b64decode(content).decode('utf-8'), 1
        except Exception:
            return base64.b64decode(content), 0

    def get_repository_contents(self, full_name: str = None, project: Project = None, ref: str = "main") -> BranchManager:
        """
        Retrieve repository contents and organize them into a BranchManager structure.

        Args:
            full_name (str, optional): Full name of the repository (e.g., "owner/repo").
            project (Project, optional): GitLab project object.

        Returns:
            BranchManager: Organized repository contents.
        """
        if not project:
            project = self.projects.get(full_name)

        branches = project.branches.list()
        contents = {}

        if ref:
            ref = str(ref).strip()
            ref_branch = next((b for b in branches if b.encoded_id == ref), None)
            if not ref_branch:
                return BranchManager(main=Branch(name=ref))

            branch_contents = [
                self.can_iterate(
                    RepositoryItem(
                        **item,
                        self=self,
                        repo_name=full_name or project.path_with_namespace,
                        branch=ref
                    )
                )
                for item in project.repository_tree(ref=ref)
            ]
            return BranchManager(
                main=Branch(name=ref, branch=ref_branch, contents=branch_contents),
                has_more=False,
                other_branches=[]
            )

        for branch in branches:
            branch_contents = [
                self.can_iterate(
                    RepositoryItem(
                        **item,
                        self=self,
                        repo_name=full_name or project.path_with_namespace,
                        branch=branch.encoded_id
                    )
                )
                for item in project.repository_tree(ref=branch.encoded_id)
            ]
            contents[branch.encoded_id] = branch_contents

        main_branch_contents = contents.pop("main", None)

        return BranchManager(
            main=Branch(
                name="main",
                branch=next((b for b in branches if b.encoded_id == "main"), None),
                contents=main_branch_contents or []
            ),
            has_more=len(contents) > 0,
            other_branches=[
                Branch(
                    name=branch.encoded_id,
                    branch=branch,
                    contents=contents.get(branch.encoded_id, [])
                )
                for branch in branches if branch.encoded_id != "main"
            ]
        )

    def clone_repo(self, full_name: str, ref: str = "main", overwrite: bool = False) -> str:
        """
        Clone the repository using the provided parameters.

        Args:
            full_name (str): Full name of the repository (e.g., "owner/repo").
            ref (str, optional): Reference branch or tag to clone. Defaults to None.

        Returns:
            str: The clone command or URL.
        """
        project = self.projects.get(full_name)
        manager = self.get_repository_contents(project=project, ref=ref)
        _, repo_name = full_name.split('/')
        repo_path = Path(os.path.join(os.getcwd(), repo_name))

        if os.path.exists(str(repo_path)):
            if not overwrite:
                self.info(f"Directory {repo_name} already exists. Use overwrite=True to replace it.")
                return
            self.info(f"Overwriting existing directory {repo_name}.")

        repo_path.mkdir(parents=True, exist_ok=True)

        def process_content(branch_manager: BranchManager):
            for item in branch_manager.main.contents:
                if item.type == "blob":
                    item_path = repo_path / Path(item.path)
                    item_path.parent.mkdir(parents=True, exist_ok=True)
                    content, flag = self.decode_content(
                        item.self.projects.get(full_name).files.get(item.path, ref=ref).content
                    )
                    with open(
                        repo_path / item.path,
                        'w' if flag else 'wb',
                        **dict(encoding='utf-8') if flag else {}
                    ) as f:
                        f.write(content)
                elif item.type == "tree":
                    dir_path = Path(os.path.join(repo_name, item.path))
                    dir_path.mkdir(parents=True, exist_ok=True)
                    sub_contents = item.tree()
                    for sub_item in sub_contents:
                        sub_item.self = self
                        sub_item.repo_name = full_name
                        sub_item.branch = ref or "main"
                        process_content(
                            BranchManager(main=Branch(name=item.name, contents=[sub_item]))
                        )

        process_content(manager)

    def get_file_content(self, full_name: str, path: str, ref: str = "main") -> tuple[str, int]:
        """
        Get the content of a file in the repository.

        Args:
            full_name (str): Full name of the repository (e.g., "owner/repo").
            path (str): Path to the file in the repository.
            ref (str, optional): Reference branch or tag. Defaults to None.

        Returns:
            tuple: Decoded content and a flag indicating if it is a string (1) or bytes (0).
        """
        project = self.projects.get(full_name)
        file = project.files.get(file_path=path, ref=ref)
        return file.decode(), 0

    def get_user_repositories(self, username: str) -> list[Project]:
        """
        Get repositories for a specific user.

        Args:
            username (str): Username of the GitLab user.

        Returns:
            list[Project]: List of repositories that can be cloned.
        """
        return [can_clone(self, project) for project in self.projects.list(username=username)]