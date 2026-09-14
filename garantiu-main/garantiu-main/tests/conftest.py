import git


def init_repo(path):
    """
    git.Repo.init() plus a repo-local commit identity, so tests that create
    commits don't depend on the machine's global git config (e.g. in CI,
    where no global user.name/user.email is set).
    """
    repo = git.Repo.init(path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "garantiu-tests")
        config.set_value("user", "email", "garantiu-tests@example.com")
        config.set_value("commit", "gpgsign", "false")
        config.set_value("diff", "renames", "true")
    return repo
