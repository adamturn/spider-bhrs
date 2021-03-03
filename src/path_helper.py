import pathlib


class ProjectPath(object):

    def __init__(self, project_root):
        self.root = project_root

    @classmethod
    def from_src(cls, file):
        print(f"Constructing ProjectPath from src file: `{file}`")
        src_dir = pathlib.Path(file).parent.absolute()

        return cls(project_root=src_dir.parent)
