from backend.config import Settings


def test_default_settings():
    s = Settings(_env_file=None)
    assert s.gemini_model == "models/gemini-3.5-flash-lite"
    assert s.gemini_pro_model == "models/gemini-3.8-flash"
    assert s.gemini_vision_model == "models/gemini-3.8-flash"
    assert s.tts_engine == "edge"
    assert s.video_engine == "nuzky"
    assert s.monthly_budget_usd == 0.0
    assert s.approval_timeout_hours == 24
    assert s.max_concurrent_jobs == 2
    assert s.llama_server_bin == r"D:\CONTENT-FACTORY\ollama\bin\llama-server.exe"
    assert s.spark_gguf_blob == r"C:\models\Spark-X2.5-4B-Q4_K_M.gguf"
    assert s.dataset_file == r"C:\cf_training\dataset.jsonl"
    assert s.harvest_state_file == r"C:\cf_training\harvest_state.json"
    assert s.uploads_dir == r"C:\cf_training\temp\uploads"


def test_niches_parsing():
    s = Settings(default_niches="horror,scifi,mystery", _env_file=None)
    assert s.niches_list == ["horror", "scifi", "mystery"]


def test_niches_single():
    s = Settings(default_niches="cooking", _env_file=None)
    assert s.niches_list == ["cooking"]


def test_paths():
    s = Settings(data_dir="/tmp/cf_test", _env_file=None)
    assert str(s.output_dir).endswith("output")
    assert str(s.temp_dir).endswith("temp")
    assert str(s.styles_dir).endswith("styles")
    assert str(s.skills_dir).endswith("skills")


def test_free_first_defaults():
    s = Settings(_env_file=None)
    assert s.gemini_api_key == ""
    assert s.elevenlabs_api_key == ""
    assert s.monthly_budget_usd == 0.0
