"""Unit tests for :mod:`search.agent`."""

from unittest import TestCase, mock

from search.domain import DocMeta, Document
from search.services import metadata, index
from search.agent import consumer

# type: ignore


class TestIndexPaper(TestCase):
    """Re-index all versions of an arXiv paper."""

    def setUp(self):
        """Initialize a :class:`.MetadataRecordProcessor`."""
        self.checkpointer = mock.MagicMock()
        self.args = ('foo', '1', 'a1b2c3d4', 'qwertyuiop', 'us-east-1',
                     self.checkpointer)

    @mock.patch('boto3.client')
    @mock.patch('search.agent.consumer.index.SearchSession')
    @mock.patch('search.agent.consumer.transform')
    @mock.patch('search.agent.consumer.metadata')
    def test_paper_has_one_version(self, mock_meta, mock_tx, mock_idx,
                                   mock_client_factory):
        """The arXiv paper has only one version."""
        mock_client = mock.MagicMock()
        mock_waiter = mock.MagicMock()
        mock_client.get_waiter.return_value = mock_waiter
        mock_client_factory.return_value = mock_client
        processor = consumer.MetadataRecordProcessor(*self.args)

        mock_docmeta = DocMeta(version=1, paper_id='1234.56789', title='foo',
                               submitted_date='2001-03-02T03:04:05-400')
        mock_meta.retrieve.return_value = mock_docmeta
        mock_meta.bulk_retrieve.return_value = [mock_docmeta]

        mock_doc = Document(version=1, paper_id='1234.56789', title='foo',
                            submitted_date=['2001-03-02T03:04:05-400'])
        mock_tx.to_search_document.return_value = mock_doc

        processor.index_paper('1234.56789')

        mock_idx.bulk_add_documents.assert_called_once_with([mock_doc])

    @mock.patch('boto3.client')
    @mock.patch('search.agent.consumer.index.SearchSession')
    @mock.patch('search.agent.consumer.transform')
    @mock.patch('search.agent.consumer.metadata')
    def test_paper_has_three_versions(self, mock_meta, mock_tx, mock_idx,
                                      mock_client_factory):
        """The arXiv paper has three versions."""
        mock_client = mock.MagicMock()
        mock_waiter = mock.MagicMock()
        mock_client.get_waiter.return_value = mock_waiter
        mock_client_factory.return_value = mock_client
        processor = consumer.MetadataRecordProcessor(*self.args)

        mock_dm_1 = DocMeta(version=1, paper_id='1234.56789', title='foo',
                            submitted_date='2001-03-02T03:04:05-400')
        mock_dm_2 = DocMeta(version=2, paper_id='1234.56789', title='foo',
                            submitted_date='2001-03-03T03:04:05-400')
        mock_dm_3 = DocMeta(version=3, paper_id='1234.56789', title='foo',
                            submitted_date='2001-03-04T03:04:05-400')
        mock_meta.retrieve.side_effect = [mock_dm_3, mock_dm_1, mock_dm_2]

        mock_meta.bulk_retrieve.return_value = [
            mock_dm_3, mock_dm_1, mock_dm_2, mock_dm_3
        ]

        mock_doc_1 = Document(version=1, paper_id='1234.56789', title='foo',
                              submitted_date=['2001-03-02T03:04:05-400'],
                              submitted_date_all=[
                                '2001-03-02T03:04:05-400',
                              ])
        mock_doc_2 = Document(version=2, paper_id='1234.56789', title='foo',
                              submitted_date=['2001-03-03T03:04:05-400'],
                              submitted_date_all=[
                                '2001-03-02T03:04:05-400',
                                '2001-03-03T03:04:05-400',
                              ])
        mock_doc_3 = Document(version=3, paper_id='1234.56789', title='foo',
                              submitted_date=['2001-03-04T03:04:05-400'],
                              submitted_date_all=[
                                '2001-03-02T03:04:05-400',
                                '2001-03-03T03:04:05-400',
                                '2001-03-04T03:04:05-400'
                              ])
        mock_tx.to_search_document.side_effect = [
            mock_doc_3, mock_doc_1, mock_doc_2, mock_doc_3
        ]
        processor.index_paper('1234.56789')
        self.assertEqual(mock_meta.bulk_retrieve.call_count, 1,
                         "Metadata should be retrieved for current version"
                         " with bulk_retrieve")
        self.assertEqual(mock_meta.retrieve.call_count, 0,
                         "Metadata should be retrieved for each non-current"
                         " version")

        mock_idx.bulk_add_documents.assert_called_once_with(
            [mock_doc_3, mock_doc_1, mock_doc_2, mock_doc_3])


