import unittest

from sqlalchemy.sql import text

import bcrypt
import pytest
from skygear.container import SkygearContainer
from skygear.transmitter.common import _get_engine
from skygear.utils import user as u

PLAINTEXT = 'helloworld!'


def assert_correct_pw(password, salt):
    decoded_salt = salt.encode('utf-8')
    new_hash = bcrypt.hashpw(password.encode('utf-8'), decoded_salt)
    assert new_hash == decoded_salt


class TestHashPassword():
    def test_hash_password(self):
        hashed = u.hash_password(PLAINTEXT)
        assert isinstance(hashed, str)
        assert_correct_pw(PLAINTEXT, hashed)


class TestResetPassword(unittest.TestCase):
    app_name = '_'

    def setUp(self):
        SkygearContainer.set_default_app_name(self.app_name)
        with _get_engine().begin() as conn:
            conn.execute("CREATE SCHEMA IF NOT EXISTS app_{0}"
                         .format(self.app_name))
            conn.execute("set search_path to app_{0};".format(self.app_name))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _user (
                    id text PRIMARY KEY,
                    username text,
                    email text,
                    password text,
                    auth jsonb
                );""")
            sql = text("""
                INSERT INTO _user (id, username, password)
                VALUES (:id, :username, :password);
                """)
            conn.execute(sql,
                         id='1',
                         username='USER_1',
                         password=u.hash_password('supersecret1'))

    def tearDown(self):
        with _get_engine().begin() as conn:
            conn.execute("DROP TABLE app_{0}._user;".format(self.app_name))

    def test_reset_password(self):
        with _get_engine().begin() as conn:
            done = u.reset_password_by_username(conn, "USER_1", PLAINTEXT)
            assert done

            result = conn.execute(text("""
                SELECT password
                FROM app_{0}._user
                WHERE username=:username
                """.format(self.app_name)),
                username='USER_1')
            r = result.fetchone()
            assert_correct_pw(PLAINTEXT, r[0])

    def test_no_such_user(self):
        with _get_engine().begin() as conn:
            done = u.reset_password_by_username(conn, "USER_2", PLAINTEXT)
            assert not done

    def test_bad_parameter(self):
        with _get_engine().begin() as conn:
            with pytest.raises(ValueError):
                u.reset_password_by_username(conn, 1, '')

            with pytest.raises(ValueError):
                u.reset_password_by_username(conn, '', 1)