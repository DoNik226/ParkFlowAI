from pydantic import BaseModel


class AuthUser(BaseModel):
    username: str
    email: str
    full_name: str | None = None

# id = Column(BigInteger, primary_key=True, autoincrement=True)
#     username = Column(String(50), unique=True, nullable=False)
#     email = Column(String(255), unique=True, nullable=False)
#     password_hash = Column(String(255), nullable=False)
#     role = Column(String(20), nullable=False, default=UserRole.USER.value)
#     full_name = Column(String(255))
#     is_active = Column(Boolean, nullable=False, default=True)
#     failed_attempts = Column(Integer, nullable=False, default=0)
#     locked_until = Column(DateTime(timezone=True), nullable=True)