import sqlite3
import re

# ==========================================
# NATURAL LANGUAGE DATABASE MANAGER
# ==========================================

DB_NAME = "database_manager.db"

# DATABASE CONNECTION

db = sqlite3.connect(DB_NAME)
db.row_factory = sqlite3.Row
cursor = db.cursor()

print("\n" + "=" * 60)
print("       NATURAL LANGUAGE DATABASE MANAGER")
print("=" * 60)
print("Database connected successfully!")


# ==========================================
# IDENTIFIER VALIDATION
# ==========================================

def identifier(name):

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError("Invalid table or column name.")

    return f'"{name}"'


# ==========================================
# VALUE PROCESSING
# ==========================================

def parse_value(value):

    value = value.strip()

    if len(value) >= 2 and value[0] == value[-1]:
        if value[0] in ("'", '"'):
            return value[1:-1]

    if value.upper() == "NULL":
        return None

    if re.fullmatch(r"-?\d+", value):
        return int(value)

    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)

    return value


def split_values(text):

    values = []
    current = ""
    quote = None

    for char in text:

        if char in ("'", '"'):

            if quote is None:
                quote = char

            elif quote == char:
                quote = None

        if char == "," and quote is None:
            values.append(current.strip())
            current = ""
        else:
            current += char

    if quote:
        raise ValueError("Unclosed quotation mark.")

    values.append(current.strip())

    return values


# ==========================================
# SQL DATA TYPE VALIDATION
# ==========================================

def valid_type(data_type):

    allowed_types = [
        "INT", "INTEGER", "REAL", "TEXT",
        "BLOB", "NUMERIC", "BOOLEAN",
        "DATE", "DATETIME"
    ]

    dtype = data_type.strip().upper()

    if dtype not in allowed_types:
        raise ValueError("Unsupported SQLite data type.")

    return dtype


# ==========================================
# CONDITION PROCESSING
# ==========================================

def parse_condition(text):

    match = re.fullmatch(
        r"([A-Za-z_]\w*)\s+is\s+(.+)",
        text.strip(),
        re.I
    )

    if not match:
        raise ValueError(
            "Example condition: name is 'Mani'"
        )

    column = identifier(match.group(1))
    value = parse_value(match.group(2))

    return column, value


# ==========================================
# SQL EXECUTION ENGINE
# ==========================================

def execute(sql, params=None, fetch=False):

    try:

        cursor.execute(sql, params or ())

        if fetch:

            records = cursor.fetchall()

            print("\n" + "-" * 60)
            print("DATABASE RESULTS")
            print("-" * 60)

            if records:

                for record in records:
                    print(dict(record))

            else:
                print("No records found.")

        else:

            db.commit()

            print("\nQuery executed successfully!")
            print("Affected rows:", cursor.rowcount)

        print("\nGenerated SQL:")
        print(sql)

    except sqlite3.Error as e:

        db.rollback()

        print("\nSQLite Error:", e)


# ==========================================
# NATURAL LANGUAGE PROCESSING ENGINE
# ==========================================

