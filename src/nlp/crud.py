from src.nlp.models import Message, Session
from src.utils.crud import CRUDBase


class SessionCRUD(CRUDBase[Session]):
    model = Session


class MessageCRUD(CRUDBase[Message]):
    model = Message
