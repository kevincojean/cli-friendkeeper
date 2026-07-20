from pathlib import Path

from cli_friendkeeper.paths import APP_DIR, config_dir, config_file, data_dir, data_file


class TestDataDir:
    def test_given_xdg_cache_home_set_when_calling_data_dir_then_uses_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        result = data_dir()
        assert result == tmp_path / APP_DIR
        assert result.is_dir()

    def test_given_no_xdg_cache_home_when_calling_data_dir_then_falls_back_to_default(self, monkeypatch, tmp_path):
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = data_dir()
        assert result == tmp_path / ".cache" / APP_DIR
        assert result.is_dir()

    def test_given_cache_home_is_symlink_when_calling_data_dir_then_returns_resolved_path(
        self, monkeypatch, tmp_path,
    ) -> None:
        real_cache = tmp_path / "realcache"
        real_cache.mkdir()
        link_cache = tmp_path / "linkcache"
        link_cache.symlink_to(real_cache)
        monkeypatch.setenv("XDG_CACHE_HOME", str(link_cache))
        result = data_dir()
        assert result == (real_cache / APP_DIR).resolve()
        assert result.is_dir()
        # data dir was created inside the real target, not under the symlink
        assert result.parent == (real_cache / "com.kevincojean").resolve()


class TestConfigDir:
    def test_given_xdg_config_home_set_when_calling_config_dir_then_uses_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        result = config_dir()
        assert result == tmp_path / APP_DIR
        assert result.is_dir()

    def test_given_no_xdg_config_home_when_calling_config_dir_then_falls_back_to_default(self, monkeypatch, tmp_path):
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = config_dir()
        assert result == tmp_path / ".config" / APP_DIR
        assert result.is_dir()


class TestDataFile:
    def test_given_data_dir_when_getting_data_file_then_returns_path_under_it(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        result = data_file("friends.jsonl")
        assert result == data_dir() / "friends.jsonl"
        # parent dir was created by data_dir() call
        assert result.parent.is_dir()


class TestConfigFile:
    def test_given_config_dir_when_getting_config_file_then_returns_config_json_path(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        result = config_file()
        assert result == config_dir() / "config.json"
