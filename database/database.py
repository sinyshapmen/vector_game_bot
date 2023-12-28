import psycopg2


class PostgreClient:
    def __init__(
        self, host: str, dbname: str, user: str, password: str, logger=None
    ) -> None:
        self.logger = logger
        self.__conn = psycopg2.connect(
            f"host={host} dbname={dbname} user={user} password={password}"
        )
        self.__cur = self.__conn.cursor()
        if logger is not None:
            self.logger.info("Database connected")

    def log_decorator(message: str):
        def actual_decorator(func):
            def inner(self, *args, **kwargs):
                try:
                    if self.logger is not None:
                        args_str = ", ".join(str(arg) for arg in args)
                        kwargs_str = ", ".join(
                            f"{key}={value}" for key, value in kwargs.items()
                        )
                        full_message = (
                            f"{message} - Args: [{args_str}], Kwargs: {{{kwargs_str}}}"
                        )
                        self.logger.info(full_message)
                    result = func(self, *args, **kwargs)
                except Exception as e:
                    if self.logger is not None:
                        self.logger.error(f"ERROR: {e}")
                    return None
                return result

            return inner

        return actual_decorator

    @log_decorator("table initialized")
    def init_user_table(self):
        self.__cur.execute(
            """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            timestamp_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            credits INTEGER DEFAULT 0
        );
        """
        )

    @log_decorator("Successful interaction 'add_user_if_not_exists'")
    def add_user_if_not_exists(self, user_id):
        self.__cur.execute("SELECT COUNT(*) FROM users WHERE user_id = %s", (user_id,))
        count: tuple | None = self.__cur.fetchone()

        if count is not None and count[0] == 0:
            self.__cur.execute(
                "INSERT INTO users (user_id) VALUES (%s)",
                (user_id,),
            )
            self.__conn.commit()

    @log_decorator("Successful interaction 'get_user_string_by_id'")
    def get_user_string_by_id(self, user_id):
        self.__cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user_string = self.__cur.fetchone()
        if user_string:
            return user_string
        else:
            return None

    @log_decorator("Successful interaction 'add_credits_to_user'")
    def add_credits_to_user(self, user_id, credits_to_add):
        self.__cur.execute(
            "UPDATE users SET credits = credits + %s WHERE user_id = %s",
            (credits_to_add, user_id),
        )
        self.__conn.commit()

    @log_decorator("Table dropped")
    def drop_table(self, table_name):
        self.__cur.execute(f"DROP TABLE IF EXISTS {table_name};")
        self.__conn.commit()

    @log_decorator("User deleted")
    def delete_user(self, user_id):
        self.__cur.execute(f"DELETE FROM users WHERE user_id = {user_id};")
        self.__conn.commit()
