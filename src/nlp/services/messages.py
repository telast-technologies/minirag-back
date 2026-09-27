from fastapi import Request

from src.nlp.crud import MessageCRUD, SessionCRUD
from src.nlp.models import Message, Session
from src.nlp.services.controllers import NLPController
from src.utils.llm.generation.enums import MsgRoles


class MessageService:
    """
    Service for handling message operations.

    Manages text and voice message processing, including interaction
    with Client for chat completions and audio transcription/synthesis.
    """

    def __init__(self, session: Session) -> None:
        """
        Initialize the messages service.

        Args:
            session (Session): The session to get messages from.
        """
        self.session = session
        # تعريف الـ CRUDs هنا يضمن توفر الـ DB Session في السياق
        self.message_crud = MessageCRUD()
        self.session_crud = SessionCRUD()

    async def get_history_messages(self, nlp_controller: NLPController, limit: int = 20) -> list[dict]:
        """
        Retrieve recent messages for Client context.

        Args:
            limit (int): Maximum number of messages to retrieve.
        Returns:
            list[dict]: List of message dictionaries with role and content.
        """
        query = (Message.session_id == self.session.id,)
        history = await self.message_crud.list(*query, limit=limit)

        history = [
            nlp_controller.generator.provider.construct_prompt(prompt=msg.content, role=msg.role) for msg in history
        ]
        return history

    async def ask(
        self,
        request: Request,
        content: str,
        nlp_controller: NLPController,
        limit: int = 10,
    ):
        """
        إرسال رسالة نصية، جلب التاريخ، تطبيق الـ RAG، واسترجاع الرد تدفقياً.
        """
        # 1) جلب سجل المحادثات السابق للسياق باستخدام الدالة الصحيحة
        history = await self.get_history_messages(nlp_controller=nlp_controller, limit=20)

        # 2) حفظ رسالة المستخدم في قاعدة البيانات
        await self.message_crud.create(
            {"session_id": self.session.id, "role": MsgRoles.USER.value, "content": content},
        )

        async def message_generator():
            accumulated_content: str = ""
            try:
                # 3) استهلاك الـ stream القادم من الـ Controller وتمرير السؤال والتاريخ معه
                async for chunk in nlp_controller.answer_stream(
                    project=self.session.project, query=content, history=history, limit=limit
                ):
                    accumulated_content += chunk
                    yield chunk
            except Exception as e:
                yield f"\n\n[ERROR]: {e}"
            finally:
                # 4) حفظ رد المساعد (Assistant) بالكامل في قاعدة البيانات بعد انتهاء الـ Stream
                async with request.app.state.db_session() as db_session:
                    self.message_crud.session = db_session
                    await self.message_crud.create(
                        {
                            "session_id": self.session.id,
                            "role": MsgRoles.ASSISTANT.value,
                            "content": accumulated_content,
                        },
                    )
                    # commit
                    await db_session.commit()
                    yield "\n\n[DONE]"

        return message_generator