def process_command(command):

    command = command.strip().rstrip(".")

    # 1. CREATE TABLE

    match = re.fullmatch(
        r"create table (?:named )?(\w+) with columns (.+)",
        command,
        re.I
    )

    if match:

        table = identifier(match.group(1))
        column_data = split_values(match.group(2))

        columns = []

        for item in column_data:

            col = re.fullmatch(
                r"(\w+)\s+(\w+)",
                item
            )

            if not col:
                raise ValueError("Invalid column definition.")

            name = identifier(col.group(1))
            dtype = valid_type(col.group(2))

            columns.append(f"{name} {dtype}")

        if not columns:
            raise ValueError("No columns provided.")

        sql = (
            f"CREATE TABLE {table} "
            f"({', '.join(columns)})"
        )

        execute(sql)
        return

    # 2. DROP TABLE

    match = re.fullmatch(
        r"drop table (\w+)",
        command,
        re.I
    )

    if match:

        confirm = input(
            "WARNING! Permanently delete table. Type YES: "
        )

        if confirm != "YES":
            print("Operation cancelled.")
            return

        execute(
            f"DROP TABLE {identifier(match.group(1))}"
        )

        return

    # 3. TRUNCATE TABLE
    # SQLite uses DELETE FROM instead

    match = re.fullmatch(
        r"(?:truncate|empty) (?:the )?(?:table )?(\w+)",
        command,
        re.I
    )

    if match:

        confirm = input(
            "WARNING! Delete ALL records. Type YES: "
        )

        if confirm != "YES":
            print("Operation cancelled.")
            return

        execute(
            f"DELETE FROM {identifier(match.group(1))}"
        )

        return

    # 4. ALTER TABLE - ADD COLUMN

    match = re.fullmatch(
        r"add column (\w+) (\w+) to (\w+)",
        command,
        re.I
    )

    if match:

        column = identifier(match.group(1))
        dtype = valid_type(match.group(2))
        table = identifier(match.group(3))

        execute(
            f"ALTER TABLE {table} "
            f"ADD COLUMN {column} {dtype}"
        )

        return

    # 5. ALTER TABLE - MODIFY COLUMN

    match = re.fullmatch(
        r"change column (\w+) in (\w+) to (\w+)",
        command,
        re.I
    )

    if match:

        raise ValueError(
            "SQLite does not support direct MODIFY COLUMN. "
            "Use table reconstruction or rename the column."
        )

    # 6. INSERT RECORD

    match = re.fullmatch(
        r"insert (?:a new )?(?:record|student) "
        r"into (\w+) with (.+)",
        command,
        re.I
    )

    if match:

        table = identifier(match.group(1))
        items = split_values(match.group(2))

        columns = []
        values = []

        for item in items:

            pair = re.fullmatch(
                r"(\w+)\s*=\s*(.+)",
                item
            )

            if not pair:
                raise ValueError(
                    "Use column=value format."
                )

            columns.append(
                identifier(pair.group(1))
            )

            values.append(
                parse_value(pair.group(2))
            )

        placeholders = ", ".join(
            ["?"] * len(values)
        )

        sql = (
            f"INSERT INTO {table} "
            f"({', '.join(columns)}) "
            f"VALUES ({placeholders})"
        )

        execute(sql, values)
        return

    # 7. SELECT RECORDS

    match = re.fullmatch(
        r"(?:show|display) (?:all )?(\w+)"
        r"(?: where (.+))?",
        command,
        re.I
    )

    if match:

        table = identifier(match.group(1))

        sql = f"SELECT * FROM {table}"
        params = []

        if match.group(2):

            col, value = parse_condition(
                match.group(2)
            )

            if value is None:
                sql += f" WHERE {col} IS NULL"

            else:
                sql += f" WHERE {col} = ?"
                params.append(value)

        execute(sql, params, fetch=True)
        return

    # 8. UPDATE RECORD

    match = re.fullmatch(
        r"update (\w+) set (\w+) to (.+) where (.+)",
        command,
        re.I
    )

    if match:

        table = identifier(match.group(1))
        column = identifier(match.group(2))

        new_value = parse_value(match.group(3))

        where_col, where_value = parse_condition(
            match.group(4)
        )

        if where_value is None:

            condition = f"{where_col} IS NULL"
            params = [new_value]

        else:

            condition = f"{where_col} = ?"
            params = [new_value, where_value]

        sql = (
            f"UPDATE {table} "
            f"SET {column} = ? "
            f"WHERE {condition}"
        )

        execute(sql, params)
        return

    # 9. DELETE RECORD

    match = re.fullmatch(
        r"delete (?:the )?(?:record|student) "
        r"from (\w+) where (.+)",
        command,
        re.I
    )

    if match:

        table = identifier(match.group(1))

        col, value = parse_condition(
            match.group(2)
        )

        if value is None:

            sql = (
                f"DELETE FROM {table} "
                f"WHERE {col} IS NULL"
            )

            execute(sql)

        else:

            sql = (
                f"DELETE FROM {table} "
                f"WHERE {col} = ?"
            )

            execute(sql, [value])

        return

    # INVALID COMMAND

    print("\nSorry! Command not recognized.")
    print("Please enter a supported English command.")


# ==========================================
# MAIN APPLICATION
# ==========================================

print("""
SUPPORTED OPERATIONS:

1. CREATE
2. SELECT
3. INSERT
4. UPDATE
5. DELETE
6. DROP
7. TRUNCATE
8. ALTER (ADD COLUMN)

Type 'exit' to close the application.
""")

while True:

    try:

        user_input = input(
            "\nNatural Language Database Manager > "
        )

        if user_input.lower().strip() == "exit":
            break

        if not user_input.strip():
            continue

        process_command(user_input)

    except (ValueError, TypeError) as e:

        print("\nInvalid command:", e)

    except Exception as e:

        print("\nUnexpected error:", e)


# ==========================================
# CLOSE DATABASE
# ==========================================

cursor.close()
db.close()

print("\nNatural Language Database Manager closed.")
