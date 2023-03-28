"""TcEx Framework Module"""
# standard library
import logging

# third-party
from redis import Redis

from ...pleb.scoped_property import scoped_property
from ...requests_tc.tc_session import TcSession
from .key_value_api import KeyValueApi
from .key_value_mock import KeyValueMock
from .key_value_redis import KeyValueRedis
from .redis_client import RedisClient

# get logger
_logger = logging.getLogger(__name__.split('.', maxsplit=1)[0])


class KeyValueStore:
    """TcEx Module"""

    def __init__(
        self,
        session_tc: TcSession,
        tc_kvstore_host: str,
        tc_kvstore_port: int,
        tc_kvstore_type: str,
    ):
        """Initialize the class properties."""
        self.session_tc = session_tc
        self.tc_kvstore_host = tc_kvstore_host
        self.tc_kvstore_port = tc_kvstore_port
        self.tc_kvstore_type = tc_kvstore_type

        # properties
        self.log = _logger

    @scoped_property
    def client(self) -> KeyValueApi | KeyValueMock | KeyValueRedis:
        """Return the correct KV store for this execution.

        The TCKeyValueAPI KV store is limited to two operations (create and read),
        while the Redis kvstore wraps a few other Redis methods.
        """
        if self.tc_kvstore_type == 'Redis':
            # submodule doesn't have scoped_property decorator, so resolution of type doesn't work
            return KeyValueRedis(self.redis_client)  # type: ignore

        if self.tc_kvstore_type == 'TCKeyValueAPI':
            return KeyValueApi(self.session_tc)  # pylint: disable=no-member

        if self.tc_kvstore_type == 'Mock':
            self.log.warning(
                'Using mock key-value store. '
                'This should *never* happen when running in-platform.'
            )
            return KeyValueMock()

        raise RuntimeError(f'Invalid KV Store Type: ({self.tc_kvstore_type})')

    @staticmethod
    def get_redis_client(
        host: str, port: int, db: int = 0, blocking_pool: bool = False, **kwargs
    ) -> Redis:
        """Return a *new* instance of Redis client.

        For a full list of kwargs see https://redis-py.readthedocs.io/en/latest/#redis.Connection.

        Args:
            host: The REDIS host. Defaults to localhost.
            port: The REDIS port. Defaults to 6379.
            db: The REDIS db. Defaults to 0.
            blocking_pool: Use BlockingConnectionPool instead of ConnectionPool.
            **kwargs: Additional keyword arguments.

        Keyword Args:
            errors (str): The REDIS errors policy (e.g. strict).
            max_connections (int): The maximum number of connections to REDIS.
            password (str): The REDIS password.
            socket_timeout (int): The REDIS socket timeout.
            timeout (int): The REDIS Blocking Connection Pool timeout value.
        """
        return RedisClient(
            host=host, port=port, db=db, blocking_pool=blocking_pool, **kwargs
        ).client

    @scoped_property
    def redis_client(self) -> Redis:
        """Return redis client instance configure for Playbook/Service Apps."""
        return self.get_redis_client(
            host=self.tc_kvstore_host,
            port=self.tc_kvstore_port,
            db=0,
        )
