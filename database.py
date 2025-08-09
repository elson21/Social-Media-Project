import sqlite3
from sqlite3 import Connection
from typing import List

from models import Post, Posts

def get_post(connection: Connection) -> List[tuple]:
    """
    Fetches all posts from the "posts" table

    Arguments:
       connection (COnnection): An active SQLite db connection

    Returns:
        List[tuple]: A list of tuples containing attributes.
    """

    with connection:
        cur = connection.cursor()
        cur.execute(
            """
            SELECT post_title, post_text, user_id
            FROM posts;
            """
        )

        return Posts(posts=[Post.model_validate(dict(post)) for post in cur])
    

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


if __name__ == "__main__":    
    connection = sqlite3.connect("social.db")   # create connection with the db

    connection.row_factory = sqlite3.Row    # allows fetching rows as dict-like objects instead of plain tuples

    test_post = Post(post_title="Pydantic Test", post_text="A test", user_id=2)

    # insert_post(connection, test_post)
    
    for post in get_post(connection):
        print(dict(post))