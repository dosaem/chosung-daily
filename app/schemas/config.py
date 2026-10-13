from pydantic import BaseModel


class MinAppVersion(BaseModel):
    ios: str
    android: str


class Maintenance(BaseModel):
    enabled: bool
    message: str | None


class StoreUrls(BaseModel):
    """스토어 등록 전에는 둘 다 null 이다 (환경변수가 비어 있음)."""

    ios: str | None
    android: str | None


class AppConfigResponse(BaseModel):
    min_app_version: MinAppVersion
    maintenance: Maintenance
    languages: list[str]
    store_urls: StoreUrls
