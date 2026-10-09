"""Operations shared by the migrations."""

from django.contrib.postgres.operations import AddIndexConcurrently


class AddIndexConcurrentlyIfMissing(AddIndexConcurrently):
    """
    Create the index unless a valid one with the same name already exists.

    Until an index is valid, the queries relying on it read the whole table. On large
    databases such an index is thus created by hand before the release is deployed:
    the migration must then succeed without building it again.
    """

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        # Look the index up by name: no row means it does not exist, otherwise the row
        # holds the flag Postgres sets once a concurrent build is complete.
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(
                "SELECT indisvalid FROM pg_index WHERE indexrelid = to_regclass(%s)",
                [schema_editor.quote_name(self.index.name)],
            )
            row = cursor.fetchone()

        if row is not None:
            # The index exists and is valid: it was created ahead of the migration,
            # there is nothing to do.
            if row[0]:
                return

            # The index exists but is invalid: a previous build was interrupted and
            # left an index that queries ignore. CREATE INDEX would fail on its name,
            # so drop it first. Like the build, DROP INDEX CONCURRENTLY does not lock
            # writes on the table and cannot run inside a transaction.
            self._ensure_not_in_transaction(schema_editor)
            model = to_state.apps.get_model(app_label, self.model_name)
            schema_editor.remove_index(model, self.index, concurrently=True)

        # The index does not exist, or was just dropped: build it.
        super().database_forwards(app_label, schema_editor, from_state, to_state)
