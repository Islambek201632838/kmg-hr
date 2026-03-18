import importlib
from logging.config import fileConfig

from sqlalchemy import create_engine
from alembic import context

from app.config import settings
from app.database import LocalBase


def import_all_models():
    modules = [
        "app.models",
    ]
    for module in modules:
        importlib.import_module(module)


import_all_models()

target_metadata = LocalBase.metadata

config = context.config

url = settings.local_db_url.replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

connectable = create_engine(url)


def run_migrations_offline() -> None:
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
