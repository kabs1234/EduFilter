import os
import psycopg2
from dotenv import load_dotenv
from typing import Dict, Any, Optional, Tuple

class DatabaseManager:
    def __init__(self):
        load_dotenv()
        self.db_config = {
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST')
        }

    def execute_query(self, query: str, params: tuple = None, fetch: bool = True) -> Optional[Any]:
        """
        Execute a database query with error handling
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch results
            
        Returns:
            Query results if fetch is True, None otherwise
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            cur.execute(query, params)
            result = cur.fetchone() if fetch else None
            
            conn.commit()
            return result
        except Exception as e:
            raise DatabaseError(f"Database error: {str(e)}")
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    def verify_user_exists(self, user_id: int) -> bool:
        """Check if a user exists in the database"""
        # Try to convert user_id to integer if possible
        try:
            user_id = int(user_id)
            result = self.execute_query(
                "SELECT id FROM users WHERE id = %s",
                (user_id,)
            )
            return bool(result)
        except (ValueError, TypeError):
            # If user_id is not an integer, return False
            return False

    def get_user_settings(self, user_id: int) -> Tuple[str, bool]:
        """Get user email and 2FA status"""
        try:
            user_id = int(user_id)
            result = self.execute_query(
                "SELECT email, is_2fa_enabled FROM users WHERE id = %s",
                (user_id,)
            )
            if result:
                return result
            return None, None
        except (ValueError, TypeError):
            # If user_id is not an integer, return None values
            return None, None

    def update_user_settings(self, user_id: int, email: str, is_2fa_enabled: bool) -> bool:
        """Update user settings"""
        try:
            # Try to convert user_id to integer if possible
            try:
                user_id = int(user_id)
                self.execute_query(
                    """
                    UPDATE users 
                    SET email = %s, is_2fa_enabled = %s 
                    WHERE id = %s
                    """,
                    (email, is_2fa_enabled, user_id),
                    fetch=False
                )
                return True
            except (ValueError, TypeError):
                # If user_id is not an integer, return False
                return False
        except Exception:
            return False

    def manage_2fa_codes(self, user_id: int, code: str = None, verify: bool = False, delete: bool = False):
        """Manage 2FA codes - create, verify, or delete"""
        try:
            # Try to convert user_id to integer
            user_id = int(user_id)
            
            if verify:
                result = self.execute_query(
                    """
                    SELECT code FROM two_factor_codes 
                    WHERE user_id = %s AND code = %s AND expiry > NOW()
                    """,
                    (user_id, code)
                )
                return bool(result)
            elif delete:
                self.execute_query(
                    "DELETE FROM two_factor_codes WHERE user_id = %s",
                    (user_id,),
                    fetch=False
                )
            else:
                self.execute_query(
                    """
                    INSERT INTO two_factor_codes (user_id, code, expiry) 
                    VALUES (%s, %s, NOW() + INTERVAL '10 minutes')
                    """,
                    (user_id, code),
                    fetch=False
                )
            return True
        except (ValueError, TypeError):
            # If user_id is not an integer, return False for verify
            # and True for other operations to avoid errors
            return False if verify else True
        except Exception:
            return False if verify else True

class DatabaseError(Exception):
    """Custom exception for database errors"""
    pass
