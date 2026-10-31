import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from scripts.monitor_providers import (
    PROBE_RETRY_DELAY_SECONDS,
    CheckResult,
    check_jina,
    log_issue,
    main,
    open_github_issue,
    probe_with_retry,
    update_routing_priority,
    write_summary,
)


class TestMonitorProviders(unittest.TestCase):
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='base = ["jina", "duckduckgo"]')
    def test_update_routing_priority_basic(self, mock_file, mock_exists):
        update_routing_priority("jina")

        # Check that it was called to write
        mock_file.assert_called_with("scripts/routing.py", "w")
        handle = mock_file()
        # Find the write call that contains the updated list
        all_writes = "".join(call.args[0] for call in handle.write.call_args_list)
        self.assertIn('base = ["duckduckgo", "jina"]', all_writes)

    @patch("os.path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='base = [\n    "jina",\n    "duckduckgo"\n]',
    )
    def test_update_routing_priority_multiline(self, mock_file, mock_exists):
        update_routing_priority("jina")

        handle = mock_file()
        all_writes = "".join(call.args[0] for call in handle.write.call_args_list)
        self.assertIn('"duckduckgo",', all_writes)
        self.assertIn('"jina",', all_writes)
        # Check jina is after duckduckgo
        self.assertTrue(all_writes.find('"jina"') > all_writes.find('"duckduckgo"'))

    @patch("scripts.monitor_providers.get_session")
    def test_check_jina_healthy(self, mock_get_session):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Some markdown content"
        mock_get_session.return_value.get.return_value = mock_resp

        result, error = check_jina()
        self.assertEqual(result, CheckResult.HEALTHY)
        self.assertIsNone(error)

    @patch("scripts.monitor_providers.get_session")
    def test_check_jina_failed(self, mock_get_session):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_get_session.return_value.get.return_value = mock_resp

        result, error = check_jina()
        self.assertEqual(result, CheckResult.FAILED)
        self.assertIn("Status code 500", error)

    @patch("os.path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="# Provider Alert: jina unstable\n- **Date**: 2026-05-20",
    )
    @patch("scripts.monitor_providers.open_github_issue")
    def test_log_issue_duplicate(self, mock_github, mock_file, mock_exists):
        # We need to freeze time or mock datetime to test exact date matching if we want to be precise,
        # but for now we rely on the mocked read_data containing today's date (simulated)
        with patch("scripts.monitor_providers.datetime") as mock_date:
            mock_date.now.return_value.strftime.return_value = "2026-05-20"
            log_issue("jina", "Some error")

            # Should NOT append because it exists for today
            self.assertFalse(any(call.args[0] == "a" for call in mock_file.call_args_list))

    @patch("requests.post")
    @patch("requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test", "GITHUB_REPOSITORY": "owner/repo"})
    def test_open_github_issue_deduplication(self, mock_get, mock_post):
        # Mock existing issue
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [{"title": "Provider Alert: jina unstable"}]

        open_github_issue("jina", "error")

        # post (creation) should NOT be called
        mock_post.assert_not_called()


