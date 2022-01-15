##
## Author:    Roger D. Serwy
## Copyright: 2020-2022, Roger D. Serwy
##            All rights reserved.
## License:   BSD 2-Clause, see LICENSE file from project
##

import relmod
import unittest
import sys
import io


class TestRunner(unittest.TestCase):

    def setUp(self):
        self.NULL = io.StringIO()

    def test_runtest_decorator(self):

        check = set()
        @relmod.runtest(None, stream=self.NULL)
        class TestNested(unittest.TestCase):
            def test_1(self):
                check.add(1)
            def test_2(self):
                check.add(2)

        self.assertEqual(check, set([1, 2]))


    def test_runtest_names(self):

        check = set()
        @relmod.runtest(None, test_names='test_2', stream=self.NULL)
        class TestNested(unittest.TestCase):
            def test_1(self):
                check.add(1)
            def test_2(self):
                check.add(2)

        self.assertEqual(check, set([2]))


    @relmod.testfocus
    def test_testfocus(self):

        check = []
        @relmod.runtest(None, test_names='test_2', stream=self.NULL)
        class TestNested(unittest.TestCase):

            @relmod.testfocus  # override the provided test_2
            def test_1(self):
                check.append(1)

            def test_2(self):
                check.append(2)

        self.assertEqual(check, [1])


def run():
    unittest.main(__name__, verbosity=2)

if __name__ == '__main__':
    run()
