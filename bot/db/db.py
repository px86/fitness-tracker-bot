import aiosqlite
from typing import TypeAlias
from pathlib import Path

PathLike: TypeAlias = str | bytes | Path

db: aiosqlite.Connection | None = None

from bot.models.user import User


async def db_connect(*args) -> aiosqlite.Connection:
    """Return database connection."""
    global db
    if db is None:
        db = await aiosqlite.connect("fitness-tracker.db")
    return db


async def db_disconnect(*args) -> None:
    """Close the database connection"""
    global db
    if db is not None:
        await db.close()
        db = None


async def db_init(*args) -> None:
    """Create database table if does not exist already."""
    db = await db_connect()

    await db.executescript(
        """
        BEGIN;

        CREATE TABLE IF NOT EXISTS users(
                 id INTEGER PRIMARY KEY,
                 name TEXT NOT NULL,
                 gender TEXT NOT NULL,
                 age INTEGER NOT NULL,
                 height REAL NOT NULL,
                 weight REAL NOT NULL
            );

        CREATE TABLE IF NOT EXISTS meals(
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 timestamp TEXT NOT NULL,
                 description TEXT NOT NULL,
                 nutrient_breakdown TEXT
            );

        COMMIT;
        """
    )


async def getuser(userid: int) -> User | None:
    db = await db_connect()
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM users WHERE id=?", (userid,)) as cursor:
        async for row in cursor:
            return User(
                userid=row["id"],
                name=row["name"],
                gender=row["gender"],
                age=row["age"],
                height=row["height"],
                weight=row["weight"],
            )


async def saveuser(user: User) -> None:
    db = await db_connect()
    user_in_db = await getuser(user.userid)
    if user_in_db is None:
        await db.execute_insert(
            "INSERT INTO users(id,name,gender,age,height,weight) VALUES(?,?,?,?,?, ?)",
            (user.userid, user.name, user.gender, user.age, user.height, user.weight),
        )
    else:
        await db.execute(
            "UPDATE users SET name=?,gender=?,age=?,height=?,weight=? WHERE id=?",
            (user.name, user.gender, user.age, user.height, user.weight, user.userid),
        )
    await db.commit()


class Database:
    def __init__(self, url: str):
        self.url = url
        self.connection: aiosqlite.Connection | None = None

    async def connect(self) -> aiosqlite.Connection:
        """Connect to sqlite database."""
        if self.connection is None:
            self.connection = await aiosqlite.connect(self.url)
        return self.connection

    async def disconnect(self) -> None:
        """Close connection to sqlite database."""
        if self.connection is not None:
            await self.connection.close()
            self.connection = None
        else:
            raise Exception("attempt made to disconnect before connect")
