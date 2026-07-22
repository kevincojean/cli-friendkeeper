from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cli_friendkeeper.config import (
    DEFAULT_CADENCE,
    DEFAULT_PRIORITY,
    DEFAULT_SUBCOMMAND,
    Config,
    effective_cadence,
    effective_cadence_with_warm_up,
    effective_snooze,
    load_config,
    save_config,
)
from cli_friendkeeper.errors import ConfigError, InvalidPriorityError, StorageError
from cli_friendkeeper.models import ContactState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_given_missing_config_file_when_loading_then_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "nonexistent" / "config.json"
            cfg = load_config(p)
            assert cfg.cadence == DEFAULT_CADENCE

    def test_given_valid_json_when_loading_then_parses_correctly(self) -> None:
        data = {"cadence": {"deep": 10, "casual": 30, "network": 90, "acquaintance": 0}}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            cfg = load_config(p)
            assert cfg.cadence == {"deep": 10, "casual": 30, "network": 90, "acquaintance": 0}
            assert cfg.default_priority == DEFAULT_PRIORITY

    def test_given_default_priority_in_config_when_loading_then_uses_it(self) -> None:
        data = {"cadence": {"deep": 15}, "default_priority": "acquaintance"}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            cfg = load_config(p)
            assert cfg.default_priority == "acquaintance"

    def test_given_invalid_default_priority_when_loading_then_raises_config_error(self) -> None:
        data = {"cadence": {"deep": 15}, "default_priority": "unknown"}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            with pytest.raises(ConfigError, match="invalid default_priority"):
                load_config(p)

    def test_given_default_subcommand_in_config_when_loading_then_uses_it(self) -> None:
        data = {"cadence": {"deep": 15}, "default_subcommand": "list"}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            cfg = load_config(p)
            assert cfg.default_subcommand == "list"

    def test_given_missing_default_subcommand_when_loading_then_defaults_to_due(self) -> None:
        data = {"cadence": {"deep": 15}}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            cfg = load_config(p)
            assert cfg.default_subcommand == DEFAULT_SUBCOMMAND

    def test_given_invalid_default_subcommand_when_loading_then_raises_config_error(self) -> None:
        data = {"cadence": {"deep": 15}, "default_subcommand": "unknown"}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            with pytest.raises(ConfigError, match="invalid default_subcommand"):
                load_config(p)

    def test_given_partial_config_when_loading_then_uses_defaults_for_missing_keys(self) -> None:
        data = {"cadence": {"deep": 7}}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            cfg = load_config(p)
            assert cfg.cadence == {"deep": 7}

    def test_given_bad_json_when_loading_then_raises_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("not json")
            with pytest.raises(ConfigError, match="invalid JSON"):
                load_config(p)

    def test_given_cadence_not_object_when_loading_then_raises_config_error(self) -> None:
        data = {"cadence": "not-a-dict"}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            with pytest.raises(ConfigError, match="missing.*cadence"):
                load_config(p)

    def test_given_cadence_value_not_int_when_loading_then_raises_config_error(self) -> None:
        data = {"cadence": {"deep": "fifteen"}}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            with pytest.raises(ConfigError, match="cadence.*must be integers"):
                load_config(p)

    def test_given_top_level_not_object_when_loading_then_raises_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            p.write_text("[]")
            with pytest.raises(ConfigError, match="expected a JSON object"):
                load_config(p)

    def test_given_missing_cadence_key_when_loading_then_raises_config_error(self) -> None:
        data = {"foo": "bar"}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            with pytest.raises(ConfigError, match="missing.*cadence"):
                load_config(p)


# ---------------------------------------------------------------------------
# save_config
# ---------------------------------------------------------------------------

