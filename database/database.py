import psycopg2


class PostgreClient:
    def __init__(
        self, host: str, dbname: str, user: str, password: str, logger=None
    ) -> None:
        self.logger = logger
        self.__cur = None
        try:
            self.__conn = psycopg2.connect(
                f"host={host} dbname={dbname} user={user} password={password}"
            )
            self.__cur = self.__conn.cursor()
            if logger is not None:
                self.logger.info("Database connected")
        except Exception as e:
            if logger is not None:
                self.logger.error(f"ERROR: {e}")

    def init_user_table(self):
        try:
            self.__cur.execute(
                """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                timestamp_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                credits INTEGER DEFAULT 0
            );
            """
            )
            if self.logger is not None:
                self.logger.info(f"table users initted")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"ERROR: {e}")

    def add_user_if_not_exists(self, user_id):
        self.__cur.execute("SELECT COUNT(*) FROM users WHERE user_id = %s", (user_id,))
        count = self.__cur.fetchone()[0]

        if count == 0:
            self.__cur.execute(
                "INSERT INTO users (user_id) VALUES (%s)",
                (user_id,),
            )
            self.__conn.commit()
            if self.logger is not None:
                self.logger.info(f"User ID {user_id} added")
        else:
            if self.logger is not None:
                self.logger.info(f"User ID {user_id} alredy exists.")

    def get_user_string_by_id(self, user_id):
        try:
            self.__cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user_string = self.__cur.fetchone()
            if user_string:
                return user_string
            else:
                if self.logger is not None:
                    self.logger.info(f"No user found with ID {user_id}")
                return None
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"ERROR: {e}")
            return None

    def add_credits_to_user(self, user_id, credits_to_add):
        try:
            self.__cur.execute(
                "UPDATE users SET credits = credits + %s WHERE user_id = %s",
                (credits_to_add, user_id),
            )
            self.__conn.commit()
            if self.logger is not None:
                self.logger.info(f"{credits_to_add} credits added to User ID {user_id}")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"ERROR: {e}")

    def drop_table(self, table_name):
        try:
            self.__cur.execute(f"DROP TABLE IF EXISTS {table_name};")
            self.__conn.commit()
            if self.logger is not None:
                self.logger.info(f"Table {table_name} dropped")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"ERROR: {e}")


client = PostgreClient(
    host="84.23.52.41",
    dbname="user_db",
    password="zVA89Y31(rN91K9c6",
    user="korney",
)