class TestAddToIndex(TestCase):
    """Add a search document to the index."""

    def setUp(self):
        """Initialize a :class:`.MetadataRecordProcessor`."""
        self.checkpointer = mock.MagicMock()
        self.args = ('foo', '1', 'a1b2c3d4', 'qwertyuiop', 'us-east-1',
                     self.checkpointer)

    @mock.patch('boto3.client')
    @mock.patch('search.agent.consumer.index.SearchSession')
    def test_add_document_succeeds(self, mock_index, mock_client_factory):
        """The search document is added successfully."""
        mock_client = mock.MagicMock()
        mock_waiter = mock.MagicMock()
        mock_client.get_waiter.return_value = mock_waiter
        mock_client_factory.return_value = mock_client
        processor = consumer.MetadataRecordProcessor(*self.args)
        try:
            processor._add_to_index(Document())
        except Exception as ex:
            self.fail(ex)
        mock_index.add_document.assert_called_once()

    @mock.patch('boto3.client')
    @mock.patch('search.agent.consumer.index.SearchSession')
    def test_index_raises_index_connection_error(self, mock_index,
                                                 mock_client_factory):
        """The index raises :class:`.index.IndexConnectionError`."""
        mock_client = mock.MagicMock()
        mock_waiter = mock.MagicMock()
        mock_client.get_waiter.return_value = mock_waiter
        mock_client_factory.return_value = mock_client
        processor = consumer.MetadataRecordProcessor(*self.args)

        mock_index.add_document.side_effect = index.IndexConnectionError
        with self.assertRaises(consumer.IndexingFailed):
            processor._add_to_index(Document())

    @mock.patch('boto3.client')
    @mock.patch('search.agent.consumer.index.SearchSession')
    def test_index_raises_unhandled_error(self, mock_index,
                                          mock_client_factory):
        """The index raises an unhandled exception."""
        mock_client = mock.MagicMock()
        mock_waiter = mock.MagicMock()
        mock_client.get_waiter.return_value = mock_waiter
        mock_client_factory.return_value = mock_client
        processor = consumer.MetadataRecordProcessor(*self.args)

        mock_index.add_document.side_effect = RuntimeError
        with self.assertRaises(consumer.IndexingFailed):
            processor._add_to_index(Document())


class TestBulkAddToIndex(TestCase):
    """Add multiple search documents to the index in bulk."""

    def setUp(self):
        """Initialize a :class:`.MetadataRecordProcessor`."""
        self.checkpointer = mock.MagicMock()
        self.args = ('foo', '1', 'a1b2c3d4', 'qwertyuiop', 'us-east-1',
                     self.checkpointer)

    @mock.patch('boto3.client')
    @mock.patch('search.agent.consumer.index.SearchSession')
    def test_bulk_add_documents_succeeds(self, mock_index,
                                         mock_client_factory):
        """The search document is added successfully."""
        mock_client = mock.MagicMock()
        mock_waiter = mock.MagicMock()
        mock_client.get_waiter.return_value = mock_waiter
        mock_client_factory.return_value = mock_client
        processor = consumer.MetadataRecordProcessor(*self.args)
        try:
            processor._bulk_add_to_index([Document()])
        except Exception as ex:
            self.fail(ex)
        mock_index.bulk_add_documents.assert_called_once()

    @mock.patch('boto3.client')
    @mock.patch('search.agent.consumer.index.SearchSession')
    def test_index_raises_index_connection_error(self, mock_index,
                                                 mock_client_factory):
        """The index raises :class:`.index.IndexConnectionError`."""
        mock_client = mock.MagicMock()
        mock_waiter = mock.MagicMock()
        mock_client.get_waiter.return_value = mock_waiter
        mock_client_factory.return_value = mock_client
        processor = consumer.MetadataRecordProcessor(*self.args)

        mock_index.bulk_add_documents.side_effect = index.IndexConnectionError
        with self.assertRaises(consumer.IndexingFailed):
            processor._bulk_add_to_index([Document()])

    @mock.patch('boto3.client')
    @mock.patch('search.agent.consumer.index.SearchSession')
    def test_index_raises_unhandled_error(self, mock_index,
                                          mock_client_factory):
        """The index raises an unhandled exception."""
        mock_client = mock.MagicMock()
        mock_waiter = mock.MagicMock()
        mock_client.get_waiter.return_value = mock_waiter
        mock_client_factory.return_value = mock_client
        processor = consumer.MetadataRecordProcessor(*self.args)

        mock_index.bulk_add_documents.side_effect = RuntimeError
        with self.assertRaises(consumer.IndexingFailed):
            processor._bulk_add_to_index([Document()])