class TestSaveConfig:
    def test_given_saved_config_when_reloading_then_round_trips(self) -> None:
        cfg = Config(cadence={"deep": 5, "casual": 10})
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            save_config(cfg, p)
            assert p.exists()
            reloaded = load_config(p)
            assert reloaded.cadence == {"deep": 5, "casual": 10}
            assert reloaded.default_priority == DEFAULT_PRIORITY

    def test_given_non_default_priority_when_saving_then_persists(self) -> None:
        cfg = Config(cadence={"deep": 5}, default_priority="acquaintance")
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            save_config(cfg, p)
            reloaded = load_config(p)
            assert reloaded.default_priority == "acquaintance"

    def test_given_non_default_subcommand_when_saving_then_persists(self) -> None:
        cfg = Config(cadence={"deep": 5}, default_subcommand="list")
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            save_config(cfg, p)
            reloaded = load_config(p)
            assert reloaded.default_subcommand == "list"

    def test_given_default_subcommand_when_saving_then_omitted_from_file(self) -> None:
        cfg = Config(cadence={"deep": 5}, default_subcommand=DEFAULT_SUBCOMMAND)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            save_config(cfg, p)
            raw = json.loads(p.read_text())
            assert "default_subcommand" not in raw

    def test_given_saved_default_subcommand_when_reading_raw_then_present(self) -> None:
        cfg = Config(cadence={"deep": 3}, default_subcommand="list")
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            save_config(cfg, p)
            raw = json.loads(p.read_text())
            assert raw["default_subcommand"] == "list"

    def test_given_new_config_when_saving_then_creates_parent_dirs(self) -> None:
        cfg = Config(cadence={"deep": 1})
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a" / "b" / "config.json"
            save_config(cfg, p)
            assert p.exists()

    def test_given_saved_config_when_reading_raw_then_format_matches(self) -> None:
        cfg = Config(cadence={"deep": 3})
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            save_config(cfg, p)
            raw = json.loads(p.read_text())
            assert raw == {"cadence.deep": 3}

    def test_given_unwritable_path_when_saving_then_raises_storage_error(self) -> None:
        cfg = Config(cadence={"deep": 1})
        p = Path("/no-perms/config.json")
        with pytest.raises(StorageError, match="could not write config"):
            save_config(cfg, p)


# ---------------------------------------------------------------------------
# effective_cadence
# ---------------------------------------------------------------------------

class TestEffectiveCadence:
    def test_given_per_contact_override_when_effective_then_override_wins(self) -> None:
        cfg = Config(cadence={"deep": 15})
        assert effective_cadence(cfg, "deep", 99) == 99

    def test_given_config_cadence_when_effective_then_uses_config_value(self) -> None:
        cfg = Config(cadence={"deep": 7})
        assert effective_cadence(cfg, "deep", None) == 7

    def test_given_missing_in_config_when_effective_then_uses_default_cadence(self) -> None:
        cfg = Config(cadence={})
        assert effective_cadence(cfg, "deep", None) == DEFAULT_CADENCE["deep"]

    def test_given_unknown_priority_when_effective_then_uses_default_cadence(self) -> None:
        cfg = Config(cadence={"deep": 5})
        assert effective_cadence(cfg, "network", None) == DEFAULT_CADENCE["network"]

    def test_given_acquaintance_priority_when_effective_then_returns_zero(self) -> None:
        cfg = Config(cadence=DEFAULT_CADENCE)
        assert effective_cadence(cfg, "acquaintance", None) == 0

    def test_given_acquaintance_with_override_when_effective_then_override_wins(self) -> None:
        cfg = Config(cadence=DEFAULT_CADENCE)
        assert effective_cadence(cfg, "acquaintance", 30) == 30

    def test_given_invalid_priority_when_effective_then_raises(self) -> None:
        cfg = Config(cadence={"deep": 5})
        with pytest.raises(InvalidPriorityError, match="unknown priority"):
            effective_cadence(cfg, "unknown", None)

    def test_given_override_with_unknown_priority_when_effective_then_returns_override(self) -> None:
        """Override short-circuits, so an unknown priority is fine."""
        cfg = Config(cadence={"deep": 5})
        assert effective_cadence(cfg, "unknown", 42) == 42


# ---------------------------------------------------------------------------
# Warm-Up Config
# ---------------------------------------------------------------------------

class TestWarmUpConfigDefaults:
    def test_given_no_config_file_when_loading_then_warm_up_defaults_match_spec(self) -> None:
        cfg = Config(cadence=DEFAULT_CADENCE)
        assert cfg.warm_up == {"acquaintance": 45, "casual": 15}

    def test_given_no_config_file_when_loading_then_warm_up_max_snoozes_defaults(self) -> None:
        cfg = Config(cadence=DEFAULT_CADENCE)
        assert cfg.warm_up_max_snoozes == {"acquaintance": 2, "casual": 3}

    def test_given_no_config_file_when_loading_then_acquaintance_auto_upgrade_defaults_true(self) -> None:
        cfg = Config(cadence=DEFAULT_CADENCE)
        assert cfg.acquaintance_auto_upgrade is True


class TestWarmUpLoading:
    def test_given_warm_up_flat_keys_in_config_when_loading_then_parsed_correctly(self) -> None:
        data = {"cadence": {"deep": 15}, "warm_up.acquaintance": 30, "warm_up.casual": 10}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            cfg = load_config(p)
            assert cfg.warm_up["acquaintance"] == 30
            assert cfg.warm_up["casual"] == 10

    def test_given_warm_up_max_snoozes_flat_keys_in_config_when_loading_then_parsed_correctly(self) -> None:
        data = {"cadence": {"deep": 15}, "warm_up.max_snoozes.acquaintance": 5}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            cfg = load_config(p)
            assert cfg.warm_up_max_snoozes["acquaintance"] == 5

    def test_given_acquaintance_auto_upgrade_false_in_config_when_loading_then_false(self) -> None:
        data = {"cadence": {"deep": 15}, "acquaintance.auto_upgrade": False}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            cfg = load_config(p)
            assert cfg.acquaintance_auto_upgrade is False