class TestProbeRetry(unittest.TestCase):
    @patch("scripts.monitor_providers.time.sleep")
    def test_healthy_first_probe_is_not_retried(self, mock_sleep):
        probe = MagicMock(return_value=(CheckResult.HEALTHY, None))

        result, error, retry_note = probe_with_retry("jina", probe)

        self.assertEqual(result, CheckResult.HEALTHY)
        self.assertIsNone(error)
        self.assertIsNone(retry_note)
        self.assertEqual(probe.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("scripts.monitor_providers.time.sleep")
    def test_recovers_on_second_probe(self, mock_sleep):
        probe = MagicMock(
            side_effect=[
                (CheckResult.FAILED, "Status code 503"),
                (CheckResult.HEALTHY, None),
            ]
        )

        result, error, retry_note = probe_with_retry("jina", probe)

        self.assertEqual(result, CheckResult.HEALTHY)
        self.assertIsNone(error)
        self.assertEqual(retry_note, "Status code 503")
        self.assertEqual(probe.call_count, 2)
        mock_sleep.assert_called_once_with(PROBE_RETRY_DELAY_SECONDS)

    @patch("scripts.monitor_providers.time.sleep")
    def test_fails_only_after_both_probes(self, mock_sleep):
        probe = MagicMock(return_value=(CheckResult.FAILED, "Status code 500"))

        result, error, retry_note = probe_with_retry("serper", probe)

        self.assertEqual(result, CheckResult.FAILED)
        self.assertIn("500", error)
        self.assertIsNone(retry_note)
        self.assertEqual(probe.call_count, 2)
        mock_sleep.assert_called_once()

    @patch("scripts.monitor_providers.write_summary")
    @patch("scripts.monitor_providers.time.sleep")
    @patch("scripts.monitor_providers.log_issue")
    @patch("scripts.monitor_providers.update_routing_priority")
    def test_main_does_not_deprioritize_when_retry_recovers(
        self, mock_update, mock_log, mock_sleep, mock_summary
    ):
        healthy = MagicMock(return_value=(CheckResult.HEALTHY, None))
        flaky = MagicMock(
            side_effect=[
                (CheckResult.FAILED, "Status code 503"),
                (CheckResult.HEALTHY, None),
            ]
        )

        with patch.multiple(
            "scripts.monitor_providers",
            check_jina=flaky,
            check_firecrawl=healthy,
            check_tavily=healthy,
            check_serper=healthy,
            check_exa=healthy,
            check_mistral_websearch=healthy,
            check_mistral_browser=healthy,
            check_duckduckgo=healthy,
        ):
            main()

        mock_update.assert_not_called()
        mock_log.assert_not_called()
        self.assertEqual(flaky.call_count, 2)
        mock_summary.assert_called_once()
        self.assertEqual(mock_summary.call_args.args[1], [])

    @patch("scripts.monitor_providers.write_summary")
    @patch("scripts.monitor_providers.time.sleep")
    @patch("scripts.monitor_providers.log_issue")
    @patch("scripts.monitor_providers.update_routing_priority")
    def test_main_deprioritizes_when_both_probes_fail(
        self, mock_update, mock_log, mock_sleep, mock_summary
    ):
        healthy = MagicMock(return_value=(CheckResult.HEALTHY, None))
        down = MagicMock(return_value=(CheckResult.FAILED, "Status code 500"))

        with patch.multiple(
            "scripts.monitor_providers",
            check_jina=down,
            check_firecrawl=healthy,
            check_tavily=healthy,
            check_serper=healthy,
            check_exa=healthy,
            check_mistral_websearch=healthy,
            check_mistral_browser=healthy,
            check_duckduckgo=healthy,
        ):
            main()

        mock_update.assert_called_once_with("jina")
        mock_log.assert_called_once()
        self.assertEqual(down.call_count, 2)
        failed = mock_summary.call_args.args[1]
        self.assertEqual([name for name, _ in failed], ["jina"])


class TestCircuitBreaker(unittest.TestCase):
    @patch("scripts.monitor_providers.write_summary")
    @patch("scripts.monitor_providers.time.sleep")
    @patch("scripts.monitor_providers.log_issue")
    @patch("scripts.monitor_providers.update_routing_priority")
    def test_total_probe_failure_leaves_routing_untouched(
        self, mock_update, mock_log, mock_sleep, mock_summary
    ):
        down = MagicMock(return_value=(CheckResult.FAILED, "Network is unreachable"))

        with patch.multiple(
            "scripts.monitor_providers",
            check_jina=down,
            check_firecrawl=down,
            check_tavily=down,
            check_serper=down,
            check_exa=down,
            check_mistral_websearch=down,
            check_mistral_browser=down,
            check_duckduckgo=down,
        ):
            exit_code = main()

        self.assertEqual(exit_code, 1)
        mock_update.assert_not_called()
        mock_log.assert_not_called()
        failing = mock_summary.call_args.args[1]
        self.assertEqual(len(failing), 9)
        self.assertTrue(mock_summary.call_args.kwargs["circuit_breaker"])

    @patch("scripts.monitor_providers.write_summary")
    @patch("scripts.monitor_providers.time.sleep")
    @patch("scripts.monitor_providers.log_issue")
    @patch("scripts.monitor_providers.update_routing_priority")
    def test_one_probed_success_disables_breaker(
        self, mock_update, mock_log, mock_sleep, mock_summary
    ):
        healthy = MagicMock(return_value=(CheckResult.HEALTHY, None))
        down = MagicMock(return_value=(CheckResult.FAILED, "Network is unreachable"))

        with patch.multiple(
            "scripts.monitor_providers",
            check_jina=healthy,
            check_firecrawl=down,
            check_tavily=down,
            check_serper=down,
            check_exa=down,
            check_mistral_websearch=down,
            check_mistral_browser=down,
            check_duckduckgo=down,
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_update.call_count, 8)
        self.assertFalse(mock_summary.call_args.kwargs.get("circuit_breaker", False))

    @patch("scripts.monitor_providers.write_summary")
    @patch("scripts.monitor_providers.time.sleep")
    @patch("scripts.monitor_providers.log_issue")
    @patch("scripts.monitor_providers.update_routing_priority")
    def test_single_probed_failure_is_still_deprioritized(
        self, mock_update, mock_log, mock_sleep, mock_summary
    ):
        down = MagicMock(return_value=(CheckResult.FAILED, "Network is unreachable"))
        skipped = MagicMock(return_value=(CheckResult.SKIPPED, "No API Key"))

        with patch.multiple(
            "scripts.monitor_providers",
            check_jina=down,
            check_firecrawl=skipped,
            check_tavily=skipped,
            check_serper=skipped,
            check_exa=skipped,
            check_mistral_websearch=skipped,
            check_mistral_browser=skipped,
            check_duckduckgo=skipped,
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        mock_update.assert_called_once_with("jina")
        mock_log.assert_called_once()


class TestProviderSummary(unittest.TestCase):
    def test_summary_records_retry_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            summary_path = Path(tmp_dir) / "summary.md"
            summary_path.touch()

            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_path)}):
                write_summary(
                    [("jina", "Status code 503")],
                    [("serper", "Status code 401: invalid key\nsecond line")],
                )

            content = summary_path.read_text()

        self.assertIn("Recovered on retry", content)
        self.assertIn("**jina**: first probe failed (Status code 503)", content)
        self.assertIn("Failed every probe", content)
        self.assertIn("**serper**: Status code 401: invalid key second line", content)

    def test_summary_is_a_noop_outside_actions(self):
        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": ""}):
            write_summary([("jina", "Status code 503")], [])

    def test_summary_reports_circuit_breaker(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            summary_path = Path(tmp_dir) / "summary.md"
            summary_path.touch()

            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_path)}):
                write_summary(
                    [],
                    [("jina", "Network is unreachable"), ("serper", "timeout")],
                    circuit_breaker=True,
                )

            content = summary_path.read_text()

        self.assertIn("Circuit breaker tripped", content)
        self.assertIn("All 2 probed providers failed", content)
        self.assertIn("routing was left unchanged", content)


if __name__ == "__main__":
    unittest.main()
