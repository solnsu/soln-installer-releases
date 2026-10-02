import unittest
from sync_gitcode import SyncError, checksums, safe_name


class ValidationTests(unittest.TestCase):
    def test_checksums_cover_every_binary(self):
        digest = 'a' * 64
        self.assertEqual(checksums(f'{digest}  Soln.exe\n', ['Soln.exe']), {'Soln.exe': digest})
        with self.assertRaises(SyncError):
            checksums(f'{digest}  Soln.exe\n', ['Soln.exe', 'Soln.dmg'])

    def test_rejects_duplicates_and_invalid_hashes(self):
        line = 'a' * 64 + '  Soln.exe\n'
        for text in [line + line, 'invalid  Soln.exe\n']:
            with self.assertRaises(SyncError):
                checksums(text, ['Soln.exe'])

    def test_rejects_path_traversal_and_unsafe_filenames(self):
        for name in ['../Soln.exe', '/Soln.exe', 'a/b.exe', 'a\\b.exe', 'a\n.exe', '']:
            with self.assertRaises(SyncError):
                safe_name(name)
        self.assertEqual(safe_name('Soln.Setup.1.0.0.exe'), 'Soln.Setup.1.0.0.exe')
