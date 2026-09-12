from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://solapur:solapur@localhost:5432/solapur"
    jwt_secret: str = "dev-only-change-me"
    jwt_expire_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:3000,http://localhost:8081,http://localhost:19006"
    demo_geo: bool = True
    upload_dir: str = "./uploads"
    vision_ai_enabled: bool = False
    vision_model_path: str = "backend/models/complaint_vision_classifier_v1.pt"
    vision_confidence_threshold: float = 0.60
    rag_enabled: bool = False
    advanced_verification_enabled: bool = False
    push_notifications_enabled: bool = False
    default_sla_enabled: bool = False
    sla_poll_interval_seconds: int = 60
    ml_text_classifier_enabled: bool = False
    ml_confidence_threshold: float = 0.50
    ml_model_path: str = "backend/models/complaint_text_classifier_v1.joblib"
    semantic_duplicates_enabled: bool = False
    duplicate_similarity_threshold: float = 0.60
    duplicate_max_distance_meters: float = 300.0
    duplicate_window_days: int = 7
    duplicate_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    # Phase 3 – SLA breach probability prediction
    sla_breach_ml_enabled: bool = False
    sla_breach_model_path: str = "backend/models/sla_breach_predictor_v1.joblib"
    # Phase 6 – Multi-signal resolution verification
    verification_gps_threshold_meters: float = 200.0
    verification_min_duration_seconds: int = 30
    verification_auto_verify_threshold: float = 0.75
    verification_review_threshold: float = 0.50

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
