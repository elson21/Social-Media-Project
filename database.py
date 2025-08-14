import sqlite3
from sqlite3 import Connection
from typing import Union

from models import Post, Posts, UserHashed, UserHashedIndex, Like

def get_post(
        connection: Connection,
        user_id: int | None = None,
        limit: int=10,
        page: int=0) -> Posts:
    """
    Fetches all posts from the "posts" table

    Arguments:
       connection (COnnection): An active SQLite db connection

    Returns:
        List[tuple]: A list of tuples containing attributes.
    """

    offset = limit * page

    with connection:
        cur = connection.cursor()
        cur.execute(
            """
            WITH post_page AS (
                SELECT 
                    post_id,
                    post_title,
                    post_text,
                    user_id
                FROM posts
                LIMIT :limit
                OFFSET :offset
            ),
            like_count AS (
                SELECT post_id, COUNT(*) num_likes
                FROM likes
                WHERE post_id IN (SELECT post_id FROM post_page)
                GROUP BY post_id
            ),
            user_liked AS (
                SELECT post_id, user_id
                FROM likes
                WHERE user_id = :user_id
                AND post_id IN (SELECT post_id FROM post_page)
            ),
            num_comments AS (
                SELECT post_for_id, COUNT(*) number_comments
                FROM comments
                GROUP BY 1
            )
            SELECT 
                post_title,
                post_text,
                p.user_id user_id,
                num_likes,
                p.post_id post_id,
                u.user_id user_liked,
                number_comments
            FROM post_page p
            LEFT JOIN like_count l
            USING (post_id)
            LEFT JOIN user_liked u
            USING (post_id)
            LEFT JOIN num_comments AS n
            ON (p.post_id = n.post_for_id);
            """,
            {
                "limit"  : limit,
                "offset" : offset,
                "user_id": user_id
            }
        )

        return Posts(posts=[Post.model_validate(dict(post)) for post in cur])


def get_single_post(
        connection: Connection,
        post_id: int,
        user_id: int|None) -> Post:
    """
    Fetches a post from the "posts" table

    Arguments:
       connection (COnnection): An active SQLite db connection

    Returns:
        List[tuple]: A list of tuples containing attributes.
    """

    with connection:
        cur = connection.cursor()
        cur.execute(
            """
            WITH post_page AS (
                SELECT post_id, post_title, post_text, user_id
                FROM posts
                WHERE post_id = :post_id
            ),
            like_count AS (
                SELECT DISTINCT post_id, COUNT(*) num_likes
                FROM likes
                WHERE post_id = :post_id
            ),
            user_liked AS (
                SELECT post_id, user_id user_liked
                FROM likes
                WHERE user_id = :user_id AND post_id = :post_id
            ),
            num_comments AS (
                SELECT DISTINCT post_for_id, COUNT(*) number_comments
                FROM comments
                WHERE post_for_id = :post_id
            )
            SELECT 
                post_title,
                post_text,
                p.user_id user_id,
                num_likes,
                p.post_id post_id,
                user_liked,
                number_comments
            FROM post_page p
            LEFT JOIN like_count l USING (post_id)
            LEFT JOIN user_liked u USING (post_id)
            LEFT JOIN num_comments c ON (p.post_id = c.post_for_id );
            """,
            {
                "post_id": post_id,
                "user_id": user_id
            }
        )

        return Post.model_validate(dict(cur.fetchone()))
    

def insert_post(connection: Connection, post: Post) -> None:
    """
    Inserts a new post in the "posts" table

    Arguments:
        connection (Connection): An active SQLite db connection
        post (dict): A dictionary with the attributes as keys
    """
    with connection:
        # create an interface for the db (AKA cursor)
        cur = connection.cursor()

        # execute commands (queries)
        cur.execute(
            """
            INSERT INTO posts (post_title, post_text, user_id)
            VALUES
            ( :post_title, :post_text, :user_id)
            """,
            post.model_dump()
        )

    return cur.lastrowid


def create_user(connection: Connection, user: UserHashed) -> bool:
    with connection:
        cur = connection.cursor()

        cur.execute(
            """
            INSERT INTO users (username, salt, hash_password)
            VALUES
            ( :username, :salt, :hash_password)
            """,
            user.model_dump()
        )

    return True


def get_user(connection: Connection, username: str) -> Union[UserHashedIndex, None]:
    with connection:
        cur = connection.cursor()

        cur.execute(
            """
            SELECT
                user_id,
                username,
                salt,
                hash_password
            FROM users
            WHERE username = ?
            """,
            (username,),
        )

    user = cur.fetchone()
    if user is None:
        return None
    
    return UserHashedIndex(**dict(user))


def add_like(connection: Connection, like: Like) -> None:
    with connection:
        cur = connection.cursor()

        cur.execute(
            """
            INSERT INTO likes (user_id, post_id)
            VALUES ( :user_id, :post_id);
            """,
            like.model_dump()
        )


def add_comment(
                connection: Connection,
                post_id: int,
                post_for_id: int
            ) -> None:
    
    with connection:
        cur = connection.cursor()
        cur.execute("INSERT INTO comments (post_id, post_for_id) VALUES (?, ?)",
                    (post_id, post_for_id)
                )
        

def get_comments(
                connection: Connection,
                post_id: int,
                user_id: int|None
            ) -> Posts:

    with connection:
        cur = connection.cursor()
        cur.execute(
            """
            WITH get_comments AS(
                SELECT post_id, post_for_id
                FROM comments
                WHERE post_for_id = :post_id
            ),
            post_page AS (
                SELECT post_id, post_title, post_text, user_id
                FROM posts
                WHERE post_id IN (SELECT post_id FROM get_comments)
            ),
            like_count AS (
                SELECT DISTINCT post_id, COUNT(*) num_likes
                FROM likes
                WHERE post_id IN (SELECT post_id FROM get_comments)
                GROUP BY 1
            ),
            user_liked AS (
                SELECT post_id, user_id
                FROM likes
                WHERE user_id = :user_id
                AND post_id = (SELECT post_id FROM get_comments)
            ),
            num_comments AS (
                SELECT DISTINCT post_for_id, COUNT(*) number_comments
                FROM comments
                WHERE post_for_id IN (SELECT post_id FROM get_comments)
            )
            SELECT 
                post_title,
                post_text,
                p.user_id user_id,
                num_likes,
                p.post_id post_id,
                u.user_id user_liked,
                number_comments
            FROM post_page p
            LEFT JOIN like_count l USING (post_id)
            LEFT JOIN user_liked u USING (post_id)
            LEFT JOIN num_comments c ON (p.post_id = c.post_for_id);
            """,
            {
                "post_id": post_id,
                "user_id": user_id
            }
        )

        return Posts(posts=[Post.model_validate(dict(post)) for post in cur])
        


def check_like(
                connection: Connection,
                like: Like    
            ) -> bool:
    cur = connection.cursor()
    cur.execute(
        """
        SELECT * FROM likes
        WHERE user_id = :user_id
        AND post_id = :post_id;
        """,
        like.model_dump()
    )

    return True if cur.fetchone() is not None else False


def delete_like(
                connection: Connection,
                like: Like
            ) -> None:
    
    cur = connection.cursor()
    cur.execute(
        """
        DELETE FROM likes
        WHERE user_id = :user_id
        AND post_id = :post_id;
        """,
        like.model_dump()
    )

if __name__ == "__main__":    
    connection = sqlite3.connect("social.db")   # create connection with the db

    connection.row_factory = sqlite3.Row    # allows fetching rows as dict-like objects instead of plain tuples

    print(get_user)