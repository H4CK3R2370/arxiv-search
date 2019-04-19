# """
# Integration and search behavior tests.
#
# These tests evaluate the behavior of :mod:`.index` against a live Elasticsearch
# cluster.
# """
#
# from unittest import TestCase
# import os
# import subprocess
# import time
# from datetime import datetime
# from pytz import timezone
#
# from search.factory import create_ui_web_app
# from search.services import index
# from search.agent.consumer import MetadataRecordProcessor
# from search.domain import SimpleQuery,  AdvancedQuery, DateRange, \
#     FieldedSearchList, FieldedSearchTerm
#
# EASTERN = timezone('US/Eastern')
#
#
# class TestSearchIntegration(TestCase):
#     """Indexes a limited set of documents, and tests search behavior."""
#
#     __test__ = int(bool(os.environ.get('WITH_INTEGRATION', False)))
#
#     @classmethod
#     def setUpClass(cls):
#         """Spin up ES and index documents."""
#         build_es = subprocess.run(
#             "docker build ./"
#             " -t arxiv/elasticsearch"
#             " -f ./Dockerfile-elasticsearch",
#             stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
#         )
#         start_es = subprocess.run(
#             "docker run -d -p 9201:9200 arxiv/elasticsearch",
#             stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
#         if start_es.returncode != 0 or build_es.returncode != 0:
#             raise RuntimeError('Could not start elasticsearch.')
#
#         cls.es_container = start_es.stdout.decode('ascii').strip()
#         os.environ['ELASTICSEARCH_SERVICE_HOST'] = 'localhost'
#         os.environ['ELASTICSEARCH_SERVICE_PORT'] = "9201"
#         os.environ['ELASTICSEARCH_PORT_9201_PROTO'] = "http"
#         os.environ['ELASTICSEARCH_VERIFY'] = 'false'
#
#         # Build and start the docmeta stub.
#         build_docmeta = subprocess.run(
#             "docker build ./"
#             " -t arxiv/search-metadata"
#             " -f ./Dockerfile-metadata",
#             stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
#         )
#         start_docmeta = subprocess.run(
#             "docker run -d -p 9000:8000 arxiv/search-metadata",
#             stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
#
#         if start_docmeta.returncode != 0 or build_docmeta.returncode != 0:
#             raise RuntimeError('Could not start docmeta.')
#
#         cls.md_container = start_docmeta.stdout.decode('ascii').strip()
#         os.environ['METADATA_ENDPOINT'] = 'http://localhost:9000/docmeta/'
#
#         cls.app = create_ui_web_app()
#         # app.app_context().push()
#
#         print('Waiting for ES cluster to be available...')
#         time.sleep(12)
#         with cls.app.app_context():
#             while True:
#                 if index.SearchSession.cluster_available():
#                     index.SearchSession.create_index()
#                     time.sleep(2)
#                     break
#                 time.sleep(5)
#
#         to_index = [
#             "1712.04442",    # flux capacitor
#             "1511.07473",    # flux capacitor
#             "1604.04228",    # flux capacitor
#             "1403.6219",     # λ
#             "1404.3450",     # $Z_1$
#             "1703.09067",    # $\Lambda\Lambda$
#             "1408.6682",     # $\Lambda$
#             "1607.05107",    # Schröder
#             "1509.08727",    # Schroder
#             "1710.01597",    # Schroeder
#             "1708.07156",    # w w
#             "1401.1012",     # Wonmin Son
#             "0711.0418"      # disk, switch
#         ]
#         with cls.app.app_context():
#             cls.processor = MetadataRecordProcessor()
#             cls.processor.index_papers(to_index)
#         time.sleep(5)    # Give a few seconds for docs to be available.
#
#     @classmethod
#     def tearDownClass(cls):
#         """Tear down Elasticsearch once all tests have run."""
#         stop_es = subprocess.run(f"docker rm -f {cls.es_container}",
#                                  stdout=subprocess.PIPE,
#                                  stderr=subprocess.PIPE,
#                                  shell=True)
#         stop_md = subprocess.run(f"docker rm -f {cls.md_container}",
#                                  stdout=subprocess.PIPE,
#                                  stderr=subprocess.PIPE,
#                                  shell=True)
#         del cls.app
#
#     def test_simple_search_all_fields(self):
#         """Scenario: simple term search across all fields."""
#         # Given search term is "flux capacitor"
#         # And selected field to search is "All fields"
#         # When a user performs a search...
#         query = SimpleQuery(
#             order='',
#             size=10,
#             field='all',
#             value='flux capacitor'
#         )
#         with self.app.app_context():
#             document_set = index.SearchSession.search(query)
#         # All entries contain a metadata field that contains either "flux"
#         # or "capacitor".
#         self.assertEqual(len(document_set.results), 3)
#         for item in document_set.results:
#             self.assertTrue("flux" in str(item) or "capacitor" in str(item),
#                             "Should have a metadata field that contains either"
#                             " 'flux' or 'capacitor'.")
#
#
#     def test_simple_search_for_utf8(self):
#         """Scenario: simple search for utf8 terms."""
#
#         # A search for a TeX expression should match similar metadata strings.
#         query = SimpleQuery(
#             order='',
#             size=10,
#             field='all',
#             value='λ'
#         )
#         with self.app.app_context():
#             document_set = index.SearchSession.search(query)
#         self.assertEqual(len(document_set.results), 1)
#         self.assertEqual(document_set.results[0].id, "1403.6219")
#
#     def test_simple_search_for_texism(self):
#         """Scenario: simple search for TeX terms."""
#         query = SimpleQuery(
#             order='',
#             size=10,
#             field='all',
#             value='$Z_1(4475)$'
#         )
#         with self.app.app_context():
#             document_set = index.SearchSession.search(query)
#         self.assertEqual(len(document_set.results), 1)
#         self.assertEqual(document_set.results[0].id, "1404.3450")
#
#     def test_simple_search_for_texism2(self):
#         """Scenario: simple search for TeX terms."""
#         query = SimpleQuery(
#             order='',
#             size=10,
#             field='all',
#             value='$\Lambda$'
#         )
#         with self.app.app_context():
#             document_set = index.SearchSession.search(query)
#         self.assertEqual(len(document_set.results), 1)
#
#         query = SimpleQuery(
#             order='',
#             size=10,
#             field='all',
#             value='$\Lambda\Lambda$'
#         )
#         with self.app.app_context():
#             document_set = index.SearchSession.search(query)
#         self.assertEqual(len(document_set.results), 2)
#
#     def test_advanced_date_range_search(self):
#         """Scenario: date range search."""
#         search_year = 2015
#         query = AdvancedQuery(
#             order='',
#             size=10,
#             date_range=DateRange(
#                 start_date=datetime(year=2015, month=1, day=1, tzinfo=EASTERN),
#                 end_date=datetime(year=2016, month=1, day=1, tzinfo=EASTERN)
#             )
#         )
#         with self.app.app_context():
#             document_set = index.SearchSession.search(query)
#         self.assertEqual(len(document_set.results), 3,
#                          "Should be three results from 2015.")
#         _ids = [r.paper_id_v for r in document_set.results]
#         self.assertIn("1509.08727v1", _ids,
#                       "Results should include older versions of papers.")
#         self.assertIn("1408.6682v2", _ids)
#         self.assertIn("1511.07473v1", _ids)
#
#     def test_advanced_multiple_search_terms(self):
#         """Scenario: multiple terms search success."""
#         query = AdvancedQuery(
#             order='',
#             size=10,
#             terms=FieldedSearchList([
#                 FieldedSearchTerm(operator='AND', field='author',
#                                   term='schroder'),
#                 FieldedSearchTerm(operator='OR', field='title',
#                                   term='jqk'),
#             ])
#         )
#         with self.app.app_context():
#             document_set = index.SearchSession.search(query)
#         _ids = [r.paper_id for r in document_set.results]
#         self.assertEqual(len(document_set.results), 3)
#         self.assertIn("1607.05107", _ids, "Schröder should match.")
#         self.assertIn("1509.08727", _ids, "Schroder should match.")
#
#     def test_advanced_multiple_search_terms_all_fields(self):
#         """Scenario: multiple terms search success."""
#         query = AdvancedQuery(
#             order='',
#             size=10,
#             include_older_versions=True,
#             terms=FieldedSearchList([
#                 FieldedSearchTerm(operator='AND', field='all',
#                                   term='disk'),
#                 FieldedSearchTerm(operator='AND', field='all',
#                                   term='switch'),
#             ])
#         )
#         with self.app.app_context():
#             document_set = index.SearchSession.search(query)
#         _ids = [r.id for r in document_set.results]
#         self.assertEqual(len(document_set.results), 2)
#         self.assertIn("0711.0418", _ids, "'disk' should match in title, "
#                                          "'switch' in abstract")
#
#     def test_advanced_multiple_search_terms_fails(self):
#         """Scenario: multiple terms with no results."""
#         query = AdvancedQuery(
#             order='',
#             size=10,
#             terms=FieldedSearchList([
#                 FieldedSearchTerm(operator='AND', field='author',
#                                   term='schroder'),
#                 FieldedSearchTerm(operator='AND', field='title', term='jqk'),
#             ])
#         )
#         with self.app.app_context():
#             document_set = index.SearchSession.search(query)
#         self.assertEqual(len(document_set.results), 0)
