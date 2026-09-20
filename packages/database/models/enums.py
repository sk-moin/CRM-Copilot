from enum import Enum


class DocumentProcessingStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PARSING = "PARSING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    READY = "READY"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"

class AgentActionStatus(str, Enum):
    """Lifecycle of an agent-proposed CRM mutation.

    PENDING is the only state from which a decision may be made; the guard on
    that transition is what stops a double-approve executing twice.
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"


class AgentActionType(str, Enum):
    """The CRM mutations the agent is allowed to propose.

    Deliberately a closed set. Execution maps each member to one named service
    method, so a payload can never select a method by name.
    """

    CREATE_TASK = "CREATE_TASK"
    UPDATE_TASK_STATUS = "UPDATE_TASK_STATUS"
    CREATE_CONTACT = "CREATE_CONTACT"
    UPDATE_CONTACT = "UPDATE_CONTACT"
    UPDATE_OPPORTUNITY_STAGE = "UPDATE_OPPORTUNITY_STAGE"
