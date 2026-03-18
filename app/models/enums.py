import enum


class SystemRole(str, enum.Enum):
    admin = "admin"
    project_manager = "project_manager"
    developer = "developer"


class ProjectRole(str, enum.Enum):
    administrator = "administrator"
    project_manager = "project_manager"
    developer = "developer"


class EpicStatus(str, enum.Enum):
    backlog = "backlog"
    in_progress = "in_progress"
    done = "done"


class IssueType(str, enum.Enum):
    story = "story"
    task = "task"
    bug = "bug"


class IssueStatus(str, enum.Enum):
    backlog = "backlog"
    todo = "todo"
    in_progress = "in_progress"
    review = "review"
    done = "done"


class IssuePriority(str, enum.Enum):
    lowest = "lowest"
    low = "low"
    medium = "medium"
    high = "high"
    highest = "highest"


class SprintStatus(str, enum.Enum):
    planned = "planned"
    active = "active"
    completed = "completed"


ALLOWED_TRANSITIONS: dict[IssueStatus, list[IssueStatus]] = {
    IssueStatus.backlog: [IssueStatus.todo],
    IssueStatus.todo: [IssueStatus.in_progress],
    IssueStatus.in_progress: [IssueStatus.review, IssueStatus.todo],
    IssueStatus.review: [IssueStatus.done, IssueStatus.in_progress],
    IssueStatus.done: [IssueStatus.in_progress],
}
