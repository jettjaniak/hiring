"""
SQLAdmin configuration for the hiring process app
"""
from sqladmin import Admin, ModelView
from .models import (
    Candidate,
    Checklist,
    CandidateChecklistState,
    EmailTemplate,
    TaskTemplate,
    EmailTemplateTask,
    Task,
    TaskCandidateLink
)


# Model Admin Views
class CandidateAdmin(ModelView, model=Candidate):
    column_list = [Candidate.email, Candidate.name, Candidate.workflow_id, Candidate.phone, Candidate.created_at]
    column_searchable_list = [Candidate.email, Candidate.name]
    column_sortable_list = [Candidate.email, Candidate.name, Candidate.created_at]
    name = "Candidate"
    name_plural = "Candidates"
    icon = "fa-solid fa-user"


class ChecklistAdmin(ModelView, model=Checklist):
    column_list = [Checklist.id, Checklist.name, Checklist.task_template_id, Checklist.created_at]
    column_searchable_list = [Checklist.name]
    column_sortable_list = [Checklist.name, Checklist.created_at]
    form_ajax_refs = {
        "task_template": {
            "fields": ("task_id", "name"),
            "order_by": "name",
        }
    }
    name = "Checklist"
    name_plural = "Checklists"
    icon = "fa-solid fa-list-check"


class CandidateChecklistStateAdmin(ModelView, model=CandidateChecklistState):
    column_list = [
        CandidateChecklistState.candidate_id,
        CandidateChecklistState.checklist_id,
        CandidateChecklistState.task_identifier,
        CandidateChecklistState.updated_at
    ]
    column_searchable_list = [CandidateChecklistState.candidate_id, CandidateChecklistState.task_identifier]
    form_ajax_refs = {
        "candidate": {
            "fields": ("email", "name"),
            "order_by": "name",
        },
        "checklist": {
            "fields": ("id", "name"),
            "order_by": "name",
        }
    }
    name = "Checklist State"
    name_plural = "Checklist States"
    icon = "fa-solid fa-check-square"


class EmailTemplateAdmin(ModelView, model=EmailTemplate):
    column_list = [EmailTemplate.id, EmailTemplate.name, EmailTemplate.subject, EmailTemplate.created_at]
    column_searchable_list = [EmailTemplate.name, EmailTemplate.subject]
    column_sortable_list = [EmailTemplate.name, EmailTemplate.created_at]
    name = "Email Template"
    name_plural = "Email Templates"
    icon = "fa-solid fa-envelope"


class TaskTemplateAdmin(ModelView, model=TaskTemplate):
    column_list = [TaskTemplate.task_id, TaskTemplate.name, TaskTemplate.special_action, TaskTemplate.created_at]
    column_searchable_list = [TaskTemplate.name]
    column_sortable_list = [TaskTemplate.name, TaskTemplate.created_at]
    name = "Task Template"
    name_plural = "Task Templates"
    icon = "fa-solid fa-clipboard-list"


class EmailTemplateTaskAdmin(ModelView, model=EmailTemplateTask):
    column_list = [
        EmailTemplateTask.email_template_id,
        EmailTemplateTask.task_template_id,
        EmailTemplateTask.created_at
    ]
    form_ajax_refs = {
        "email_template": {
            "fields": ("id", "name"),
            "order_by": "name",
        },
        "task_template": {
            "fields": ("task_id", "name"),
            "order_by": "name",
        }
    }
    name = "Email-Task Link"
    name_plural = "Email-Task Links"
    icon = "fa-solid fa-link"


class TaskAdmin(ModelView, model=Task):
    column_list = [Task.id, Task.title, Task.status, Task.template_id, Task.workflow_id, Task.created_at]
    column_searchable_list = [Task.title]
    column_sortable_list = [Task.title, Task.status, Task.created_at]
    column_default_sort = [(Task.created_at, True)]  # Descending order
    form_ajax_refs = {
        "template": {
            "fields": ("task_id", "name"),
            "order_by": "name",
        }
    }
    name = "Task"
    name_plural = "Tasks"
    icon = "fa-solid fa-tasks"


class TaskCandidateLinkAdmin(ModelView, model=TaskCandidateLink):
    column_list = [
        TaskCandidateLink.task_id,
        TaskCandidateLink.candidate_email,
        TaskCandidateLink.created_at
    ]
    form_ajax_refs = {
        "task": {
            "fields": ("id", "title"),
            "order_by": "id",
        },
        "candidate": {
            "fields": ("email", "name"),
            "order_by": "name",
        }
    }
    name = "Task-Candidate Link"
    name_plural = "Task-Candidate Links"
    icon = "fa-solid fa-link"


def setup_admin(app, engine):
    """Set up SQLAdmin with all model views"""
    admin = Admin(app, engine, title="Hiring Process Admin")

    # Register all model views
    admin.add_view(CandidateAdmin)
    admin.add_view(TaskAdmin)
    admin.add_view(TaskTemplateAdmin)
    admin.add_view(EmailTemplateAdmin)
    admin.add_view(ChecklistAdmin)
    admin.add_view(CandidateChecklistStateAdmin)
    admin.add_view(EmailTemplateTaskAdmin)
    admin.add_view(TaskCandidateLinkAdmin)

    return admin