class TestWarmUpValidation:
    def test_given_warm_up_non_integer_when_loading_then_raises_config_error(self) -> None:
        data = {"cadence": {"deep": 15}, "warm_up.acquaintance": "ten"}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            with pytest.raises(ConfigError, match="warm_up"):
                load_config(p)

    def test_given_warm_up_max_snoozes_negative_when_loading_then_raises_config_error(self) -> None:
        data = {"cadence": {"deep": 15}, "warm_up.max_snoozes.casual": -1}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            with pytest.raises(ConfigError, match="warm_up"):
                load_config(p)

    def test_given_acquaintance_auto_upgrade_non_bool_when_loading_then_raises_config_error(self) -> None:
        data = {"cadence": {"deep": 15}, "acquaintance.auto_upgrade": "yes"}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            with pytest.raises(ConfigError, match="auto_upgrade"):
                load_config(p)

    def test_given_warm_up_unknown_priority_when_loading_then_raises_config_error(self) -> None:
        data = {"cadence": {"deep": 15}, "warm_up.bestie": 10}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            _write_json(p, data)
            with pytest.raises(ConfigError, match="warm_up"):
                load_config(p)


class TestWarmUpSave:
    def test_given_custom_warm_up_when_saving_then_flat_keys_written(self) -> None:
        cfg = Config(
            cadence={"deep": 15},
            warm_up={"acquaintance": 30},
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            save_config(cfg, p)
            raw = json.loads(p.read_text())
            assert raw["warm_up.acquaintance"] == 30

    def test_given_default_warm_up_when_saving_then_not_written(self) -> None:
        cfg = Config(cadence={"deep": 15})
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            save_config(cfg, p)
            raw = json.loads(p.read_text())
            for key in raw:
                assert not key.startswith("warm_up")

    def test_given_auto_upgrade_false_when_saving_then_written(self) -> None:
        cfg = Config(cadence={"deep": 15}, acquaintance_auto_upgrade=False)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            save_config(cfg, p)
            raw = json.loads(p.read_text())
            assert raw["acquaintance.auto_upgrade"] is False


class TestEffectiveWarmUpCadence:
    def test_given_acquaintance_state_when_effective_warm_up_cadence_then_returns_warm_up_value(self) -> None:
        cfg = Config(cadence=DEFAULT_CADENCE)
        state = ContactState(id="uuid-a", name="A", warm_up_consumed=False, snooze_count=0)
        result = effective_cadence_with_warm_up(cfg, "acquaintance", state)
        assert result == 45

    def test_given_acquaintance_warm_up_consumed_when_effective_warm_up_cadence_then_returns_regular_cadence_zero(self) -> None:
        cfg = Config(cadence=DEFAULT_CADENCE)
        state = ContactState(id="uuid-a", name="A", warm_up_consumed=True, snooze_count=2)
        result = effective_cadence_with_warm_up(cfg, "acquaintance", state)
        assert result == 0

    def test_given_casual_state_when_effective_warm_up_cadence_then_returns_warm_up_value(self) -> None:
        cfg = Config(cadence=DEFAULT_CADENCE)
        state = ContactState(id="uuid-b", name="B", warm_up_consumed=False, snooze_count=0)
        result = effective_cadence_with_warm_up(cfg, "casual", state)
        assert result == 15

    def test_given_casual_warm_up_consumed_when_effective_warm_up_cadence_then_returns_regular_cadence(self) -> None:
        cfg = Config(cadence=DEFAULT_CADENCE)
        state = ContactState(id="uuid-b", name="B", warm_up_consumed=True, snooze_count=3)
        result = effective_cadence_with_warm_up(cfg, "casual", state)
        assert result == 45

    def test_given_deep_contact_when_effective_warm_up_cadence_then_returns_regular_cadence(self) -> None:
        cfg = Config(cadence=DEFAULT_CADENCE)
        state = ContactState(id="uuid-d", name="D", warm_up_consumed=True, snooze_count=0)
        result = effective_cadence_with_warm_up(cfg, "deep", state)
        assert result == 15

    def test_given_network_contact_when_effective_warm_up_cadence_then_returns_regular_cadence(self) -> None:
        cfg = Config(cadence=DEFAULT_CADENCE)
        state = ContactState(id="uuid-n", name="N", warm_up_consumed=True, snooze_count=0)
        result = effective_cadence_with_warm_up(cfg, "network", state)
        assert result == 180
