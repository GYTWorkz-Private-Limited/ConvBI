import psycopg

def run(state, get_db_connection):

    try:
        conn = get_db_connection()
        if not conn:
            raise ConnectionError("Could not establish database connection")
        
        cursor = conn.cursor()
        query = state["sql_query"]

        try:
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            formatted_results = [dict(zip(columns, row)) for row in results]

            state["query_result"] = str(formatted_results)
            state["needs_clarification"] = False
            state["has_sql_error"] = False

        except psycopg.OperationalError as op_err:
            state["error_message"] = "Database connection error. Please retry."
            state["needs_clarification"] = True
            state["has_sql_error"] = True
            try:
                state.setdefault("error_history", []).append(f"OperationalError: {str(op_err)}")
            except Exception:
                pass

        except psycopg.ProgrammingError as pg_err:
            state["error_message"] = "Invalid SQL query."
            state["needs_clarification"] = True
            state["has_sql_error"] = True
            try:
                state.setdefault("error_history", []).append(f"ProgrammingError: {str(pg_err)}")
            except Exception:
                pass

        except Exception as e:
            state["error_message"] = f"Unexpected error: {e}"
            state["needs_clarification"] = True
            state["has_sql_error"] = True
            try:
                state.setdefault("error_history", []).append(f"Exception: {str(e)}")
            except Exception:
                pass

        finally:
            cursor.close()
            conn.close()

    except Exception as conn_err:
        state["error_message"] = "Database unavailable. Please try again later."
        state["needs_clarification"] = True
        state["has_sql_error"] = True
        try:
            state.setdefault("error_history", []).append(f"ConnectionError: {str(conn_err)}")
        except Exception:
            pass

    return state

