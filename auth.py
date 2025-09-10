from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import uuid
from typing import Optional, List

from database import get_db
from models import User


SECRET_KEY = "supersecretjwtkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 5
REFRESH_TOKEN_EXPIRE_DAYS = 7
RESET_TOKEN_EXPIRE_MINUTES = 15


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


blacklisted_refresh_tokens = set()


ROLE_HIERARCHY = {
    "admin": ["admin", "manager", "hr", "employee"],
    "manager": ["manager", "hr", "employee"],
    "hr": ["hr", "employee"],
    "employee": ["employee"]
}


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    jti = str(uuid.uuid4())
    to_encode = {**data, "exp": expire, "iat": datetime.utcnow(), "jti": jti}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    to_encode = {**data, "exp": expire, "iat": datetime.utcnow(), "jti": jti, "type": "refresh"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_reset_token(data: dict, expires_delta: timedelta = None):
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES))
    return jwt.encode({**data, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db, username)
    if user is None:
        raise credentials_exception
    return user


def require_roles(allowed_roles: List[str]):
    def role_checker(current_user: User = Depends(get_current_user)):
        user_roles = [role.name.lower() for role in current_user.roles]
        expanded_roles = set()
        for role in user_roles:
            expanded_roles.update(ROLE_HIERARCHY.get(role, [role]))
        if not any(role in allowed_roles for role in expanded_roles):
            raise HTTPException(status_code=403, detail="Permission denied")
        return current_user
    return role_checker


def get_user_roles(username: str, db: Session) -> List[str]:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return [role.name for role in user.roles]

def authorize(username: str, resource: str, action: str, db: Session):
    roles = get_user_roles(username, db)
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="Unauthorized action")
    

    