class TestTransformToDocument(TestCase):
    """Transform metadata into a search document."""

    def setUp(self):
        """Initialize a :class:`.MetadataRecordProcessor`."""
        self.checkpointer = mock.MagicMock()
        self.args = ('foo', '1', 'a1b2c3d4', 'qwertyuiop', 'us-east-1',
                     self.checkpointer)

    @mock.patch('boto3.client')
    @mock.patch('search.agent.consumer.transform')
    def test_transform_raises_exception(self, mock_transform,
                                        mock_client_factory):
        """The transform module raises an exception."""
        mock_client = mock.MagicMock()
        mock_waiter = mock.MagicMock()
        mock_client.get_waiter.return_value = mock_waiter
        mock_client_factory.return_value = mock_client
        processor = consumer.MetadataRecordProcessor(*self.args)

        mock_transform.to_search_document.side_effect = RuntimeError
        with self.assertRaises(consumer.DocumentFailed):
            processor._transform_to_document(DocMeta())


class TestGetMetadata(TestCase):
    """Retrieve metadata for an arXiv e-print."""

    def setUp(self):
        """Initialize a :class:`.MetadataRecordProcessor`."""
        self.checkpointer = mock.MagicMock()
        self.args = ('foo', '1', 'a1b2c3d4', 'qwertyuiop', 'us-east-1',
                     self.checkpointer)

    @mock.patch('boto3.client')
    @mock.patch('search.agent.consumer.metadata')
    def test_metadata_service_returns_metadata(self, mock_metadata,
                                               mock_client_factory):
        """The metadata service returns valid metadata."""
        mock_client = mock.MagicMock()
        mock_waiter = mock.MagicMock()
        mock_client.get_waiter.return_value = mock_waiter
        mock_client_factory.return_value = mock_client
        processor = consumer.MetadataRecordProcessor(*self.args)

        docmeta = DocMeta()
        mock_metadata.retrieve.return_value = docmeta
        self.assertEqual(docmeta, processor._get_metadata('1234.5678'),
                         "The metadata is returned.")

    @mock.patch('boto3.client')
    @mock.patch('search.agent.consumer.metadata')
    def test_metadata_service_raises_connection_error(self, mock_metadata,
                                                      mock_client_factory):
        """The metadata service raises :class:`.metadata.ConnectionFailed`."""
        mock_metadata.RequestFailed = metadata.RequestFailed
        mock_metadata.ConnectionFailed = metadata.ConnectionFailed

        mock_client = mock.MagicMock()
        mock_waiter = mock.MagicMock()
        mock_client.get_waiter.return_value = mock_waiter
        mock_client_factory.return_value = mock_client
        processor = consumer.MetadataRecordProcessor(*self.args)

        mock_metadata.retrieve.side_effect = metadata.ConnectionFailed
        with self.assertRaises(consumer.IndexingFailed):
            processor._get_metadata('1234.5678')

    @mock.patch('boto3.client')
    @mock.patch('search.agent.consumer.metadata')
    def test_metadata_service_raises_request_error(self, mock_metadata,
                                                   mock_client_factory):
        """The metadata service raises :class:`.metadata.RequestFailed`."""
        mock_metadata.RequestFailed = metadata.RequestFailed
        mock_metadata.ConnectionFailed = metadata.ConnectionFailed

        mock_client = mock.MagicMock()
        mock_waiter = mock.MagicMock()
        mock_client.get_waiter.return_value = mock_waiter
        mock_client_factory.return_value = mock_client

        processor = consumer.MetadataRecordProcessor(*self.args)

        mock_metadata.retrieve.side_effect = metadata.RequestFailed
        with self.assertRaises(consumer.DocumentFailed):
            processor._get_metadata('1234.5678')

    @mock.patch('boto3.client')
    @mock.patch('search.agent.consumer.metadata')
    def test_metadata_service_raises_bad_response(self, mock_metadata,
                                                  mock_client_factory):
        """The metadata service raises :class:`.metadata.BadResponse`."""
        mock_metadata.RequestFailed = metadata.RequestFailed
        mock_metadata.ConnectionFailed = metadata.ConnectionFailed
        mock_metadata.BadResponse = metadata.BadResponse

        mock_client = mock.MagicMock()
        mock_waiter = mock.MagicMock()
        mock_client.get_waiter.return_value = mock_waiter
        mock_client_factory.return_value = mock_client
        processor = consumer.MetadataRecordProcessor(*self.args)

        mock_metadata.retrieve.side_effect = metadata.BadResponse
        with self.assertRaises(consumer.DocumentFailed):
            processor._get_metadata('1234.5678')
