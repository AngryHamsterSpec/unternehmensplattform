"""Die Originaldemo muss auch bei fehlgeschlagener Testbereinigung wieder starten."""

import unittest
from unittest.mock import call, patch

from check_restore import SOURCE, cleanup, paused_worker


class RestoreCleanupTests(unittest.TestCase):
    def test_resume_original_after_success(self):
        with patch("check_restore.command") as command:
            cleanup("phase1-restore-test", True)
        self.assertEqual(
            command.call_args_list,
            [
                call("phase1-restore-test", "down", "--volumes", "--remove-orphans"),
                call(
                    SOURCE,
                    "up",
                    "-d",
                    "--no-deps",
                    "--wait",
                    "--wait-timeout",
                    "120",
                    "web",
                    timeout=150,
                ),
            ],
        )

    def test_resume_original_even_if_test_teardown_fails(self):
        with (
            patch(
                "check_restore.command", side_effect=[RuntimeError("Testabbruch"), None]
            ) as command,
            self.assertRaises(RuntimeError),
        ):
            cleanup("phase1-restore-test", True)
        self.assertEqual(command.call_count, 2)
        self.assertEqual(command.call_args.args[0], SOURCE)

    def test_database_only_does_not_touch_original_proxy(self):
        with patch("check_restore.command") as command:
            cleanup("phase1-restore-test", False)
        command.assert_called_once_with(
            "phase1-restore-test", "down", "--volumes", "--remove-orphans"
        )


class RestoreWorkerTests(unittest.TestCase):
    def test_worker_resumes_after_backup_failure(self):
        with patch("check_restore.command") as command, self.assertRaises(RuntimeError):
            with paused_worker():
                raise RuntimeError("Synthetischer Backupfehler")
        self.assertEqual(
            command.call_args_list,
            [
                call(SOURCE, "stop", "data-worker", "intelligence-worker"),
                call(
                    SOURCE, "up", "-d", "--no-deps", "--wait", "data-worker", "intelligence-worker"
                ),
            ],
        )
