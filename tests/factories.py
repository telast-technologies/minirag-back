# tests/factories.py
import factory

from src.users.models import User


class BaseFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session = None
        sqlalchemy_session_persistence = None


class UserFactory(BaseFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    phone = factory.Sequence(lambda n: f"+201011934{100 + n:03d}")

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        raw_password = extracted or "password123"
        self.set_password(raw_password)
