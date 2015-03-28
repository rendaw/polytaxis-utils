import unittest
import sqlite3

from mock import patch

import ptmonitor.common
import ptmonitor.main

db = sqlite3.connect(':memory:').cursor()
ptmonitor.common.init_db(db)
ptmonitor.main.conn = db

class TestWrite(unittest.TestCase):
    def setUp(self):
        db.execute('DELETE FROM tags')
        db.execute('DELETE FROM files')

    def test_split_abs_path(self):
        self.assertEqual(
            list(ptmonitor.main.split_abs_path('/a/b/c.txt')),
            ['/', 'a', 'b', 'c.txt'],
        )
    
    def test_split_abs_path_win(self):
        self.assertEqual(
            list(ptmonitor.main.split_abs_path('c:\\a\\b\\c.txt')),
            ['c:', 'a', 'b', 'c.txt'],
        )

    def test_create_file(self):
        tags = {'a': set(['b'])}
        fid = ptmonitor.main.create_file(
            '/what/you/at/gamma.vob', 
            tags,
        )
        ptmonitor.main.add_tags(fid, tags)
        self.assertEqual(
            db.execute('SELECT * FROM files').fetchall(),
            [
                (1, None, u'/', None),
                (2, 1, u'what', None),
                (3, 2, u'you', None),
                (4, 3, u'at', None),
                (5, 4, u'gamma.vob', 'a=b\n'),
            ],
        )
        self.assertEqual(
            db.execute('SELECT * FROM tags').fetchall(),
            [
                (u'a=b', 5),
            ],
        )

        ptmonitor.main.remove_tags(fid)
        self.assertEqual(
            db.execute('SELECT * FROM tags').fetchall(),
            [],
        )

        ptmonitor.main.delete_file(fid)
        self.assertEqual(
            db.execute('SELECT * FROM files').fetchall(),
            [],
        )

class TestQueryDB(unittest.TestCase):
    def setUp(self):
        db.execute('DELETE FROM tags')
        db.execute('DELETE FROM files')
        self.tag_sets = [
            {
                'red': set([None]),
                'juicy': set([None]),
                'date': set(['99']),
            },
            {
                'red': set([None]),
                'date': set(['98']),
            },
            {
                'under': set([None]),
                'length': set(['7']),
                'date': set(['103']),
            },
        ]
        self.files = [
            ('/what/you/at/gamma.vob', self.tag_sets[0]),
            ('/home/hebwy/loog.txt', self.tag_sets[1]),
            ('/home/hebwy/noxx', self.tag_sets[2]),
        ]
        self.fids = []
        for filename, tags in self.files:
            fid = ptmonitor.main.create_file(filename, tags)
            self.fids.append(fid)
            ptmonitor.main.add_tags(fid, tags)
        with patch('ptmonitor.common.open_db', new=lambda: db):
            self.query = ptmonitor.common.QueryDB()

    def test_query_none(self):
        self.assertItemsEqual(
            list(self.query.query([], [])),
            [
                {'fid': self.fids[0], 'segment': u'gamma.vob', 'tags': self.tag_sets[0]},
                {'fid': self.fids[1], 'segment': u'loog.txt', 'tags': self.tag_sets[1]},
                {'fid': self.fids[2], 'segment': u'noxx', 'tags': self.tag_sets[2]},
            ],
        )

    def test_query_include(self):
        self.assertItemsEqual(
            list(self.query.query([('red', None)], [])),
            [
                {'fid': self.fids[0], 'segment': u'gamma.vob', 'tags': self.tag_sets[0]},
                {'fid': self.fids[1], 'segment': u'loog.txt', 'tags': self.tag_sets[1]},
            ],
        )
    
    def test_query_exclude(self):
        self.assertItemsEqual(
            list(self.query.query([], [('juicy', None)])),
            [
                {'fid': self.fids[1], 'segment': u'loog.txt', 'tags': self.tag_sets[1]},
                {'fid': self.fids[2], 'segment': u'noxx', 'tags': self.tag_sets[2]},
            ],
        )

    def test_query_path(self):
        self.assertEqual(
            self.query.query_path(self.fids[1]),
            '/home/hebwy/loog.txt',
        )

    def test_query_tags_prefix(self):
        self.assertEqual(
            list(self.query.query_tags('prefix', 'date=')),
            [
                u'date=103',
                u'date=98', 
                u'date=99', 
            ],
        )

    def test_query_tags_anywhere(self):
        self.assertEqual(
            list(self.query.query_tags('anywhere', 'r')),
            [
                u'red', 
                u'under', 
            ],
        )

class TestCommon(unittest.TestCase):
    def test_sort(self):
        rows = [
            {'fid': 0, 'segment': u'0', 'tags': {'1': 'a', '2': 'a'}},
            {'fid': 1, 'segment': u'1', 'tags': {'1': 'a', '2': 'b'}},
            {'fid': 2, 'segment': u'2', 'tags': {'1': 'b', '2': 'a'}},
        ]
        self.assertEqual(
            ptmonitor.common.sort([('asc', '1'), ('desc', '2')], rows),
            [
                {'fid': 1, 'segment': u'1', 'tags': {'1': 'a', '2': 'b'}},
                {'fid': 0, 'segment': u'0', 'tags': {'1': 'a', '2': 'a'}},
                {'fid': 2, 'segment': u'2', 'tags': {'1': 'b', '2': 'a'}},
            ],
        )
